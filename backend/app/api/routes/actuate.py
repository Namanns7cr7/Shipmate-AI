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
from app.utils.github_auth import verify_repo_write_access

router = APIRouter(tags=["actuate"])
logger = logging.getLogger("shipmate.actuate_route")


@router.post("/actuate", response_model=ActuateResponse)
async def actuate(req: ActuateRequest) -> ActuateResponse:
    if not req.owner or not req.repo:
        raise HTTPException(status_code=400, detail="owner and repo are required")
    if not req.access_token:
        raise HTTPException(status_code=400, detail="access_token is required")

    await verify_repo_write_access(req.access_token, req.owner, req.repo)

    try:
        return await CoderOrchestrator.run_actuation(req)
    except httpx.HTTPStatusError as e:
        logger.warning("Actuate GitHub error: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        logger.exception("Actuate failed for %s/%s finding=%s",
                         req.owner, req.repo, req.finding.id)
        raise HTTPException(status_code=500, detail=f"Actuation failed: {e}") from e
