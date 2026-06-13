"""
GitHub write-side helpers for the Coder/actuate flow.

Parallel structure to GitHubAPIService (which is read-only). Splitting
writes into a dedicated module keeps the read service unchanged and makes
auditing the new write paths straightforward.

Auth: same `_headers(token)` shape as github_api_service.py. Scope `repo`
is already granted at GitHubAuthService.get_auth_url, so all of these
calls succeed without re-prompting the user.

Failure semantics: every method propagates httpx.HTTPStatusError on non-2xx
responses with the actual GitHub error body attached, so the orchestrator's
500-handler shows the real reason (e.g. branch already exists, protected
branch, file too large).

Authorization: `verify_push_access` is called at the start of every write
path. It resolves the authenticated user's login via /user, then checks
/repos/{owner}/{repo}/collaborators/{username}/permission. If the resolved
permission is not write or admin the call is rejected with a 403 before any
GitHub write API is touched.
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional, Tuple

import httpx
from fastapi import HTTPException

logger = logging.getLogger("shipmate.github_pr_service")

_BASE = "https://api.github.com"
_TIMEOUT = httpx.Timeout(20.0)

# Permissions that imply push access on GitHub
_PUSH_PERMISSIONS = {"write", "admin"}


def _headers(token: str) -> Dict[str, str]:
    # Delegates to the single shared definition (see github_client.gh_headers).
    from app.services.github_client import gh_headers
    return gh_headers(token)


async def _raise_with_body(resp: httpx.Response, action: str) -> None:
    """Raise a clean error message including GitHub's response body."""
    try:
        detail = resp.json()
        message = detail.get("message") or str(detail)
    except Exception:
        message = resp.text
    raise httpx.HTTPStatusError(
        f"GitHub {action} failed ({resp.status_code}): {message}",
        request=resp.request,
        response=resp,
    )


async def _get_authenticated_username(token: str, client: httpx.AsyncClient) -> str:
    """
    Resolve the GitHub login for the supplied token via GET /user.
    Raises HTTPException(401) if the token is invalid.
    """
    resp = await client.get(f"{_BASE}/user", headers=_headers(token))
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=401,
            detail="Could not verify GitHub identity; token may be invalid.",
        )
    login = resp.json().get("login")
    if not login:
        raise HTTPException(
            status_code=401,
            detail="GitHub /user response contained no login field.",
        )
    return login


async def verify_push_access(token: str, owner: str, repo: str) -> None:
    """
    Verify that the token's owner has at least `push` (write) permission on
    `owner/repo`.  Raises:
      - HTTPException(401) if the token cannot be resolved to a GitHub user.
      - HTTPException(403) if the user does not have write/admin permission.
      - HTTPException(404) if the repo does not exist or is not accessible.

    This must be called before any write operation that accepts owner/repo
    from the client request body.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        username = await _get_authenticated_username(token, client)

        resp = await client.get(
            f"{_BASE}/repos/{owner}/{repo}/collaborators/{username}/permission",
            headers=_headers(token),
        )

        if resp.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Repository {owner}/{repo} not found or not accessible.",
            )

        if resp.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"User '{username}' is not a collaborator on {owner}/{repo}."
                ),
            )

        if resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"GitHub permission check failed ({resp.status_code}).",
            )

        data = resp.json()
        permission = data.get("permission", "none")

        if permission not in _PUSH_PERMISSIONS:
            logger.warning(
                "Access denied: user '%s' has permission '%s' on %s/%s (need write/admin)",
                username, permission, owner, repo,
            )
            raise HTTPException(
                status_code=403,
                detail=(
                    f"User '{username}' does not have push access to {owner}/{repo}. "
                    f"Current permission: '{permission}'."
                ),
            )

        logger.info(
            "Push access verified: user '%s' has permission '%s' on %s/%s",
            username, permission, owner, repo,
        )


class GitHubPRService:

    @staticmethod
    async def get_branch_sha(token: str, owner: str, repo: str, branch: str) -> str:
        """Return the commit SHA at the tip of `branch`."""
        await verify_push_access(token, owner, repo)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/git/refs/heads/{branch}",
                headers=_headers(token),
            )
            if resp.status_code >= 400:
                await _raise_with_body(resp, f"get_branch_sha({branch})")
            data = resp.json()
            sha = data.get("object", {}).get("sha")
            if not sha:
                raise RuntimeError(f"GitHub returned no sha for {owner}/{repo}@{branch}")
            return sha

    @staticmethod
    async def create_branch(
        token: str, owner: str, repo: str, new_branch: str, base_sha: str,
    ) -> None:
        """Create a fresh ref off base_sha. 422 means the branch already exists."""
        await verify_push_access(token, owner, repo)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE}/repos/{owner}/{repo}/git/refs",
                headers=_headers(token),
                json={"ref": f"refs/heads/{new_branch}", "sha": base_sha},
            )
            if resp.status_code >= 400:
                await _raise_with_body(resp, f"create_branch({new_branch})")
            logger.info("Created branch %s/%s/%s @ %s", owner, repo, new_branch, base_sha[:7])

    @staticmethod
    async def get_file_sha(
        token: str, owner: str, repo: str, path: str, branch: str,
    ) -> Optional[str]:
        """
        Return the file's blob sha on `branch`, or None if the file does not exist.
        Used to decide whether `put_file` needs the `sha` field (update vs create).
        """
        await verify_push_access(token, owner, repo)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/contents/{path}",
                headers=_headers(token),
                params={"ref": branch},
            )
            if resp.status_code == 404:
                return None
            if resp.status_code >= 400:
                await _raise_with_body(resp, f"get_file_sha({path})")
            data = resp.json()
            return data.get("sha")

    @staticmethod
    async def put_file(
        token: str,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: Optional[str] = None,
    ) -> None:
        """
        Create or update a file via the Contents API. If `sha` is provided, the
        call updates the existing file; otherwise it creates a new file.
        """
        await verify_push_access(token, owner, repo)
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        body: Dict[str, Any] = {
            "message": message,
            "content": encoded,
            "branch": branch,
        }
        if sha is not None:
            body["sha"] = sha

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.put(
                f"{_BASE}/repos/{owner}/{repo}/contents/{path}",
                headers=_headers(token),
                json=body,
            )
            if resp.status_code >= 400:
                await _raise_with_body(resp, f"put_file({path})")
            logger.info("Wrote %s/%s/%s on %s (%s)",
                        owner, repo, path, branch, "update" if sha else "create")

    @staticmethod
    async def create_pull_request(
        token: str,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> Tuple[str, int]:
        """Open a PR. Returns (html_url, number)."""
        await verify_push_access(token, owner, repo)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE}/repos/{owner}/{repo}/pulls",
                headers=_headers(token),
                json={
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base,
                    "maintainer_can_modify": True,
                },
            )
            if resp.status_code >= 400:
                await _raise_with_body(resp, "create_pull_request")
            data = resp.json()
            url = data.get("html_url")
            number = data.get("number")
            if not url or not number:
                raise RuntimeError("GitHub PR creation returned no html_url/number")
            logger.info("Opened PR #%s %s -> %s on %s/%s", number, head, base, owner, repo)
            return url, number

    @staticmethod
    async def get_default_branch(token: str, owner: str, repo: str) -> str:
        """Fetch the repo's default branch name (used as the PR base)."""
        await verify_push_access(token, owner, repo)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}",
                headers=_headers(token),
            )
            if resp.status_code >= 400:
                await _raise_with_body(resp, "get_default_branch")
            return resp.json().get("default_branch", "main")
