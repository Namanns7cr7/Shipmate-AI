"""Tests for the server-side token vault (Refactor #2).

Proves the raw GitHub token lives in ONE place (the vault) and everything else
holds an opaque, server-resolvable session id — while raw tokens still pass
through for back-compat.
"""
import os

import pytest

from app.services import sqlite_store


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMATE_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("SHIPMATE_SESSIONS_DB", raising=False)
    sqlite_store.close_all()
    from app.services import session_store
    session_store.reset_all()
    yield
    sqlite_store.close_all()


def test_mint_returns_opaque_id_not_the_token():
    from app.services import session_store as ss
    sid = ss.mint("ghp_realsecret")
    assert sid.startswith("shipmate_sess_")
    assert "ghp_realsecret" not in sid
    assert ss.looks_like_session(sid)


def test_resolve_roundtrip():
    from app.services import session_store as ss
    sid = ss.mint("ghp_abc")
    assert ss.resolve(sid) == "ghp_abc"


def test_resolve_unknown_returns_none():
    from app.services import session_store as ss
    assert ss.resolve("shipmate_sess_nope") is None


def test_ensure_is_idempotent():
    from app.services import session_store as ss
    a = ss.ensure("ghp_tok")
    b = ss.ensure("ghp_tok")
    assert a == b, "ensure must reuse the live session for the same token"


def test_revoke_and_revoke_token():
    from app.services import session_store as ss
    sid = ss.mint("ghp_x")
    ss.revoke(sid)
    assert ss.resolve(sid) is None

    sid2 = ss.mint("ghp_y")
    ss.revoke_token("ghp_y")
    assert ss.resolve(sid2) is None


def test_looks_like_session_distinguishes_raw_tokens():
    from app.services import session_store as ss
    assert ss.looks_like_session("shipmate_sess_abc") is True
    assert ss.looks_like_session("ghp_realtoken") is False
    assert ss.looks_like_session("t") is False
    assert ss.looks_like_session(None) is False


def test_expired_session_does_not_resolve():
    from app.services import session_store as ss
    sid = ss.mint("ghp_short", ttl_s=-1)  # already expired
    assert ss.resolve(sid) is None


def test_resolve_rehydrates_from_sqlite_after_memory_loss():
    """A session minted before a 'restart' (memory cleared, sqlite intact)
    still resolves — this is what lets the CIWatcher resume."""
    from app.services import session_store as ss
    sid = ss.mint("ghp_durable")
    # Simulate a process restart: clear the in-memory maps but keep the DB.
    ss._forward.clear()
    ss._reverse.clear()
    assert ss.resolve(sid) == "ghp_durable"


# ── Boundary resolution (deps) ───────────────────────────────────────────────

def test_resolve_credential_passes_raw_token_through():
    from app.api.deps import resolve_credential
    assert resolve_credential("ghp_raw") == "ghp_raw"
    assert resolve_credential("t") == "t"


def test_resolve_credential_resolves_session_id():
    from app.api.deps import resolve_credential
    from app.services import session_store as ss
    sid = ss.mint("ghp_real")
    assert resolve_credential(sid) == "ghp_real"


def test_resolve_credential_none_for_expired_session():
    from app.api.deps import resolve_credential
    from app.services import session_store as ss
    sid = ss.mint("ghp_real", ttl_s=-1)
    assert resolve_credential(sid) is None


def test_require_body_credential_raises_on_missing_and_bad():
    from app.api.deps import require_body_credential
    from app.services import session_store as ss
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        require_body_credential(None)
    assert ei.value.status_code == 400

    with pytest.raises(HTTPException) as ei:
        require_body_credential("shipmate_sess_expired")  # unknown session
    assert ei.value.status_code == 401

    # Raw token resolves fine.
    assert require_body_credential("ghp_raw") == "ghp_raw"
    # Live session resolves to the token.
    sid = ss.mint("ghp_live")
    assert require_body_credential(sid) == "ghp_live"


# ── OAuth callback mints a session (raw token never reaches the client) ──────

def test_oauth_callback_returns_session_id_not_raw_token(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    import app.api.routes.auth as auth_mod
    from app.services import session_store as ss

    async def fake_exchange(code, state):
        return {"access_token": "ghp_THE_REAL_TOKEN", "scope": "repo", "token_type": "bearer"}

    async def fake_profile(token):
        # The callback resolves the profile with the REAL token internally.
        assert token == "ghp_THE_REAL_TOKEN"
        return {"login": "octocat"}

    monkeypatch.setattr(auth_mod.GitHubAuthService, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(auth_mod.GitHubAuthService, "get_user_profile", fake_profile)

    client = TestClient(app)
    resp = client.get("/api/auth/github/callback", params={"code": "c", "state": "s"})
    assert resp.status_code == 200
    body = resp.json()
    # The client must receive a session id, NOT the raw token.
    assert body["session_id"].startswith("shipmate_sess_")
    assert body["session_id"] != "ghp_THE_REAL_TOKEN"
    assert "ghp_THE_REAL_TOKEN" not in resp.text
    # And that session must resolve back to the real token server-side.
    assert ss.resolve(body["session_id"]) == "ghp_THE_REAL_TOKEN"
