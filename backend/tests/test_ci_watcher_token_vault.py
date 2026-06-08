"""The CIWatcher persists a VAULT SESSION ID to ci_watch_state, never the raw
GitHub token (Refactor #2). On restart, resume resolves the session ref back to
a real token. A row whose session no longer resolves is marked crashed, not
silently abandoned.
"""
import os

import pytest

from app.services import sqlite_store


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMATE_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("SHIPMATE_INFLIGHT_DB", raising=False)
    monkeypatch.delenv("SHIPMATE_SESSIONS_DB", raising=False)
    sqlite_store.close_all()
    from app.services import inflight_registry as ir
    from app.services import session_store
    ir.reset_all()
    session_store.reset_all()
    yield
    sqlite_store.close_all()


def _entry():
    from app.services.ci_watcher import WatchEntry
    from app.schemas.api_schemas import FindingPayload
    return WatchEntry(
        owner="o", repo="r", pr_number=42, branch="b", base_branch="main",
        access_token="ghp_REAL_secret",
        finding=FindingPayload(kind="milestone", id="M", title="x", description="d"),
        repo_lens=None, pr_url="https://github.com/o/r/pull/42",
    )


def test_persist_stores_session_ref_not_raw_token():
    from app.services.ci_watcher import CIWatcher
    from app.services import inflight_registry as ir

    entry = _entry()
    CIWatcher._persist(entry)

    row = ir.get_ci_watch("o", "r", 42)
    assert row is not None
    stored = row["access_token"]
    # The raw token must NOT be on disk; a session ref must be.
    assert stored != "ghp_REAL_secret"
    assert stored.startswith("shipmate_sess_")


def test_persisted_session_resolves_back_to_token():
    from app.services.ci_watcher import CIWatcher
    from app.services import inflight_registry as ir
    from app.services import session_store as ss

    CIWatcher._persist(_entry())
    row = ir.get_ci_watch("o", "r", 42)
    assert ss.resolve(row["access_token"]) == "ghp_REAL_secret"


def test_resume_marks_crashed_when_session_unresolvable(monkeypatch):
    """A row referencing a session that no longer resolves (vault wiped) must be
    marked crashed — never silently dropped."""
    from app.services.ci_watcher import CIWatcher
    from app.services import inflight_registry as ir
    from app.services import session_store as ss

    CIWatcher._persist(_entry())
    # Nuke the vault so the stored session ref can't resolve.
    ss.reset_all()
    # No live tasks for this key.
    CIWatcher._tasks.pop(("o", "r", 42), None)

    resumed = CIWatcher.resume_from_db()
    row = ir.get_ci_watch("o", "r", 42)
    assert row["status"] == "crashed"
    assert resumed == 0
