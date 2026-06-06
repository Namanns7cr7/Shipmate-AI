"""
GET    /api/watcher                              — list active CI watchers (read-only, public)
GET    /api/watcher/{owner}/{repo}/{pr_number}   — single watcher state (read-only, public)
DELETE /api/watcher/{owner}/{repo}/{pr_number}   — stop watching (requires Authorization header)

The frontend can poll /api/watcher every ~10-15s to render a live "PRs under auto-fix" strip.
The access_token is held internally by CIWatcher and never exposed in responses.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header

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
async def stop_watcher(
    owner: str,
    repo: str,
    pr_number: int,
    authorization: Optional[str] = Header(None),
) -> Dict[str, bool]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return {"stopped": CIWatcher.stop(owner, repo, pr_number)}
