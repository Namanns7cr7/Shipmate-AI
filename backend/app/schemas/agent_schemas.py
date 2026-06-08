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
    # True when the LLM discovery/enhancement path was live for this run; False
    # when it silently degraded to pure heuristics (expired creds / unreachable
    # provider). Lets the UI show a "heuristic-only" banner instead of leaving
    # the user wondering why findings look generic. Defaults True for back-compat
    # with any stored/older report that predates this field.
    ai_enhanced: bool = True


# ── Opportunity Planner (Phase 1A) ────────────────────────────────────────────
# An "opportunity" is a piece of self-improvement work ShipMate identifies for
# the repo: a new feature, an improvement to an existing one, a code-quality
# tweak, or a bug. It is the candidate input to the (Phase 1B) PlannerAgent and,
# later, the CoderOrchestrator. Phase 1A's job is ONLY to prove these are GOOD:
# grounded in real code, ranked by value, deduped against the journal — no
# planning or execution yet. The schema is intentionally "semi-plan-shaped"
# (target_files + suggested_approach) so the UI can show something actionable
# without committing to the full step-by-step plan that 1B will produce.

class Opportunity(BaseModel):
    id: str                                    # "OPP-001"
    title: str
    category: str                              # "feature" | "improvement" | "tweak" | "bug"
    description: str
    impact: str                                # what concretely gets better if shipped
    effort: str                                # "S" | "M" | "L" (rough t-shirt size)
    estimated_days: int                        # 1-21, mirrors Milestone
    target_files: List[str] = []               # semi-plan: files this would touch
    suggested_approach: List[str] = []         # semi-plan: 2-4 high-level steps (NOT a full plan)
    evidence: List[str] = []                   # grounding: file paths / constructs cited from THIS repo
    rationale: str = ""                        # WHY it matters here, citing real code
    value_score: int = 0                       # ranker output 0-100 (higher = ship sooner)
    priority: str = "medium"                   # derived from value_score: critical|high|medium|low
    grounded: bool = True                      # critic verdict: evidence verified against the repo
    journal_state: Optional[str] = None        # in_progress|shipped|dismissed|parked|None(fresh)
    source: str = "discovery"


class BuildPlanResponse(BaseModel):
    """Response of POST /api/build/plan — a ranked, grounded list of
    self-improvement opportunities for the repo. Plan-only: no PRs, no Coder."""
    owner: str
    repo: str
    branch: str = "main"
    opportunities: List[Opportunity] = []
    total_found: int = 0                       # before suppression/ranking truncation
    grounded_count: int = 0                    # how many passed deterministic grounding
    ai_enhanced: bool = True                   # False ⇒ LLM unavailable, list is empty/degraded
    generated_at: str = ""
