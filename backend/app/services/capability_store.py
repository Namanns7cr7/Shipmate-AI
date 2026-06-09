"""
capability_store — persistent memory of a repo's SECURITY POSTURE over time (B3).

`_detect_security_controls` (llm_service) recomputes, from scratch on every run,
the set of controls a repo already implements (OAuth-state persistence, header
auth, CORS allowlist, security headers, webhook HMAC, …) so GuardRail stops
re-proposing them. That digest was STATELESS — recomputed and thrown away each
run — so it could tell you "these 9 controls exist NOW" but never notice DRIFT:
"CORS was locked down in run 3 — who loosened it in run 7?".

This module persists each run's detected control set per (repo, version), where
`version` is the commit SHA when known, else a deterministic fingerprint of the
analyzed corpus (so it changes exactly when the code changes — no git call
needed). Comparing the latest snapshot to the previous one yields DRIFT:

  • REGRESSED — a control present before is now absent (a security regression
    GuardRail should flag, not just silently "not detect").
  • ADDED      — a control newly present (posture improved).

So the same detection that suppresses recurrence now also feeds a trend
(dashboard) and lets GuardRail surface posture *regressions*, not just absences.

Persistence: shared sqlite_store (own table, own file). FAIL-OPEN throughout.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from typing import Any, Dict, List, Optional

from app.services import sqlite_store

logger = logging.getLogger("shipmate.capability_store")

_STORE = "capability"
_KEEP_SNAPSHOTS_PER_REPO = 50   # bound history so the table can't grow forever

_SCHEMA = """
CREATE TABLE IF NOT EXISTS capability_snapshots (
    repo_full_name  TEXT NOT NULL,
    version         TEXT NOT NULL,     -- commit sha OR corpus fingerprint
    controls_json   TEXT NOT NULL,     -- JSON array of control statements present
    control_count   INTEGER NOT NULL,
    created_at      INTEGER NOT NULL,
    PRIMARY KEY (repo_full_name, version)
);
CREATE INDEX IF NOT EXISTS idx_capability_repo ON capability_snapshots(repo_full_name, created_at);
"""

sqlite_store.register(
    _STORE,
    filename="shipmate_capability.db",
    legacy_env="SHIPMATE_CAPABILITY_DB",
    schema=_SCHEMA,
)


def _conn() -> sqlite3.Connection:
    return sqlite_store.connect(_STORE)


def init_db() -> None:
    sqlite_store.init_schema(_STORE)


# ── Version key ──────────────────────────────────────────────────────────────

def corpus_fingerprint(context: Dict[str, Any]) -> str:
    """Deterministic short fingerprint of the analyzed corpus — used as the
    snapshot version when no commit SHA is available. Hashes the sorted file
    tree + each file body so it changes exactly when the analyzed content does
    (two runs over the same commit collapse to one snapshot; an edit makes a new
    one)."""
    file_tree: List[str] = context.get("file_tree") or []
    key_files: Dict[str, str] = context.get("key_files") or {}
    h = hashlib.sha1()
    for p in sorted(file_tree):
        h.update(p.encode("utf-8", "replace"))
        h.update(b"\0")
    for path in sorted(key_files):
        h.update(path.encode("utf-8", "replace"))
        h.update(b"\0")
        h.update((key_files.get(path) or "").encode("utf-8", "replace"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def _version_for(context: Dict[str, Any]) -> str:
    """Prefer a real commit SHA if the context carries one (repo_info.sha /
    head_sha), else fall back to the corpus fingerprint."""
    info = context.get("repo_info") or {}
    for key in ("sha", "head_sha", "commit_sha"):
        v = info.get(key)
        if isinstance(v, str) and len(v) >= 7:
            return v[:40]
    return corpus_fingerprint(context)


def _repo_full(context: Dict[str, Any]) -> str:
    info = context.get("repo_info") or {}
    full = info.get("full_name")
    if full:
        return full
    owner = info.get("owner")
    owner = owner.get("login") if isinstance(owner, dict) else (owner or "")
    name = info.get("name", "")
    return f"{owner}/{name}" if owner and name else ""


# ── Record ───────────────────────────────────────────────────────────────────

def record_snapshot(
    context: Dict[str, Any], controls: List[str],
) -> Optional[Dict[str, Any]]:
    """Persist the controls detected for this run, keyed by (repo, version).
    Returns the DRIFT vs the immediately-previous snapshot (see compute_drift),
    or None on any error / missing repo. Idempotent for re-runs over the same
    version (the snapshot is replaced, drift is computed vs the prior version)."""
    repo_full = _repo_full(context)
    if not repo_full:
        return None
    version = _version_for(context)
    try:
        # Drift is measured against the most recent snapshot of a DIFFERENT
        # version (re-analyzing the same commit isn't drift).
        prev = _latest_snapshot(repo_full, exclude_version=version)
        c = _conn()
        # DO NOTHING on conflict — the FIRST analysis of a version is the
        # authoritative snapshot for it. Overwriting controls_json on a re-run
        # (e.g. a second analysis of the same SHA over a stale/partial corpus)
        # would retroactively rewrite history, so a LATER version's drift would
        # diff against a mutated prior snapshot and report phantom regressions.
        # We deliberately do NOT refresh created_at either: keeping the original
        # timestamp preserves the true ordering drift relies on.
        c.execute(
            "INSERT INTO capability_snapshots "
            "(repo_full_name, version, controls_json, control_count, created_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(repo_full_name, version) DO NOTHING",
            (repo_full, version, json.dumps(sorted(set(controls))),
             len(set(controls)), int(time.time())),
        )
        c.commit()
        _prune(repo_full)
        if prev is None:
            return {"regressed": [], "added": [], "version": version,
                    "previous_version": None}
        return compute_drift(prev["controls"], list(controls), version,
                             prev["version"])
    except Exception as e:  # pragma: no cover - store must never break analyze
        logger.debug("capability_store.record_snapshot failed (%s)", e)
        return None


def compute_drift(
    previous: List[str], current: List[str],
    version: str = "", previous_version: str = "",
) -> Dict[str, Any]:
    """Diff two control sets. `regressed` = present before, absent now (security
    regression). `added` = newly present (posture improved)."""
    prev_set, cur_set = set(previous), set(current)
    return {
        "regressed": sorted(prev_set - cur_set),
        "added": sorted(cur_set - prev_set),
        "version": version,
        "previous_version": previous_version,
    }


# ── Query ────────────────────────────────────────────────────────────────────

def _latest_snapshot(
    repo_full_name: str, exclude_version: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    rows = _conn().execute(
        "SELECT * FROM capability_snapshots WHERE repo_full_name=? "
        "ORDER BY created_at DESC LIMIT 5",
        (repo_full_name,),
    ).fetchall()
    for r in rows:
        if exclude_version is not None and r["version"] == exclude_version:
            continue
        d = dict(r)
        d["controls"] = json.loads(d.pop("controls_json"))
        return d
    return None


def latest_controls(repo_full_name: str) -> List[str]:
    """The most recent detected control set for a repo ([] if none/err)."""
    try:
        snap = _latest_snapshot(repo_full_name)
        return snap["controls"] if snap else []
    except Exception:  # pragma: no cover
        return []


def history(repo_full_name: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Snapshot history (newest first) for a repo — the posture trend surface."""
    try:
        rows = _conn().execute(
            "SELECT version, control_count, created_at FROM capability_snapshots "
            "WHERE repo_full_name=? ORDER BY created_at DESC LIMIT ?",
            (repo_full_name, max(1, min(int(limit), 200))),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:  # pragma: no cover
        return []


def regression_findings(drift: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Turn a drift dict's `regressed` controls into GuardRail-shaped finding
    seeds (title + description). Empty when there's no regression. The orchestrator
    can fold these into GuardRail output so a *removed* control is surfaced as a
    real finding instead of merely going un-detected."""
    if not drift or not drift.get("regressed"):
        return []
    out = []
    for control in drift["regressed"]:
        out.append({
            "title": "Security control regressed since last analysis",
            "description": (
                f"A control that was present in a previous analysis is no longer "
                f"detected: \"{control}\". This may be a security regression "
                f"introduced since version {drift.get('previous_version') or 'prior'}."
            ),
            "control": control,
        })
    return out


# ── Maintenance ──────────────────────────────────────────────────────────────

def _prune(repo_full_name: str) -> None:
    """Keep only the most recent N snapshots per repo."""
    try:
        c = _conn()
        c.execute(
            "DELETE FROM capability_snapshots WHERE repo_full_name=? AND version NOT IN "
            "(SELECT version FROM capability_snapshots WHERE repo_full_name=? "
            " ORDER BY created_at DESC LIMIT ?)",
            (repo_full_name, repo_full_name, _KEEP_SNAPSHOTS_PER_REPO),
        )
        c.commit()
    except Exception as e:  # pragma: no cover
        logger.debug("capability_store._prune failed (%s)", e)


def reset_all() -> None:
    try:
        c = _conn()
        c.execute("DELETE FROM capability_snapshots")
        c.commit()
    except Exception as e:  # pragma: no cover
        logger.debug("capability_store reset failed (%s)", e)


def count(repo_full_name: Optional[str] = None) -> int:
    try:
        if repo_full_name:
            return _conn().execute(
                "SELECT COUNT(*) FROM capability_snapshots WHERE repo_full_name=?",
                (repo_full_name,),
            ).fetchone()[0]
        return _conn().execute("SELECT COUNT(*) FROM capability_snapshots").fetchone()[0]
    except Exception:  # pragma: no cover
        return 0
