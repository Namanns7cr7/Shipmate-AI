"""
POST /api/actuate — runs the Coder agent on a single finding and (optionally)
opens a PR back to the user's repo.

Stateless: the client passes the finding payload + minimal repo context
inline. No report cache lookup needed.
"""

import logging

import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.api_schemas import ActuateRequest, ActuateResponse
from app.services.coder_orchestrator import CoderOrchestrator

router = APIRouter(tags=["actuate"])
logger = logging.getLogger("shipmate.actuate_route")


async def _verify_repo_write_access(owner: str, repo: str, access_token: str) -> None:
    """
    Confirm that the token holder has push (write) access to owner/repo.

    Calls GET /repos/{owner}/{repo} and inspects the `permissions.push` field
    returned by the GitHub API.  Raises HTTP 403 if the user lacks write access
    or HTTP 502 if the GitHub API call itself fails unexpectedly.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)
    except httpx.RequestError as exc:
        logger.warning("GitHub repo permission check network error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Unable to reach GitHub API to verify repository access.",
        ) from exc

    if response.status_code == 404:
        raise HTTPException(
            status_code=403,
            detail=f"Repository {owner}/{repo} not found or access denied.",
        )

    if response.status_code == 403 or response.status_code == 401:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied to repository {owner}/{repo}.",
        )

    if response.status_code != 200:
        logger.warning(
            "GitHub repo permission check returned %s for %s/%s",
            response.status_code, owner, repo,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Unexpected GitHub API response ({response.status_code}) while verifying repository access.",
        )

    repo_data = response.json()
    permissions = repo_data.get("permissions", {})
    has_push = permissions.get("push", False)

    if not has_push:
        logger.warning(
            "Token lacks push access to %s/%s (permissions=%s)",
            owner, repo, permissions,
        )
        raise HTTPException(
            status_code=403,
            detail=f"You do not have write access to {owner}/{repo}.",
        )


@router.post("/actuate", response_model=ActuateResponse)
async def actuate(req: ActuateRequest) -> ActuateResponse:
    if not req.owner or not req.repo:
        raise HTTPException(status_code=400, detail="owner and repo are required")
    if not req.access_token:
        raise HTTPException(status_code=400, detail="access_token is required")

    await _verify_repo_write_access(req.owner, req.repo, req.access_token)

    try:
        return await CoderOrchestrator.run_actuation(req)
    except httpx.HTTPStatusError as e:
        logger.warning("Actuate GitHub error: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        logger.exception("Actuate failed for %s/%s finding=%s",
                         req.owner, req.repo, req.finding.id)
        raise HTTPException(status_code=500, detail=f"Actuation failed: {e}") from e
