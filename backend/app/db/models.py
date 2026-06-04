"""SQLAlchemy ORM models for persisting analysis reports."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AnalysisReport(Base):
    """Persisted analysis report record."""

    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, index=True)
    repo_owner = Column(String(255), nullable=False, index=True)
    repo_name = Column(String(255), nullable=False, index=True)
    repo_full_name = Column(String(511), nullable=False, index=True)
    branch = Column(String(255), nullable=False)
    readiness_score = Column(Float, nullable=False)
    ship_recommendation = Column(String(50), nullable=False)
    repo_score = Column(Float, nullable=False)
    delivery_score = Column(Float, nullable=False)
    security_score = Column(Float, nullable=False)
    test_score = Column(Float, nullable=False)
    report_data = Column(JSON, nullable=False)
    generated_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<AnalysisReport(repo={self.repo_full_name}, branch={self.branch}, score={self.readiness_score})>"
