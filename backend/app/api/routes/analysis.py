from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import AnalysisRun
from app.services.persistence_service import PersistenceService

router = APIRouter()
persistence_service = PersistenceService()


@router.get("/repos/{repo}/history")
def get_analysis_history(
    repo: str,
    limit: int = Query(50, ge=1, le=500),
    days: int = Query(90, ge=1, le=3650),
):
    """
    Retrieve historical analysis runs for a given repository.
    
    Args:
        repo: Repository identifier (e.g., 'owner/name')
        limit: Maximum number of records to return (default 50, max 500)
        days: Look back window in days (default 90, max 3650)
    
    Returns:
        List of analysis records with timestamps and scores, ordered by date descending.
    """
    db = next(get_db())
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        records = (
            db.query(AnalysisRun)
            .filter(
                AnalysisRun.repo_identifier == repo,
                AnalysisRun.created_at >= cutoff_date,
            )
            .order_by(AnalysisRun.created_at.desc())
            .limit(limit)
            .all()
        )
        
        if not records:
            return {
                "repo": repo,
                "history": [],
                "total_count": 0,
            }
        
        history = [
            {
                "id": record.id,
                "repo": record.repo_identifier,
                "readiness_score": record.readiness_score,
                "ship_recommendation": record.ship_recommendation,
                "score_breakdown": record.score_breakdown,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
            for record in records
        ]
        
        return {
            "repo": repo,
            "history": history,
            "total_count": len(history),
        }
    finally:
        db.close()
