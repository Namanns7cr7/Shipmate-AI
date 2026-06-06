from pydantic import BaseModel, Field
from typing import Optional, List, Literal
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


# ── Actuate (Coder agent + per-finding PR creation) ──────────────────────────

class FindingPayload(BaseModel):
    """
    Inline finding the client sends to /api/actuate. Agent-agnostic — `kind`
    distinguishes which report tab it came from. The backend doesn't keep
    report state, so the client passes everything Coder needs to act.
    """
    kind: Literal["guardrail", "milestone", "blocker", "test", "next_action"]
    id: str
    title: str
    description: str
    recommendation: str = ""
    file: Optional[str] = None
    severity: Optional[str] = None
    category: Optional[str] = None


class RepoLensSummary(BaseModel):
    """Compact RepoLens subset for Coder context — avoids re-running RepoLens."""
    primary_language: str = "Unknown"
    tech_stack: List[str] = Field(default_factory=list)
    entry_points: List[str] = Field(default_factory=list)
    has_ci_cd: bool = False
    has_tests: bool = False


class ActuateRequest(BaseModel):
    owner: str
    repo: str
    branch: str = "main"
    access_token: str
    finding: FindingPayload
    context: Optional[RepoLensSummary] = None
    open_pr: bool = True
    # Tier-2 opt-ins, both off by default (current behaviour unchanged):
    #  • diff_mode: ask Coder for unified diffs (token-saving; auto-falls back
    #    to full-file on any apply failure).
    #  • decompose: for multi-file features, plan ordered steps and run Coder
    #    once per step into one branch before opening the PR.
    diff_mode: bool = False
    decompose: bool = False


class ActuatedFile(BaseModel):
    path: str
    rationale: str


class ActuateResponse(BaseModel):
    status: str = "complete"
    pr_url: Optional[str] = None
    branch_name: str
    files_changed: List[ActuatedFile] = Field(default_factory=list)
    skipped: List[str] = Field(default_factory=list)
    summary: str = ""
