"""
session_store — the server-side token vault.

Before this, a raw GitHub access token lived in FOUR places at once:
  • frontend localStorage  (XSS-readable, never expires)
  • every request body / Authorization header  (logs, Referer, history)
  • the ci_watch_state.access_token sqlite column  (on disk in /tmp)
  • the in-memory _tokens dict in github_auth_service

This module makes the raw token live in exactly ONE place — this vault — and
hands everything else an OPAQUE session id (`shipmate_sess_<random>`) that
references it. The token never crosses the network boundary after the OAuth
exchange and is never persisted outside the vault.

Design — deliberately minimal, boundary-resolving:
  • mint(token)         → new session id, stores id→token (memory + sqlite)
  • ensure(token)       → idempotent: reuse this token's session id or mint one
  • resolve(session_id) → the real token, or None (memory first, sqlite rehydrate)
  • revoke(session_id)  / revoke_token(token) → drop the mapping
  • looks_like_session(value) → cheap prefix test so callers can tell a session
    id from a raw GitHub token without a DB hit

Resolution happens at the AUTH BOUNDARY (deps.resolve_access_token + the
body-token routes), so downstream services keep receiving a real token and
their signatures don't change. A value that ISN'T a session id passes through
untouched — that's the back-compat path for raw tokens (and every existing
test that passes "ghp_..."/"t").

Durability: the forward map is mirrored to the shared sqlite_store ("sessions"
store) so a session survives a backend restart — the CIWatcher needs to
resolve its session ref back to a token after uvicorn --reload. The in-memory
map is the fast path; sqlite rehydrates on a miss.

Security note for a hosted/multi-user deploy: this vault file
(SHIPMATE_STORE_DIR/shipmate_sessions.db) is now the ONE place a token rests at
rest — point SHIPMATE_STORE_DIR at an encrypted volume and the whole fleet's
token exposure is that single file, not four scattered surfaces.
"""
from __future__ import annotations

import logging
import secrets
import threading
import time
from typing import Dict, Optional, Tuple

from app.services import sqlite_store

logger = logging.getLogger("shipmate.session_store")

_STORE = "sessions"
_PREFIX = "shipmate_sess_"
# OAuth-app tokens don't expire, but a session should: long enough to outlive a
# CIWatcher's 45-min loop and a few restarts, short enough that a leaked id ages
# out. Default 7 days; override with SHIPMATE_SESSION_TTL_S.
import os
_DEFAULT_TTL_S = int(os.getenv("SHIPMATE_SESSION_TTL_S", str(7 * 24 * 3600)))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    token       TEXT NOT NULL,
    created_at  INTEGER NOT NULL,
    expires_at  INTEGER NOT NULL,
    scope       TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
"""

sqlite_store.register(
    _STORE,
    filename="shipmate_sessions.db",
    legacy_env="SHIPMATE_SESSIONS_DB",
    schema=_SCHEMA,
)

# In-memory fast path. Forward: id→(token, expires_at). Reverse: token→id (so
# ensure() doesn't mint a new session for a token we've already vaulted, and
# revoke_token() can find the id). Guarded by a lock — FastAPI handlers run on a
# threadpool.
_lock = threading.Lock()
_forward: Dict[str, Tuple[str, int]] = {}
_reverse: Dict[str, str] = {}


def looks_like_session(value: Optional[str]) -> bool:
    """True if `value` is one of our opaque session ids (cheap, no DB)."""
    return bool(value) and value.startswith(_PREFIX)


def _new_id() -> str:
    return _PREFIX + secrets.token_urlsafe(24)


def mint(token: str, *, scope: Optional[str] = None, ttl_s: int = _DEFAULT_TTL_S) -> str:
    """Vault `token` and return a fresh opaque session id."""
    sid = _new_id()
    now = int(time.time())
    expires_at = now + ttl_s
    with _lock:
        _forward[sid] = (token, expires_at)
        _reverse[token] = sid
    try:
        c = sqlite_store.connect(_STORE)
        c.execute(
            "INSERT OR REPLACE INTO sessions (session_id, token, created_at, expires_at, scope) "
            "VALUES (?, ?, ?, ?, ?)",
            (sid, token, now, expires_at, scope),
        )
        c.commit()
    except Exception as e:  # pragma: no cover - durability is best-effort
        logger.debug("session_store.mint sqlite mirror failed: %s", e)
    return sid


def ensure(token: str, *, scope: Optional[str] = None) -> str:
    """Return an existing (live) session id for `token`, minting one if needed.
    Idempotent so the CIWatcher persisting on every poll doesn't spawn a new
    session each time."""
    now = int(time.time())
    with _lock:
        sid = _reverse.get(token)
        if sid is not None:
            entry = _forward.get(sid)
            if entry is not None and entry[1] > now:
                return sid
            # stale — fall through to mint
    return mint(token, scope=scope)


def resolve(session_id: str) -> Optional[str]:
    """Return the real token for `session_id`, or None if unknown/expired.
    Checks the in-memory map first, then rehydrates from sqlite (so a session
    minted before a restart still resolves)."""
    if not looks_like_session(session_id):
        return None
    now = int(time.time())
    with _lock:
        entry = _forward.get(session_id)
        if entry is not None:
            token, expires_at = entry
            if expires_at > now:
                return token
            # expired — purge and miss
            _forward.pop(session_id, None)
            _reverse.pop(token, None)
            return None
    # Memory miss — try sqlite (post-restart rehydrate).
    try:
        c = sqlite_store.connect(_STORE)
        row = c.execute(
            "SELECT token, expires_at FROM sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
    except Exception as e:  # pragma: no cover
        logger.debug("session_store.resolve sqlite read failed: %s", e)
        return None
    if row is None:
        return None
    token, expires_at = row["token"], row["expires_at"]
    if expires_at <= now:
        revoke(session_id)
        return None
    # Warm the in-memory map for next time.
    with _lock:
        _forward[session_id] = (token, expires_at)
        _reverse[token] = session_id
    return token


def revoke(session_id: str) -> None:
    """Drop a session by id (logout)."""
    with _lock:
        entry = _forward.pop(session_id, None)
        if entry is not None:
            _reverse.pop(entry[0], None)
    try:
        c = sqlite_store.connect(_STORE)
        c.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
        c.commit()
    except Exception as e:  # pragma: no cover
        logger.debug("session_store.revoke sqlite delete failed: %s", e)


def revoke_token(token: str) -> None:
    """Drop whatever session references `token` (logout when we only hold the
    resolved token, not the id)."""
    with _lock:
        sid = _reverse.get(token)
    if sid:
        revoke(sid)


def purge_expired() -> int:
    """Remove expired rows (housekeeping). Returns rows removed. Best-effort."""
    now = int(time.time())
    with _lock:
        dead = [sid for sid, (_t, exp) in _forward.items() if exp <= now]
        for sid in dead:
            entry = _forward.pop(sid, None)
            if entry is not None:
                _reverse.pop(entry[0], None)
    try:
        c = sqlite_store.connect(_STORE)
        cur = c.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        c.commit()
        return cur.rowcount
    except Exception:  # pragma: no cover
        return len(dead)


def reset_all() -> None:
    """Wipe all sessions. For test fixtures only."""
    with _lock:
        _forward.clear()
        _reverse.clear()
    try:
        c = sqlite_store.connect(_STORE)
        c.execute("DELETE FROM sessions")
        c.commit()
    except Exception:  # pragma: no cover
        pass
