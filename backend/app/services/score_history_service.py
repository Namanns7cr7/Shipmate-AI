"""
SQLite-backed score history — stores one row per analysis run.
Used by the dashboard sparkline and the /api/history endpoint.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("shipmate.score_history")

_DB_PATH = os.getenv("SCORE_HISTORY_DB", "score_history.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS score_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                owner       TEXT    NOT NULL,
                repo        TEXT    NOT NULL,
                branch      TEXT    NOT NULL DEFAULT 'main',
                score       INTEGER NOT NULL,
                breakdown   TEXT    NOT NULL DEFAULT '{}',
                recorded_at TEXT    NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_repo ON score_history(owner, repo, branch)")


def record_score(
    owner: str,
    repo: str,
    branch: str,
    score: int,
    breakdown: Optional[Dict[str, int]] = None,
) -> None:
    init_db()
    with _conn() as c:
        c.execute(
            "INSERT INTO score_history (owner, repo, branch, score, breakdown, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                owner, repo, branch, score,
                json.dumps(breakdown or {}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def get_history(
    owner: str,
    repo: str,
    branch: Optional[str] = None,
    limit: int = 30,
) -> List[Dict]:
    """Return the last `limit` score entries for owner/repo, newest first."""
    init_db()
    with _conn() as c:
        if branch:
            rows = c.execute(
                "SELECT * FROM score_history WHERE owner=? AND repo=? AND branch=? "
                "ORDER BY id DESC LIMIT ?",
                (owner, repo, branch, limit),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM score_history WHERE owner=? AND repo=? "
                "ORDER BY id DESC LIMIT ?",
                (owner, repo, limit),
            ).fetchall()
    return [dict(r) for r in reversed(rows)]  # oldest→newest for sparkline
