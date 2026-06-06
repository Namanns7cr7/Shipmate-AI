"""
GET  /api/branches/{owner}/{repo}/prune?dry_run=true   — preview deletions
POST /api/branches/{owner}/{repo}/prune                — actually delete

Token is supplied via Authorization: Bearer <token> header.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Header

from app.services.branch_pruner import prune_shipmate_branches

router = APIRouter(tags=["branches"])
logger = logging.getLogger("shipmate.branches_route")


def _extract_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return authorization[len("Bearer "):]


@router.get("/branches/{owner}/{repo}/prune")
async def preview_prune(
    owner: str, repo: str, authorization: Optional[str] = Header(None),
):
    """Dry-run: returns what WOULD be deleted without touching anything."""
    token = _extract_token(authorization)
    try:
        report = await prune_shipmate_branches(token, owner, repo, dry_run=True)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        logger.exception("prune dry-run failed for %s/%s", owner, repo)
        raise HTTPException(status_code=500, detail=str(e)) from e
    return report.to_dict()


@router.post("/branches/{owner}/{repo}/prune")
async def execute_prune(
    owner: str, repo: str, authorization: Optional[str] = Header(None),
):
    """Actually delete the qualifying branches."""
    token = _extract_token(authorization)
    try:
        report = await prune_shipmate_branches(token, owner, repo, dry_run=False)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        logger.exception("prune execute failed for %s/%s", owner, repo)
        raise HTTPException(status_code=500, detail=str(e)) from e
    return report.to_dict()
