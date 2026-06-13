"""
Shared FastAPI dependencies — auth-token resolution + repo write-access checks.

Extracted so route modules stop each defining their own copy. Before this,
_verify_repo_write_access existed independently in analysis.py and actuate.py
(with different parameter orders), and build.py reached across to import
analysis.py's — cross-module coupling between peer routes. resolve_access_token
likewise lived in auth.py. One home, one implementation, imported everywhere.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import Header, HTTPException

from app.services import session_store

logger = logging.getLogger("shipmate.deps")

_GH = "https://api.github.com"
_PERM_TIMEOUT = httpx.Timeout(10.0)


# ── Credential resolution (session vault → real token) ───────────────────────

def resolve_credential(value: Optional[str]) -> Optional[str]:
    """Turn an opaque value into a real GitHub token.

    The frontend holds a session id (`shipmate_sess_…`) that references the
    vaulted token, never the raw token itself. This resolves that id back to
    the token at the auth boundary so every downstream service keeps receiving
    a real token (no signature changes anywhere).

    A value that ISN'T a session id passes through untouched — that's the
    back-compat path for legacy clients (and tests) that still send a raw
    `ghp_…`/`token` string. Returns None for an empty/unknown/expired session."""
    if not value:
        return None
    if session_store.looks_like_session(value):
        return session_store.resolve(value)   # None if unknown/expired
    return value  # raw token — back-compat passthrough


def require_body_credential(value: Optional[str]) -> str:
    """Resolve a credential carried in a request BODY (request.access_token)
    into a real token, raising 400/401 like the routes already do.

    Body-token routes call this once at the top and overwrite
    request.access_token with the returned real token, so every downstream
    service stays unchanged. Raises 400 if nothing was supplied, 401 if a
    session id was supplied but didn't resolve (expired/unknown)."""
    if not value:
        raise HTTPException(status_code=400, detail="access_token is required.")
    resolved = resolve_credential(value)
    if not resolved:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid. Please sign in again.",
        )
    return resolved


def resolve_access_token(
    authorization: Optional[str] = Header(default=None),
) -> str:
    """Resolve the credential from the Authorization header ONLY. The header
    carries an opaque SESSION ID (shipmate_sess_…) resolved to the real token
    via the vault; a raw token is still accepted (back-compat) and passed
    through.

    The legacy `?access_token=` query-param source was REMOVED: a token (even a
    session id) in the URL leaks into server access logs, the Referer header,
    and browser history (OPP-001), and GuardRail correctly kept flagging the
    surface. The frontend has always sent `Authorization: Bearer` via the axios
    interceptor, so nothing relied on the query path."""
    candidate: Optional[str] = None
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() in ("bearer", "token"):
            tok = parts[1].strip()
            if tok:
                candidate = tok

    resolved = resolve_credential(candidate)
    if resolved:
        return resolved
    # A session id that didn't resolve (expired/unknown) is a 401 — distinct
    # from "nothing supplied" but the same status to the client.
    raise HTTPException(
        status_code=401,
        detail="Missing or invalid access credential. Send 'Authorization: Bearer <session_id>'.",
    )


# ── Repo write-access verification ───────────────────────────────────────────

async def verify_repo_write_access(owner: str, repo: str, access_token: str) -> None:
    """Confirm the token holder has push (write) access to owner/repo via the
    GitHub repo API's `permissions` object.

    Raises HTTP 403 if the token lacks write access (or the repo is not visible),
    401 if the token is invalid, 404 if the repo doesn't exist, 502 on a GitHub
    API / network failure. Single canonical implementation — all routes import
    this rather than re-defining their own."""
    url = f"{_GH}/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with httpx.AsyncClient(timeout=_PERM_TIMEOUT) as client:
            response = await client.get(url, headers=headers)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to reach GitHub API to verify repository access: {exc}",
        )

    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{owner}/{repo}' not found or not accessible with the provided token.",
        )
    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="GitHub token is invalid or expired.")
    if response.status_code not in (200, 301):
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API returned unexpected status {response.status_code} while checking repository access.",
        )

    permissions: dict = response.json().get("permissions", {})
    has_write = (
        permissions.get("admin") is True
        or permissions.get("maintain") is True
        or permissions.get("push") is True
    )
    if not has_write:
        raise HTTPException(
            status_code=403,
            detail=(
                f"The authenticated token does not have write access to '{owner}/{repo}'. "
                "Only repositories where you have push, maintain, or admin permission "
                "may be used."
            ),
        )
