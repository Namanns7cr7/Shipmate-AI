"""
ReportStore — durable history of analysis runs.

Each completed `/api/analyze` run is persisted here so the dashboard can show a
repo's readiness-score trend over time (turning one-shot analysis into a
longitudinal view). Mirrors the stdlib-sqlite3 convention already used by
`github_auth_service.py` (oauth_state.db) and `inflight_registry.py`
(/tmp/shipmate_inflight.db) — no new dependency, WAL mode, file-backed so it
survives restarts and is shared across workers.

Public API:
    save_report(report) -> int          # persist one run, returns row id
    list_reports(owner, repo, limit=20) # summary rows for the history dashboard
    get_report(report_id) -> dict|None   # full stored ShipMateReport JSON

The DB path defaults to /tmp/shipmate_reports.db (same wiped-on-reboot tradeoff
as the inflight registry) and is overridable via SHIPMATE_REPORTS_DB.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("shipmate.report_store")

_DEFAULT_DB_PATH = "/tmp/shipmate_reports.db"

# One connection per thread (sqlite connections aren't safe to share across
# threads). FastAPI runs blocking handlers in a threadpool, so a thread-local
# cache keeps each worker thread on its own connection without re-opening.
_local = threading.local()


def _db_path() -> str:
    return os.getenv("SHIPMATE_REPORTS_DB", _DEFAULT_DB_PATH)


def _conn() -> sqlite3.Connection:
    cached = getattr(_local, "conn", None)
    cached_path = getattr(_local, "path", None)
    path = _db_path()
    if cached is not None and cached_path == path:
        return cached
    conn = sqlite3.connect(path, check_same_thread=False, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            owner               TEXT NOT NULL,
            repo                TEXT NOT NULL,
            branch              TEXT NOT NULL,
            readiness_score     INTEGER NOT NULL,
            ship_recommendation TEXT NOT NULL,
            report_json         TEXT NOT NULL,
            created_at          TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_repo "
        "ON analysis_runs(owner, repo, id)"
    )
    conn.commit()
    _local.conn = conn
    _local.path = path
    return conn


def save_report(report: Any) -> int:
    """Persist a completed ShipMateReport. Returns the new row id.

    `report` is a ShipMateReport pydantic model. We pull the dashboard-summary
    columns out for cheap querying and stash the full model JSON so a detail
    view can reconstruct everything. Never raises into the request path — a
    persistence failure must not fail the analysis the user already got."""
    try:
        repo_info = report.repo
        owner = getattr(repo_info, "owner", "") or ""
        name = getattr(repo_info, "name", "") or ""
        branch = getattr(repo_info, "branch", "") or ""
        rec = getattr(report, "ship_recommendation", "")
        rec_str = rec.value if hasattr(rec, "value") else str(rec)
        created_at = datetime.now(timezone.utc).isoformat()

        conn = _conn()
        cur = conn.execute(
            "INSERT INTO analysis_runs "
            "(owner, repo, branch, readiness_score, ship_recommendation, report_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                owner, name, branch,
                int(getattr(report, "readiness_score", 0) or 0),
                rec_str,
                report.model_dump_json(),
                created_at,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("report_store.save_report failed: %s", e)
        return -1


def list_reports(owner: str, repo: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Summary rows for owner/repo, newest first — feeds the trend dashboard.
    Returns lightweight dicts (no full report_json) for a compact list payload."""
    try:
        limit = max(1, min(int(limit), 200))
        conn = _conn()
        rows = conn.execute(
            "SELECT id, owner, repo, branch, readiness_score, ship_recommendation, created_at "
            "FROM analysis_runs WHERE owner = ? AND repo = ? "
            "ORDER BY id DESC LIMIT ?",
            (owner, repo, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("report_store.list_reports failed: %s", e)
        return []


def get_report(report_id: int) -> Optional[Dict[str, Any]]:
    """Return the full stored report (parsed JSON) for a single run, or None."""
    try:
        import json
        conn = _conn()
        row = conn.execute(
            "SELECT report_json FROM analysis_runs WHERE id = ?",
            (int(report_id),),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["report_json"])
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("report_store.get_report failed: %s", e)
        return None
