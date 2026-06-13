"""GET /api/history — score history for a repo/branch."""
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.score_history_service import get_history

router = APIRouter(tags=["history"])


class ScorePoint(BaseModel):
    id: int
    score: int
    branch: str
    recorded_at: str
    breakdown: dict


@router.get("/history")
async def score_history(
    owner: str = Query(...),
    repo: str = Query(...),
    branch: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
) -> List[ScorePoint]:
    rows = get_history(owner, repo, branch=branch, limit=limit)
    return [ScorePoint(**r) for r in rows]
