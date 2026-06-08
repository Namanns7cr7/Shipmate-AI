"""
Inflight registry — single sqlite source of truth for cross-process coordination.

This module replaces THREE older state mechanisms:
  1. The in-line `seen_paths` collision detection in coder_loop.run_round.
  2. The in-memory `CIWatcher._registry: Dict` in ci_watcher.py.
  3. The /tmp/coder_loop_state.json file (seen_signatures, parked).

Why a single sqlite instead of three separate stores:
  • The CLI loop and the FastAPI process need to coordinate. If the loop is
    actuating `backend/app/main.py` and a UI user clicks "Apply Fix" on
    another finding that also touches main.py, we must reject the second
    actuate atomically — that's hard with two separate JSON files.
  • CIWatcher state needs to survive backend restarts (uvicorn --reload
    happens every code change in dev). In-memory only means orphan PRs.
  • The finding journal (dismissed / in-progress / shipped / parked) is the
    same kind of cross-context state — UI marks dismissed, loop respects it.

Tables (see plan):
  inflight_paths    — path-level claims so two findings don't both rewrite
                      backend/app/main.py
  ci_watch_state    — persistent CIWatcher state-of-record
  ci_watch_log      — append-only log lines streamed to UI
  finding_journal   — per-finding-signature lifecycle state

Concurrency model:
  • WAL journal mode + 5s busy_timeout — concurrent readers always work,
    writers serialize through sqlite's per-DB write lock.
  • One short transaction per claim/release/upsert. Never hold a write txn
    across the Coder/Bedrock call (which can be 60s).
  • Connection-per-thread cache via threading.local() so we don't reopen
    the file on every call.

Path location:
  /tmp/shipmate_inflight.db — matches the convention of
  /tmp/coder_loop_state.json that this is replacing. Wiped on reboot;
  fine for a dev workflow. Override with SHIPMATE_INFLIGHT_DB env var
  if you want it elsewhere.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from app.services import sqlite_store

logger = logging.getLogger("shipmate.inflight_registry")

# Store identity in the shared connection manager. The legacy env override
# SHIPMATE_INFLIGHT_DB still wins (test fixtures rely on it); otherwise the file
# lives under SHIPMATE_STORE_DIR (default /tmp) as shipmate_inflight.db.
_STORE = "inflight"
_DEFAULT_DB_PATH = "/tmp/shipmate_inflight.db"  # kept for docstring/back-ref only
_DEFAULT_CLAIM_TTL_S = 600  # 10min — long enough for Coder + pytest, short enough that crashes self-heal


def _db_path() -> str:
    """Resolved path for this store. Delegates to sqlite_store (which honours
    the SHIPMATE_INFLIGHT_DB legacy override). Retained for callers/tests that
    introspect the location."""
    return sqlite_store.db_path(_STORE)


# ── Schema ──────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS inflight_paths (
    repo_full_name   TEXT NOT NULL,
    branch           TEXT NOT NULL,
    path             TEXT NOT NULL,
    finding_sig      TEXT NOT NULL,
    claimed_by       TEXT NOT NULL,
    claimed_at       INTEGER NOT NULL,
    expires_at       INTEGER NOT NULL,
    PRIMARY KEY (repo_full_name, branch, path)
);
CREATE INDEX IF NOT EXISTS idx_inflight_paths_expiry ON inflight_paths(expires_at);

-- NOTE on access_token: this column now stores a VAULT SESSION ID
-- (shipmate_sess_…), NOT the raw GitHub token. The token lives only in the
-- session vault (session_store / shipmate_sessions.db); CIWatcher persists the
-- session ref here so a backend restart (uvicorn --reload fires on every code
-- change in dev) can resolve it back to a token and RESUME watching open PRs.
-- Column name kept for back-compat with existing rows (a legacy raw token in
-- here still works — resume_from_db passes a non-session value straight
-- through). Storing the ref instead of the token means /tmp no longer holds a
-- live credential.
CREATE TABLE IF NOT EXISTS ci_watch_state (
    owner            TEXT NOT NULL,
    repo             TEXT NOT NULL,
    pr_number        INTEGER NOT NULL,
    pr_url           TEXT,
    branch           TEXT NOT NULL,
    base_branch      TEXT NOT NULL,
    finding_json     TEXT NOT NULL,
    repo_lens_json   TEXT,
    access_token     TEXT,
    status           TEXT NOT NULL,
    attempts         INTEGER NOT NULL DEFAULT 0,
    last_patch_hash  TEXT,
    last_error       TEXT,
    started_at       INTEGER NOT NULL,
    last_event_at    INTEGER NOT NULL,
    PRIMARY KEY (owner, repo, pr_number)
);
CREATE INDEX IF NOT EXISTS idx_ci_watch_status ON ci_watch_state(status);

CREATE TABLE IF NOT EXISTS ci_watch_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    owner            TEXT NOT NULL,
    repo             TEXT NOT NULL,
    pr_number        INTEGER NOT NULL,
    ts               INTEGER NOT NULL,
    level            TEXT NOT NULL,
    msg              TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ci_watch_log_pr ON ci_watch_log(owner, repo, pr_number, id);

CREATE TABLE IF NOT EXISTS finding_journal (
    finding_sig      TEXT PRIMARY KEY,
    repo_full_name   TEXT NOT NULL,
    state            TEXT NOT NULL,
    last_attempt_at  INTEGER NOT NULL,
    attempt_count    INTEGER NOT NULL DEFAULT 0,
    pr_url           TEXT,
    notes            TEXT
);
CREATE INDEX IF NOT EXISTS idx_journal_state ON finding_journal(state);

-- Small key/value bag for cross-process scalars (pytest baseline, etc).
-- Values are stringly-typed; callers JSON-encode if they need structure.
CREATE TABLE IF NOT EXISTS meta_kv (
    key              TEXT PRIMARY KEY,
    value            TEXT,
    updated_at       INTEGER NOT NULL
);

-- Durable BuildRun state machine. /build/execute used to run the whole
-- plan→critique→actuate loop inside a single HTTP request, holding all state
-- in local variables — a dropped connection or backend restart mid-build lost
-- the run entirely (only the CIWatcher survived, because IT got persisted).
-- This table makes a build observable + resumable independent of the request
-- that started it, mirroring the ci_watch_state pattern.
--   run_id    : UUID PK so the SAME opportunity can have >1 run over time
--               (re-runs after a fix) without clobbering history.
--   status    : planning | critiquing | actuating | done | failed | plan_rejected
--   *_json    : the ExecutionPlan / PlanCritique / final BuildExecuteResponse,
--               so a status query can reconstruct the full picture.
--   pr_urls   : JSON array (the loop opens one PR per step).
-- finding_journal stays the suppress-source-of-truth (dismissed/shipped); this
-- table is the run RECORD — they're updated together at each boundary.
CREATE TABLE IF NOT EXISTS build_runs (
    run_id           TEXT PRIMARY KEY,
    owner            TEXT NOT NULL,
    repo             TEXT NOT NULL,
    branch           TEXT NOT NULL,
    opportunity_sig  TEXT NOT NULL,
    opportunity_title TEXT,
    status           TEXT NOT NULL,
    plan_json        TEXT,
    critique_json    TEXT,
    result_json      TEXT,
    pr_urls          TEXT,
    step_count       INTEGER NOT NULL DEFAULT 0,
    steps_completed  INTEGER NOT NULL DEFAULT 0,
    error            TEXT,
    started_at       INTEGER NOT NULL,
    last_event_at    INTEGER NOT NULL,
    completed_at     INTEGER
);
CREATE INDEX IF NOT EXISTS idx_build_runs_repo ON build_runs(owner, repo, started_at);
CREATE INDEX IF NOT EXISTS idx_build_runs_status ON build_runs(status);
CREATE INDEX IF NOT EXISTS idx_build_runs_sig ON build_runs(opportunity_sig);
"""


# ── Connection (delegated to the shared sqlite_store) ───────────────────────

sqlite_store.register(
    _STORE,
    filename="shipmate_inflight.db",
    legacy_env="SHIPMATE_INFLIGHT_DB",
    schema=_SCHEMA,
)


def _conn() -> sqlite3.Connection:
    """Per-(thread, path) cached connection from the shared store manager.
    Shared PRAGMAs (WAL, busy_timeout, foreign_keys) + this store's schema are
    applied on first open."""
    return sqlite_store.connect(_STORE)


def init_db() -> None:
    """Eager-create tables. Called from FastAPI lifespan startup so the
    first request doesn't pay the schema-create cost."""
    sqlite_store.init_schema(_STORE)
    logger.info("InflightRegistry initialized at %s", _db_path())


# ── inflight_paths ──────────────────────────────────────────────────────────

def claim_path(
    repo_full_name: str,
    branch: str,
    path: str,
    finding_sig: str,
    claimed_by: str,
    ttl_s: int = _DEFAULT_CLAIM_TTL_S,
) -> bool:
    """Atomically claim `path` for an actuate. Returns False if already claimed
    by someone else (and the existing claim hasn't expired).

    INSERT OR FAIL means the primary-key conflict is the signal — sqlite
    serializes this through the per-DB write lock so two processes can't
    both win.

    Auto-cleanup: before claiming, delete any expired claims on this row's
    PK. That handles crashed processes (their TTL eventually lapses).
    """
    now = int(time.time())
    expires_at = now + ttl_s
    c = _conn()
    try:
        # First, sweep any expired claim for this exact path so we can take it.
        c.execute(
            "DELETE FROM inflight_paths "
            "WHERE repo_full_name=? AND branch=? AND path=? AND expires_at < ?",
            (repo_full_name, branch, path, now),
        )
        c.execute(
            "INSERT INTO inflight_paths "
            "(repo_full_name, branch, path, finding_sig, claimed_by, claimed_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (repo_full_name, branch, path, finding_sig, claimed_by, now, expires_at),
        )
        c.commit()
        return True
    except sqlite3.IntegrityError:
        # PK conflict — someone else holds the live claim.
        c.rollback()
        return False


def release_path(repo_full_name: str, branch: str, path: str, claimed_by: str) -> None:
    """Release a previously-claimed path. Only the original claimer can release;
    a mismatch is logged but doesn't raise (clean shutdown after a hand-off
    shouldn't crash)."""
    c = _conn()
    cur = c.execute(
        "DELETE FROM inflight_paths "
        "WHERE repo_full_name=? AND branch=? AND path=? AND claimed_by=?",
        (repo_full_name, branch, path, claimed_by),
    )
    c.commit()
    if cur.rowcount == 0:
        logger.debug(
            "release_path: no match for %s/%s/%s by %s",
            repo_full_name, branch, path, claimed_by,
        )


def get_path_claim(repo_full_name: str, branch: str, path: str) -> Optional[Dict[str, Any]]:
    """Inspect the live claim on `path`. None if free or expired."""
    now = int(time.time())
    row = _conn().execute(
        "SELECT * FROM inflight_paths "
        "WHERE repo_full_name=? AND branch=? AND path=? AND expires_at >= ?",
        (repo_full_name, branch, path, now),
    ).fetchone()
    return dict(row) if row else None


# ── ci_watch_state ──────────────────────────────────────────────────────────

def upsert_ci_watch(
    owner: str,
    repo: str,
    pr_number: int,
    *,
    pr_url: Optional[str] = None,
    branch: Optional[str] = None,
    base_branch: Optional[str] = None,
    finding: Optional[Any] = None,         # FindingPayload or dict
    repo_lens: Optional[Any] = None,       # RepoLensSummary or dict
    access_token: Optional[str] = None,
    status: Optional[str] = None,
    attempts: Optional[int] = None,
    last_patch_hash: Optional[str] = None,
    last_error: Optional[str] = None,
) -> None:
    """Insert-or-update a watcher row. Only fields you pass are touched —
    unset args leave the existing column alone (semantics like a partial
    PATCH). On insert, the required columns are materialized from the
    optional args; missing required args raise ValueError."""
    c = _conn()
    now = int(time.time())

    existing = c.execute(
        "SELECT * FROM ci_watch_state WHERE owner=? AND repo=? AND pr_number=?",
        (owner, repo, pr_number),
    ).fetchone()

    finding_json = _to_json(finding) if finding is not None else None
    repo_lens_json = _to_json(repo_lens) if repo_lens is not None else None

    if existing is None:
        # New row — branch/base_branch/finding/status are mandatory.
        if not (branch and base_branch and finding_json and status):
            raise ValueError(
                "upsert_ci_watch: new row requires branch, base_branch, "
                "finding, and status"
            )
        c.execute(
            "INSERT INTO ci_watch_state "
            "(owner, repo, pr_number, pr_url, branch, base_branch, "
            " finding_json, repo_lens_json, access_token, status, attempts, "
            " last_patch_hash, last_error, started_at, last_event_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                owner, repo, pr_number, pr_url, branch, base_branch,
                finding_json, repo_lens_json, access_token, status, attempts or 0,
                last_patch_hash, last_error, now, now,
            ),
        )
    else:
        # PATCH semantics — only update the fields that were passed.
        sets: List[str] = ["last_event_at=?"]
        vals: List[Any] = [now]
        for col, val in [
            ("pr_url", pr_url),
            ("branch", branch),
            ("base_branch", base_branch),
            ("finding_json", finding_json),
            ("repo_lens_json", repo_lens_json),
            ("access_token", access_token),
            ("status", status),
            ("attempts", attempts),
            ("last_patch_hash", last_patch_hash),
            ("last_error", last_error),
        ]:
            if val is not None:
                sets.append(f"{col}=?")
                vals.append(val)
        vals.extend([owner, repo, pr_number])
        c.execute(
            f"UPDATE ci_watch_state SET {', '.join(sets)} "
            "WHERE owner=? AND repo=? AND pr_number=?",
            vals,
        )
    c.commit()


def get_ci_watch(owner: str, repo: str, pr_number: int) -> Optional[Dict[str, Any]]:
    row = _conn().execute(
        "SELECT * FROM ci_watch_state WHERE owner=? AND repo=? AND pr_number=?",
        (owner, repo, pr_number),
    ).fetchone()
    if not row:
        return None
    out = dict(row)
    out["finding"] = _from_json(out.pop("finding_json"))
    out["repo_lens"] = _from_json(out.pop("repo_lens_json"))
    return out


def list_ci_watches(*, status_in: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """List watcher rows, optionally filtered by status (e.g. ['watching','fixing']
    to find rows that need supervisors re-spawned at startup)."""
    if status_in:
        placeholders = ",".join("?" * len(status_in))
        rows = _conn().execute(
            f"SELECT * FROM ci_watch_state WHERE status IN ({placeholders}) "
            "ORDER BY started_at DESC",
            status_in,
        ).fetchall()
    else:
        rows = _conn().execute(
            "SELECT * FROM ci_watch_state ORDER BY started_at DESC"
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        d["finding"] = _from_json(d.pop("finding_json"))
        d["repo_lens"] = _from_json(d.pop("repo_lens_json"))
        out.append(d)
    return out


def delete_ci_watch(owner: str, repo: str, pr_number: int) -> bool:
    cur = _conn().execute(
        "DELETE FROM ci_watch_state WHERE owner=? AND repo=? AND pr_number=?",
        (owner, repo, pr_number),
    )
    _conn().commit()
    return cur.rowcount > 0


# ── ci_watch_log ────────────────────────────────────────────────────────────

def append_log(owner: str, repo: str, pr_number: int, level: str, msg: str) -> int:
    """Append a single log line. Returns the new row's id (the UI paginates
    on `since_id`)."""
    cur = _conn().execute(
        "INSERT INTO ci_watch_log (owner, repo, pr_number, ts, level, msg) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (owner, repo, pr_number, int(time.time()), level, msg),
    )
    _conn().commit()
    return cur.lastrowid


def get_log_tail(
    owner: str, repo: str, pr_number: int,
    since_id: int = 0, limit: int = 200,
) -> Dict[str, Any]:
    """Return log lines with id > since_id. Cap at `limit` per call so a
    long-running watcher doesn't dump megabytes on each poll. The UI
    advances `since_id` to the returned `next_id` and re-polls."""
    rows = _conn().execute(
        "SELECT id, ts, level, msg FROM ci_watch_log "
        "WHERE owner=? AND repo=? AND pr_number=? AND id > ? "
        "ORDER BY id ASC LIMIT ?",
        (owner, repo, pr_number, since_id, limit),
    ).fetchall()
    lines = [dict(row) for row in rows]
    next_id = lines[-1]["id"] if lines else since_id
    return {"lines": lines, "next_id": next_id}


# ── finding_journal ─────────────────────────────────────────────────────────

# Allowed states. Strings instead of an Enum to keep sqlite simple.
_JOURNAL_STATES = {"in_progress", "shipped", "dismissed", "parked"}


def journal_set_state(
    finding_sig: str,
    repo_full_name: str,
    state: str,
    *,
    pr_url: Optional[str] = None,
    notes: Optional[str] = None,
    bump_attempt: bool = False,
) -> None:
    """Upsert journal state. `bump_attempt=True` increments attempt_count.
    Use this at every actuation boundary so the loop knows what's been
    tried."""
    if state not in _JOURNAL_STATES:
        raise ValueError(f"unknown journal state: {state!r}")
    now = int(time.time())
    c = _conn()
    existing = c.execute(
        "SELECT attempt_count FROM finding_journal WHERE finding_sig=?",
        (finding_sig,),
    ).fetchone()
    if existing is None:
        c.execute(
            "INSERT INTO finding_journal "
            "(finding_sig, repo_full_name, state, last_attempt_at, "
            " attempt_count, pr_url, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (finding_sig, repo_full_name, state, now,
             1 if bump_attempt else 0, pr_url, notes),
        )
    else:
        new_count = existing["attempt_count"] + (1 if bump_attempt else 0)
        c.execute(
            "UPDATE finding_journal SET state=?, last_attempt_at=?, "
            "attempt_count=?, pr_url=COALESCE(?, pr_url), "
            "notes=COALESCE(?, notes) "
            "WHERE finding_sig=?",
            (state, now, new_count, pr_url, notes, finding_sig),
        )
    c.commit()


def journal_get_state(finding_sig: str) -> Optional[Dict[str, Any]]:
    row = _conn().execute(
        "SELECT * FROM finding_journal WHERE finding_sig=?",
        (finding_sig,),
    ).fetchone()
    return dict(row) if row else None


def journal_delete(finding_sig: str) -> bool:
    """Remove a journal row entirely. Used by 'reopen' — absence from the
    journal IS the fresh state everywhere else, so deleting is how we undo a
    dismissal/park. Returns True if a row was deleted."""
    c = _conn()
    cur = c.execute("DELETE FROM finding_journal WHERE finding_sig=?", (finding_sig,))
    c.commit()
    return cur.rowcount > 0


def journal_list(
    repo_full_name: Optional[str] = None,
    state_in: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM finding_journal"
    where: List[str] = []
    args: List[Any] = []
    if repo_full_name:
        where.append("repo_full_name=?")
        args.append(repo_full_name)
    if state_in:
        placeholders = ",".join("?" * len(state_in))
        where.append(f"state IN ({placeholders})")
        args.extend(state_in)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY last_attempt_at DESC"
    rows = _conn().execute(sql, args).fetchall()
    return [dict(r) for r in rows]


# ── JSON helpers ────────────────────────────────────────────────────────────

def _to_json(value: Any) -> str:
    """Serialize a Pydantic model or dict for storage."""
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(), default=str)
    if isinstance(value, dict):
        return json.dumps(value, default=str)
    return json.dumps({"value": value}, default=str)


def _from_json(s: Optional[str]) -> Optional[Any]:
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


# ── One-time migration from /tmp/coder_loop_state.json ──────────────────────

_LEGACY_STATE_PATH = "/tmp/coder_loop_state.json"


def migrate_legacy_state(repo_full_name: str = "unknown/unknown") -> int:
    """If /tmp/coder_loop_state.json exists, copy `seen_signatures` and
    `parked` into finding_journal then delete the legacy file. Returns the
    number of rows migrated. Idempotent (deletes the source after success).

    `repo_full_name` is the best-effort default for the legacy entries —
    they didn't carry repo info. Caller can pass the active repo so the
    migrated rows get attributed correctly.
    """
    if not os.path.exists(_LEGACY_STATE_PATH):
        return 0
    try:
        data = json.loads(open(_LEGACY_STATE_PATH).read())
    except Exception as e:
        logger.warning("migrate_legacy_state: failed to read %s: %s",
                       _LEGACY_STATE_PATH, e)
        return 0

    seen = set(data.get("seen_signatures") or [])
    parked = set(data.get("parked") or [])
    migrated = 0

    for sig in parked:
        journal_set_state(sig, repo_full_name, "parked")
        migrated += 1
    # seen-but-not-parked entries get a "dismissed" tag — they were
    # attempted at least once and we don't want them re-picked on first
    # run after the migration. User can `reopen` if they want.
    for sig in seen - parked:
        journal_set_state(sig, repo_full_name, "dismissed",
                          notes="auto-dismissed during legacy state migration")
        migrated += 1

    try:
        os.remove(_LEGACY_STATE_PATH)
        logger.info("migrate_legacy_state: migrated %d entries, removed %s",
                    migrated, _LEGACY_STATE_PATH)
    except OSError as e:
        logger.warning("migrate_legacy_state: could not delete %s: %s",
                       _LEGACY_STATE_PATH, e)
    return migrated


# ── Meta KV (pytest baseline, etc) ──────────────────────────────────────────

def meta_get(key: str) -> Optional[str]:
    row = _conn().execute(
        "SELECT value FROM meta_kv WHERE key=?", (key,),
    ).fetchone()
    return row["value"] if row else None


def meta_set(key: str, value: Optional[str]) -> None:
    """Set or clear a meta value. Pass None to delete the key."""
    c = _conn()
    if value is None:
        c.execute("DELETE FROM meta_kv WHERE key=?", (key,))
    else:
        c.execute(
            "INSERT INTO meta_kv (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=excluded.updated_at",
            (key, value, int(time.time())),
        )
    c.commit()


# ── build_runs (durable BuildRun state machine) ─────────────────────────────

# Terminal + non-terminal statuses. Strings (not an Enum) to keep sqlite simple
# and mirror finding_journal's convention.
_BUILD_RUN_STATES = {
    "planning", "critiquing", "actuating",
    "done", "failed", "plan_rejected",
}
_BUILD_RUN_TERMINAL = {"done", "failed", "plan_rejected"}


def create_build_run(
    run_id: str,
    owner: str,
    repo: str,
    branch: str,
    opportunity_sig: str,
    *,
    opportunity_title: Optional[str] = None,
    status: str = "planning",
    step_count: int = 0,
) -> None:
    """Insert a fresh build_run row at the start of an execute. `run_id` is a
    caller-supplied UUID so the same opportunity can run more than once."""
    if status not in _BUILD_RUN_STATES:
        raise ValueError(f"unknown build_run status: {status!r}")
    now = int(time.time())
    c = _conn()
    c.execute(
        "INSERT OR REPLACE INTO build_runs "
        "(run_id, owner, repo, branch, opportunity_sig, opportunity_title, "
        " status, step_count, steps_completed, started_at, last_event_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
        (run_id, owner, repo, branch, opportunity_sig, opportunity_title,
         status, step_count, now, now),
    )
    c.commit()


def update_build_run(
    run_id: str,
    *,
    status: Optional[str] = None,
    plan: Optional[Any] = None,
    critique: Optional[Any] = None,
    result: Optional[Any] = None,
    pr_urls: Optional[List[str]] = None,
    step_count: Optional[int] = None,
    steps_completed: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """PATCH-style update — only the fields you pass are touched. Sets
    completed_at automatically when status becomes terminal. Best-effort
    semantics like upsert_ci_watch."""
    if status is not None and status not in _BUILD_RUN_STATES:
        raise ValueError(f"unknown build_run status: {status!r}")
    now = int(time.time())
    sets: List[str] = ["last_event_at=?"]
    vals: List[Any] = [now]
    for col, val in [
        ("status", status),
        ("plan_json", _to_json(plan) if plan is not None else None),
        ("critique_json", _to_json(critique) if critique is not None else None),
        ("result_json", _to_json(result) if result is not None else None),
        ("pr_urls", json.dumps(pr_urls) if pr_urls is not None else None),
        ("step_count", step_count),
        ("steps_completed", steps_completed),
        ("error", error),
    ]:
        if val is not None:
            sets.append(f"{col}=?")
            vals.append(val)
    if status in _BUILD_RUN_TERMINAL:
        sets.append("completed_at=?")
        vals.append(now)
    vals.append(run_id)
    c = _conn()
    c.execute(f"UPDATE build_runs SET {', '.join(sets)} WHERE run_id=?", vals)
    c.commit()


def get_build_run(run_id: str) -> Optional[Dict[str, Any]]:
    row = _conn().execute(
        "SELECT * FROM build_runs WHERE run_id=?", (run_id,),
    ).fetchone()
    if not row:
        return None
    return _build_run_row_to_dict(row)


def list_build_runs(
    *,
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    status_in: Optional[List[str]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM build_runs"
    where: List[str] = []
    args: List[Any] = []
    if owner:
        where.append("owner=?"); args.append(owner)
    if repo:
        where.append("repo=?"); args.append(repo)
    if status_in:
        ph = ",".join("?" * len(status_in))
        where.append(f"status IN ({ph})"); args.extend(status_in)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY started_at DESC LIMIT ?"
    args.append(max(1, min(int(limit), 200)))
    rows = _conn().execute(sql, args).fetchall()
    return [_build_run_row_to_dict(r) for r in rows]


def delete_build_run(run_id: str) -> bool:
    c = _conn()
    cur = c.execute("DELETE FROM build_runs WHERE run_id=?", (run_id,))
    c.commit()
    return cur.rowcount > 0


def _build_run_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    d["plan"] = _from_json(d.pop("plan_json", None))
    d["critique"] = _from_json(d.pop("critique_json", None))
    d["result"] = _from_json(d.pop("result_json", None))
    raw_urls = d.pop("pr_urls", None)
    d["pr_urls"] = _from_json(raw_urls) if raw_urls else []
    return d


# ── Test/debug helpers ──────────────────────────────────────────────────────

def reset_all() -> None:
    """Wipe all tables. ONLY for test fixtures and debug — never call from
    production paths."""
    c = _conn()
    for table in ("inflight_paths", "ci_watch_state", "ci_watch_log",
                  "finding_journal", "build_runs", "meta_kv"):
        c.execute(f"DELETE FROM {table}")
    c.commit()


def stats() -> Dict[str, int]:
    """Row counts per table. Useful for /healthz and integration tests."""
    c = _conn()
    return {
        "inflight_paths":    c.execute("SELECT COUNT(*) FROM inflight_paths").fetchone()[0],
        "ci_watch_state":    c.execute("SELECT COUNT(*) FROM ci_watch_state").fetchone()[0],
        "ci_watch_log":      c.execute("SELECT COUNT(*) FROM ci_watch_log").fetchone()[0],
        "finding_journal":   c.execute("SELECT COUNT(*) FROM finding_journal").fetchone()[0],
        "build_runs":        c.execute("SELECT COUNT(*) FROM build_runs").fetchone()[0],
    }
