from pydantic import BaseModel
from typing import Optional, List
from .agent_schemas import ShipMateReport


class AnalyzeRequest(BaseModel):
    owner: str
    repo: str
    branch: str = "main"
    pr_number: Optional[int] = None
    access_token: str
    feature_context: Optional[str] = None


class AnalyzeResponse(BaseModel):
    status: str = "complete"
    report: ShipMateReport


class RepoSummary(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    private: bool = False
    default_branch: str = "main"
    language: Optional[str] = None
    stargazers_count: int = 0
    forks_count: int = 0
    updated_at: Optional[str] = None
    owner: dict = {}
