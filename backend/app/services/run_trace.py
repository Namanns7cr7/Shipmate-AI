"""
run_trace — structured, queryable observability for ShipMate's multi-agent runs.

The problem this solves: a single analyze/coder run fans out to 4+ agents, each
making ≥1 LLM call, each call possibly retrying (auth refresh, array-not-string,
short-summary). All of that was visible ONLY as scattered `logging` lines, so
reconstructing "why did this run produce a bad finding / waste 3 retries" meant
reading logs by hand. There was no way to ask "how much retry waste happened
this run" or to A/B a prompt change as a metric.

This module records ONE row per instrumented operation (agent pass, LLM call,
critic pass) into a `run_traces` table on the shared sqlite_store, keyed by a
`run_id` that flows through a `contextvars.ContextVar` — so the orchestrator
sets it once and every nested agent/provider call (including those dispatched
via `asyncio.to_thread`, which copies the context) attributes itself to the
same run with NO plumbing through call signatures.

Design choices:
  • CHEAP NO-OP when inactive. `span()` / `record()` do nothing unless a run_id
    is active (or passed explicitly), so unit tests that call a provider
    directly never touch the DB and production overhead is one ContextVar read.
  • FAIL-OPEN. A tracing write must never break the thing it observes — every
    DB touch is wrapped; on error we log at debug and move on.
  • DETERMINISTIC fields only (prompt hash, char counts, latency, retry count,
    outcome). Token counts are approximated from chars (≈chars/4) and clearly
    labelled `approx` — we don't change provider return shapes to chase exact
    usage. The point is relative comparison + retry visibility, not billing.

This is the connective tissue B2 (Coder failure-memory) and prompt-A/B work
build on: a run's trace is the evidence of what actually happened.
"""
from __future__ import annotations

import contextvars
import hashlib
import logging
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from app.services import sqlite_store

logger = logging.getLogger("shipmate.run_trace")

# Own store (own file) so observability is fully decoupled from the inflight
# registry — run_trace works even if inflight_registry is never imported, and a
# trace write can never contend with a path-claim write. Legacy env override
# SHIPMATE_TRACE_DB wins (test fixtures repoint it); else SHIPMATE_STORE_DIR.
_STORE = "run_trace"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS run_traces (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL,
    phase         TEXT,                -- logical group: 'analyze' | 'coder' | 'critic' | ...
    component     TEXT NOT NULL,       -- 'agent:guardrail' | 'llm:bedrock:smart' | ...
    op            TEXT NOT NULL,       -- 'run' | 'invoke' | 'enhance' | 'discover' | ...
    model         TEXT,
    prompt_hash   TEXT,
    prompt_chars  INTEGER DEFAULT 0,
    output_chars  INTEGER DEFAULT 0,
    approx_tokens INTEGER DEFAULT 0,   -- (prompt+output) chars / 4, clearly approximate
    retries       INTEGER DEFAULT 0,
    latency_ms    INTEGER DEFAULT 0,
    outcome       TEXT,                -- 'ok' | 'error'
    error         TEXT,
    ts            INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_run_traces_run ON run_traces(run_id, id);
CREATE INDEX IF NOT EXISTS idx_run_traces_component ON run_traces(component);
"""

sqlite_store.register(
    _STORE,
    filename="shipmate_run_traces.db",
    legacy_env="SHIPMATE_TRACE_DB",
    schema=_SCHEMA,
)


def _conn() -> sqlite3.Connection:
    """Per-(thread, path) cached connection from the shared store manager, with
    this store's schema applied on first open."""
    return sqlite_store.connect(_STORE)


def init_db() -> None:
    """Eager-create the run_traces table (called from the FastAPI lifespan via
    sqlite_store.init_all, which iterates every registered store)."""
    sqlite_store.init_schema(_STORE)


# ── Active-run context ───────────────────────────────────────────────────────

_current_run: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "shipmate_run_id", default=None
)


def new_run_id(prefix: str = "run") -> str:
    """Mint a run id. Uses a monotonic perf-counter + a short hash so it's
    unique without Math.random/uuid noise and stable enough to read in logs.
    (uuid4 is fine here too, but this keeps ids short + greppable.)"""
    seed = f"{prefix}-{time.time_ns()}-{time.perf_counter_ns()}"
    return f"{prefix}-{hashlib.sha1(seed.encode()).hexdigest()[:12]}"


def get_current_run() -> Optional[str]:
    return _current_run.get()


def set_current_run(run_id: Optional[str]) -> contextvars.Token:
    """Set the active run id, returning the token to reset() later. Prefer the
    `run()` context manager which handles reset for you."""
    return _current_run.set(run_id)


@contextmanager
def run(run_id: Optional[str] = None, *, prefix: str = "run"):
    """Context manager establishing an active run. Yields the run_id. Nested
    agent/provider calls within the block (incl. asyncio.to_thread workers)
    attribute their spans to this run automatically."""
    rid = run_id or new_run_id(prefix)
    token = _current_run.set(rid)
    try:
        yield rid
    finally:
        _current_run.reset(token)


# ── Span (timed, retry-aware) ────────────────────────────────────────────────

class _Span:
    """Mutable handle yielded by `span()`. Call `.bump_retry()` from inside a
    retry path so the recorded row reflects how many extra round-trips happened.
    `.set_output(text_or_len)` lets the caller record produced size + tokens."""

    __slots__ = ("retries", "output_chars", "_extra")

    def __init__(self) -> None:
        self.retries = 0
        self.output_chars = 0
        self._extra: Dict[str, Any] = {}

    def bump_retry(self, n: int = 1) -> None:
        self.retries += n

    def set_output(self, value: Any) -> None:
        if isinstance(value, int):
            self.output_chars = value
        elif value is not None:
            try:
                self.output_chars = len(str(value))
            except Exception:
                pass


@contextmanager
def span(
    component: str,
    op: str = "invoke",
    *,
    model: Optional[str] = None,
    prompt: Optional[str] = None,
    phase: Optional[str] = None,
    run_id: Optional[str] = None,
):
    """Time an operation and record one `run_traces` row on exit. No-op (still
    yields a usable _Span) when no run is active and no run_id is given, so
    callers don't branch.

    Records outcome='error' + the exception text if the block raises, then
    re-raises — tracing never swallows the real error."""
    rid = run_id or get_current_run()
    sp = _Span()
    if not rid:
        # Inactive: hand back a span so `.bump_retry()` etc. are safe, write nothing.
        yield sp
        return

    started = time.perf_counter()
    outcome = "ok"
    err_text: Optional[str] = None
    try:
        yield sp
    except Exception as e:
        outcome = "error"
        err_text = f"{type(e).__name__}: {e}"[:500]
        raise
    finally:
        latency_ms = int((time.perf_counter() - started) * 1000)
        prompt_chars = len(prompt) if prompt else 0
        approx_tokens = (prompt_chars + sp.output_chars) // 4
        prompt_hash = (
            hashlib.sha1(prompt.encode("utf-8", "replace")).hexdigest()[:16]
            if prompt else None
        )
        _safe_insert(
            run_id=rid, phase=phase, component=component, op=op, model=model,
            prompt_hash=prompt_hash, prompt_chars=prompt_chars,
            output_chars=sp.output_chars, approx_tokens=approx_tokens,
            retries=sp.retries, latency_ms=latency_ms,
            outcome=outcome, error=err_text,
        )


def record(
    component: str,
    op: str,
    *,
    model: Optional[str] = None,
    prompt: Optional[str] = None,
    output: Any = None,
    retries: int = 0,
    latency_ms: int = 0,
    outcome: str = "ok",
    error: Optional[str] = None,
    phase: Optional[str] = None,
    run_id: Optional[str] = None,
) -> None:
    """Record a single trace row directly (when a context manager doesn't fit).
    No-op when no run is active."""
    rid = run_id or get_current_run()
    if not rid:
        return
    prompt_chars = len(prompt) if prompt else 0
    output_chars = 0
    if isinstance(output, int):
        output_chars = output
    elif output is not None:
        try:
            output_chars = len(str(output))
        except Exception:
            output_chars = 0
    _safe_insert(
        run_id=rid, phase=phase, component=component, op=op, model=model,
        prompt_hash=(hashlib.sha1(prompt.encode("utf-8", "replace")).hexdigest()[:16]
                     if prompt else None),
        prompt_chars=prompt_chars, output_chars=output_chars,
        approx_tokens=(prompt_chars + output_chars) // 4,
        retries=retries, latency_ms=latency_ms, outcome=outcome, error=error,
    )


def _safe_insert(**row: Any) -> None:
    try:
        c = _conn()
        c.execute(
            "INSERT INTO run_traces "
            "(run_id, phase, component, op, model, prompt_hash, prompt_chars, "
            " output_chars, approx_tokens, retries, latency_ms, outcome, error, ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row["run_id"], row.get("phase"), row["component"], row["op"],
                row.get("model"), row.get("prompt_hash"), row.get("prompt_chars", 0),
                row.get("output_chars", 0), row.get("approx_tokens", 0),
                row.get("retries", 0), row.get("latency_ms", 0),
                row.get("outcome", "ok"), row.get("error"), int(time.time()),
            ),
        )
        c.commit()
    except Exception as e:  # pragma: no cover - tracing must never break callers
        logger.debug("run_trace insert failed (%s)", e)


# ── Query ────────────────────────────────────────────────────────────────────

def list_traces(run_id: str) -> List[Dict[str, Any]]:
    """All trace rows for a run, oldest first."""
    try:
        rows = _conn().execute(
            "SELECT * FROM run_traces WHERE run_id=? ORDER BY id ASC", (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:  # pragma: no cover
        logger.debug("list_traces failed (%s)", e)
        return []


def run_summary(run_id: str) -> Dict[str, Any]:
    """Aggregate a run: total spans, total latency, total retries, error count,
    approx tokens, and a per-component breakdown. This is the metric surface —
    e.g. `retries` > 0 is the validation-retry waste that used to be invisible."""
    rows = list_traces(run_id)
    summary: Dict[str, Any] = {
        "run_id": run_id,
        "spans": len(rows),
        "total_latency_ms": sum(r.get("latency_ms", 0) for r in rows),
        "total_retries": sum(r.get("retries", 0) for r in rows),
        "errors": sum(1 for r in rows if r.get("outcome") == "error"),
        "approx_tokens": sum(r.get("approx_tokens", 0) for r in rows),
        "by_component": {},
    }
    for r in rows:
        comp = r.get("component", "?")
        agg = summary["by_component"].setdefault(
            comp, {"count": 0, "latency_ms": 0, "retries": 0}
        )
        agg["count"] += 1
        agg["latency_ms"] += r.get("latency_ms", 0)
        agg["retries"] += r.get("retries", 0)
    return summary


def recent_runs(limit: int = 20) -> List[str]:
    """Distinct run ids seen recently (newest first) — for a debug/ops endpoint."""
    try:
        rows = _conn().execute(
            "SELECT run_id, MAX(id) AS last FROM run_traces "
            "GROUP BY run_id ORDER BY last DESC LIMIT ?",
            (max(1, min(int(limit), 200)),),
        ).fetchall()
        return [r["run_id"] for r in rows]
    except Exception as e:  # pragma: no cover
        logger.debug("recent_runs failed (%s)", e)
        return []


def reset_all() -> None:
    """Wipe all traces. Test fixtures / debug only."""
    try:
        c = _conn()
        c.execute("DELETE FROM run_traces")
        c.commit()
    except Exception as e:  # pragma: no cover
        logger.debug("run_trace reset failed (%s)", e)
