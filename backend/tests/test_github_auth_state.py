"""
Tests for the persistent OAuth state store introduced to fix SEC-004.

These tests exercise the real _store_state / _consume_state helpers from
github_auth_service so that any regression in the CSRF fix is caught.
"""

import os
import time
import pytest

# Point the state DB at a temp file so tests don't pollute the real DB
os.environ.setdefault("OAUTH_STATE_DB", ":memory:")

from app.services.github_auth_service import _store_state, _consume_state  # noqa: E402


def test_valid_state_is_consumed_and_returns_redirect_uri():
    """A freshly stored state token must be accepted and return its redirect_uri."""
    _store_state("valid-state-token", "http://localhost:5173/callback")
    result = _consume_state("valid-state-token")
    assert result == "http://localhost:5173/callback"


def test_state_is_single_use():
    """After the first consumption the token must no longer be valid."""
    _store_state("single-use-token", "http://localhost:5173/callback")
    _consume_state("single-use-token")  # first use — succeeds
    result = _consume_state("single-use-token")  # second use — must return None
    assert result is None


def test_unknown_state_returns_none():
    """A state token that was never stored must return None (not raise)."""
    result = _consume_state("completely-unknown-state-xyz")
    assert result is None


def test_expired_state_raises_value_error(monkeypatch):
    """
    A state token whose created_at is older than 600 seconds must raise
    ValueError so the OAuth flow is rejected rather than silently bypassed.
    """
    import app.services.github_auth_service as svc

    # Store a state with a timestamp 601 seconds in the past
    past_ts = time.time() - 601

    import sqlite3

    conn = sqlite3.connect(svc._get_db_path(), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_states (
            state       TEXT PRIMARY KEY,
            redirect_uri TEXT NOT NULL,
            created_at  REAL NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO oauth_states (state, redirect_uri, created_at) VALUES (?, ?, ?)",
        ("expired-state-token", "http://localhost:5173/callback", past_ts),
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="expired"):
        _consume_state("expired-state-token")
