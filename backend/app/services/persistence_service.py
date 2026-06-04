"""Service for persisting analysis reports to database."""

from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import AnalysisReport
from app.schemas.api_schemas import ShipMateReport


def persist_report(db: Session, report: ShipMateReport) -> AnalysisReport:
    """
    Persist a ShipMateReport to the database.

    Args:
        db: SQLAlchemy session
        report: ShipMateReport object to persist

    Returns:
        AnalysisReport: The persisted database record
    """
    db_report = AnalysisReport(
        repo_owner=report.repo.owner,
        repo_name=report.repo.name,
        repo_full_name=report.repo.full_name,
        branch=report.repo.branch,
        readiness_score=report.readiness_score,
        ship_recommendation=report.ship_recommendation,
        repo_score=report.score_breakdown.repo_score,
        delivery_score=report.score_breakdown.delivery_score,
        security_score=report.score_breakdown.security_score,
        test_score=report.score_breakdown.test_score,
        report_data=report.model_dump(),
        generated_at=datetime.fromisoformat(report.generated_at.replace("Z", "+00:00")),
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


def get_report_history(
    db: Session,
    repo_full_name: str,
    limit: int = 50,
) -> list[AnalysisReport]:
    """
    Retrieve analysis report history for a repository.

    Args:
        db: SQLAlchemy session
        repo_full_name: Full repository name (owner/name)
        limit: Maximum number of records to return

    Returns:
        List of AnalysisReport records ordered by most recent first
    """
    return (
        db.query(AnalysisReport)
        .filter(AnalysisReport.repo_full_name == repo_full_name)
        .order_by(AnalysisReport.created_at.desc())
        .limit(limit)
        .all()
    )


def get_latest_report(
    db: Session,
    repo_full_name: str,
    branch: str = None,
) -> AnalysisReport | None:
    """
    Retrieve the most recent analysis report for a repository.

    Args:
        db: SQLAlchemy session
        repo_full_name: Full repository name (owner/name)
        branch: Optional branch filter

    Returns:
        AnalysisReport or None if no reports exist
    """
    query = db.query(AnalysisReport).filter(
        AnalysisReport.repo_full_name == repo_full_name
    )
    if branch:
        query = query.filter(AnalysisReport.branch == branch)
    return query.order_by(AnalysisReport.created_at.desc()).first()
