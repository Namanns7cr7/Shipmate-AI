from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ShipRecommendation(str, Enum):
    READY = "ready_to_ship"
    MOSTLY_READY = "mostly_ready"
    NEEDS_REVIEW = "needs_review"
    RISKY = "risky_release"
    NOT_READY = "not_ready"


# ── RepoLens ──────────────────────────────────────────────────────────────────

class ArchitectureRisk(BaseModel):
    risk: str
    impact: str   # "critical" | "high" | "medium" | "low"
    category: str  # "structure" | "deps" | "config" | "ci_cd" | "security" | "docs"


class RepoLensOutput(BaseModel):
    tech_stack: List[str]
    primary_language: str
    architecture_pattern: str   # "monolith" | "monorepo" | "microservices" | "library" | "unknown"
    key_modules: List[str]
    entry_points: List[str]
    config_files: List[str]
    has_ci_cd: bool
    has_dockerfile: bool
    has_tests: bool
    architecture_risks: List[ArchitectureRisk]
    dependency_summary: Dict[str, List[str]]   # {"python": [...], "npm": [...]}
    file_count: int
    repo_score: int  # 0-100


# ── PlanForge ─────────────────────────────────────────────────────────────────

class Milestone(BaseModel):
    title: str
    description: str
    estimated_days: int
    priority: str   # "critical" | "high" | "medium" | "low"
    category: str   # "feature" | "testing" | "security" | "ci_cd" | "infra" | "docs"
    source: str = "heuristic"        # "heuristic" | "discovery"
    rationale: Optional[str] = None  # Discovery-only: why this matters for THIS repo


class Blocker(BaseModel):
    id: str
    title: str
    description: str
    severity: str   # "critical" | "high" | "medium"
    resolution: str
    category: str
    source: str = "heuristic"
    rationale: Optional[str] = None


class PlanForgeOutput(BaseModel):
    milestones: List[Milestone]
    blockers: List[Blocker]
    dependencies: List[str]
    next_best_action: str
    estimated_effort: str
    delivery_score: int  # 0-100


# ── GuardRail ─────────────────────────────────────────────────────────────────

class SecurityFinding(BaseModel):
    id: str
    title: str
    severity: Severity
    category: str   # "secrets" | "auth" | "cors" | "injection" | "deps" | "exposure" | "config"
    description: str
    recommendation: str
    file: Optional[str] = None
    cve: Optional[str] = None
    source: str = "heuristic"        # "heuristic" | "discovery"
    rationale: Optional[str] = None  # Discovery-only: code-grounded explanation


class GuardRailOutput(BaseModel):
    findings: List[SecurityFinding]
    exposed_secrets: List[str]
    cors_issues: List[str]
    auth_risks: List[str]
    dependency_vulnerabilities: List[str]
    security_score: int  # 0-100


# ── TestPilot ─────────────────────────────────────────────────────────────────

class ExistingTests(BaseModel):
    count: int
    coverage_estimate: int  # 0-100 percent
    frameworks: List[str]
    test_files: List[str]


class SuggestedTest(BaseModel):
    name: str
    type: str       # "unit" | "integration" | "e2e" | "security" | "performance"
    priority: str   # "critical" | "high" | "medium" | "low"
    description: str
    target_file: Optional[str] = None
    source: str = "heuristic"        # "heuristic" | "discovery"
    rationale: Optional[str] = None  # Discovery-only: code-grounded explanation


class TestPilotOutput(BaseModel):
    existing_tests: ExistingTests
    missing_coverage_areas: List[str]
    suggested_tests: List[SuggestedTest]
    qa_readiness: str   # "not_ready" | "partial" | "ready"
    test_score: int     # 0-100


# ── PR Risk ───────────────────────────────────────────────────────────────────
# Unlike the four repo-level agents, PRRiskAgent judges a SPECIFIC pull request's
# diff. It only runs when the analyze request carries a pr_number; otherwise
# ShipMateReport.pr_risk stays None.

class PRRiskFactor(BaseModel):
    id: str
    title: str
    severity: Severity
    category: str   # "auth" | "migration" | "ci_cd" | "deps" | "secrets" | "injection" | "config" | "size" | "tests"
    description: str
    file: Optional[str] = None       # the changed path that grounds this factor
    evidence: Optional[str] = None   # the added diff line / surface that proves it
    source: str = "heuristic"        # "heuristic" | "discovery"
    confidence: str = "high"         # "high" | "medium" | "low"


class PRRiskOutput(BaseModel):
    pr_number: int
    title: str = ""
    files_changed: int = 0
    additions: int = 0
    deletions: int = 0
    net_lines: int = 0                       # additions - deletions
    # NOTE: unlike the repo *_score fields (higher = healthier), risk_score is
    # 0-100 where HIGHER = RISKIER (0 = trivial/safe PR). It is a standalone
    # signal and does NOT feed the deterministic readiness_score.
    risk_score: int = 0
    risk_level: str = "low"                  # "low" | "medium" | "high" | "critical"
    risk_factors: List[PRRiskFactor] = []
    risky_surfaces: List[str] = []           # sensitive areas the diff touched
    changed_files_without_tests: List[str] = []   # changed source files with no test change
    summary: str = ""
    recommendation: str = ""


# ── Aggregate ─────────────────────────────────────────────────────────────────

class AgentOutputs(BaseModel):
    repo_lens: RepoLensOutput
    plan_forge: PlanForgeOutput
    guardrail: GuardRailOutput
    testpilot: TestPilotOutput


class ScoreBreakdown(BaseModel):
    repo_score: int
    delivery_score: int
    security_score: int
    test_score: int


class RepoInfo(BaseModel):
    owner: str
    name: str
    full_name: str
    branch: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    file_count: int = 0
    html_url: str = ""


class ShipMateReport(BaseModel):
    repo: RepoInfo
    readiness_score: int
    ship_recommendation: ShipRecommendation
    score_breakdown: ScoreBreakdown
    agents: AgentOutputs
    key_blockers: List[str]
    next_actions: List[str]
    generated_at: str
    # PR-scoped risk assessment — present ONLY when a pr_number was analyzed.
    # None for a plain branch analysis (no PR to score). Optional + default None
    # keeps older stored reports valid under model_validate.
    pr_risk: Optional["PRRiskOutput"] = None
