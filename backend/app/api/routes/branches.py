"""
GET  /api/branches/{owner}/{repo}/prune?dry_run=true   — preview deletions
POST /api/branches/{owner}/{repo}/prune                — actually delete

Both require an `access_token` query param (same pattern as the rest of
the auth-bearing routes). Returns a per-branch decision log so the UI
can render a "5 deleted, 3 kept" summary with reasons.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.services.branch_pruner import prune_shipmate_branches

router = APIRouter(tags=["branches"])
logger = logging.getLogger("shipmate.branches_route")


@router.get("/branches/{owner}/{repo}/prune")
async def preview_prune(
    owner: str, repo: str, access_token: str = Query(...),
):
    """Dry-run: returns what WOULD be deleted without touching anything."""
    try:
        report = await prune_shipmate_branches(access_token, owner, repo, dry_run=True)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        logger.exception("prune dry-run failed for %s/%s", owner, repo)
        raise HTTPException(status_code=500, detail=str(e)) from e
    return report.to_dict()


@router.post("/branches/{owner}/{repo}/prune")
async def execute_prune(
    owner: str, repo: str, access_token: str = Query(...),
):
    """Actually delete the qualifying branches."""
    try:
        report = await prune_shipmate_branches(access_token, owner, repo, dry_run=False)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        logger.exception("prune execute failed for %s/%s", owner, repo)
        raise HTTPException(status_code=500, detail=str(e)) from e
    return report.to_dict()
