"""
GET /api/watcher          — list active CI watchers
GET /api/watcher/{owner}/{repo}/{pr_number} — single watcher state
DELETE /api/watcher/{owner}/{repo}/{pr_number} — stop watching

The frontend can poll /api/watcher every ~10-15s to render a live "PRs
under auto-fix" strip on the dashboard or report. No auth required to
read state — registry is in-memory and only contains finding metadata
+ token-less identifiers (the access_token is held internally, never
exposed in responses).
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.services.ci_watcher import CIWatcher

router = APIRouter(tags=["watcher"])
logger = logging.getLogger("shipmate.watcher_route")


@router.get("/watcher")
async def list_watchers() -> Dict[str, List[Dict[str, Any]]]:
    return {"active": CIWatcher.list_active()}


@router.get("/watcher/{owner}/{repo}/{pr_number}")
async def get_watcher(owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
    state = CIWatcher.get(owner, repo, pr_number)
    if state is None:
        raise HTTPException(status_code=404, detail="not watching this PR")
    return state


@router.delete("/watcher/{owner}/{repo}/{pr_number}")
async def stop_watcher(owner: str, repo: str, pr_number: int) -> Dict[str, bool]:
    return {"stopped": CIWatcher.stop(owner, repo, pr_number)}
