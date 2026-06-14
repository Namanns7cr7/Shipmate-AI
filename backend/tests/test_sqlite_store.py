"""Tests for the unified sqlite_store connection manager (Refactor #3).

Proves the three formerly-independent stores now share one connection/PRAGMA/
location policy while keeping their public behavior:
  • SHIPMATE_STORE_DIR is the single base-dir policy.
  • Per-store legacy env overrides (SHIPMATE_INFLIGHT_DB etc.) still win.
  • connect() is path-aware (re-opens when the resolved path changes).
  • Shared PRAGMAs (WAL, busy_timeout, foreign_keys) apply everywhere.
"""
import os

import pytest

from app.services import sqlite_store


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMATE_STORE_DIR", str(tmp_path))
    # Drop legacy overrides so the base-dir policy is what's under test.
    for var in ("SHIPMATE_INFLIGHT_DB", "SHIPMATE_REPORTS_DB", "OAUTH_STATE_DB"):
        monkeypatch.delenv(var, raising=False)
    sqlite_store.close_all()
    yield
    sqlite_store.close_all()


def test_all_three_stores_registered():
    # Importing the modules triggers their register() at import time.
    import app.services.inflight_registry  # noqa: F401
    import app.services.report_store  # noqa: F401
    import app.services.github_auth_service  # noqa: F401
    assert {"inflight", "reports", "oauth"} <= set(sqlite_store._REGISTRY)


def test_store_dir_policy_places_files_under_base_dir(tmp_path):
    import app.services.inflight_registry  # noqa: F401
    import app.services.report_store  # noqa: F401
    p = sqlite_store.db_path("inflight")
    assert p == os.path.join(str(tmp_path), "shipmate_inflight.db")
    assert sqlite_store.db_path("reports") == os.path.join(str(tmp_path), "shipmate_reports.db")


def test_legacy_env_override_wins(tmp_path, monkeypatch):
    import app.services.inflight_registry  # noqa: F401
    custom = str(tmp_path / "custom_inflight.db")
    monkeypatch.setenv("SHIPMATE_INFLIGHT_DB", custom)
    assert sqlite_store.db_path("inflight") == custom


def test_shared_pragmas_applied():
    import app.services.report_store  # noqa: F401
    conn = sqlite_store.connect("reports")
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"
    busy = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert busy == 5000
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1


def test_connect_is_path_aware(tmp_path, monkeypatch):
    """Repointing the legacy env var hands back a connection to the NEW file,
    not a stale handle on the old one."""
    import app.services.report_store as rs  # noqa: F401

    monkeypatch.setenv("SHIPMATE_REPORTS_DB", str(tmp_path / "a.db"))
    conn_a = sqlite_store.connect("reports")
    conn_a.execute("INSERT INTO analysis_runs "
                   "(owner, repo, branch, readiness_score, ship_recommendation, report_json, created_at) "
                   "VALUES ('o','r','main',1,'ready','{}','now')")
    conn_a.commit()

    monkeypatch.setenv("SHIPMATE_REPORTS_DB", str(tmp_path / "b.db"))
    conn_b = sqlite_store.connect("reports")
    assert conn_b is not conn_a
    # b.db is a fresh DB — the row written to a.db must not be visible.
    n = conn_b.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0]
    assert n == 0


def test_init_all_creates_every_store(tmp_path):
    import app.services.inflight_registry  # noqa: F401
    import app.services.report_store  # noqa: F401
    import app.services.github_auth_service  # noqa: F401
    sqlite_store.init_all()
    for name in ("inflight", "reports", "oauth"):
        assert os.path.exists(sqlite_store.db_path(name)), f"{name} db not created"


def test_unknown_store_raises():
    with pytest.raises(KeyError):
        sqlite_store.db_path("does-not-exist")
