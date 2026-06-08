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
from fastapi import Header, HTTPException, Query

logger = logging.getLogger("shipmate.deps")

_GH = "https://api.github.com"
_PERM_TIMEOUT = httpx.Timeout(10.0)


# ── Token resolution (header preferred, legacy query fallback) ───────────────

def resolve_access_token(
    authorization: Optional[str] = Header(default=None),
    access_token: Optional[str] = Query(default=None),
) -> str:
    """Resolve the GitHub token from the Authorization header (preferred) or the
    legacy ?access_token= query param (fallback).

    Passing the token as a query param leaks it into server access logs, the
    Referer header, and browser history (OPP-001). New clients send
    `Authorization: Bearer <token>`; the query param is still accepted so
    in-flight sessions keep working during migration."""
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() in ("bearer", "token"):
            tok = parts[1].strip()
            if tok:
                return tok
    if access_token:
        return access_token
    raise HTTPException(
        status_code=401,
        detail="Missing access token. Send 'Authorization: Bearer <token>'.",
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
