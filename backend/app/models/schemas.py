from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple


class AnalyzeRequest(BaseModel):
    feature_request: str
    repo_context: Optional[str] = None


class Task(BaseModel):
    id: str
    title: str
    type: str  # frontend, backend, database, test, devops
    priority: str  # high, medium, low
    effort: str  # S, M, L, XL
    description: str


class PlannerOutput(BaseModel):
    frontend_tasks: List[Task]
    backend_tasks: List[Task]
    database_changes: List[Task]
    test_requirements: List[Task]
    deployment_risks: List[str]
    total_story_points: int
    recommended_sprint_count: int


class RepoFile(BaseModel):
    path: str
    risk_level: str  # high, medium, low
    change_type: str  # modify, create, delete
    reason: str


class RepoAnalystOutput(BaseModel):
    files_to_change: List[RepoFile]
    affected_apis: List[str]
    risky_dependencies: List[str]
    patterns_to_follow: List[str]
    impact_score: int
    architecture_notes: str


class TestCase(BaseModel):
    id: str
    name: str
    type: str  # unit, integration, e2e, security
    priority: str
    description: str
    assertions: List[str]


class TestGeneratorOutput(BaseModel):
    unit_tests: List[TestCase]
    api_tests: List[TestCase]
    edge_cases: List[TestCase]
    regression_checklist: List[str]
    total_coverage_estimate: int


class SecurityRisk(BaseModel):
    id: str
    title: str
    severity: str  # critical, high, medium, low
    category: str
    description: str
    recommendation: str
    cve_reference: Optional[str] = None


class SecurityGuardOutput(BaseModel):
    risks: List[SecurityRisk]
    prompt_injection_risks: List[str]
    exposed_secrets: List[str]
    unsafe_tool_calls: List[str]
    auth_bypass_risks: List[str]
    dependency_warnings: List[str]
    overall_security_score: int


class SprintTask(BaseModel):
    day: str
    tasks: List[str]
    owner: str


class DeliveryManagerOutput(BaseModel):
    sprint_plan: List[SprintTask]
    standup_summary: str
    pr_review_summary: str
    cicd_recommendations: List[str]
    release_readiness_score: int
    next_actions: List[str]
    estimated_release_date: str


class AgentResults(BaseModel):
    planner: PlannerOutput
    repo_analyst: RepoAnalystOutput
    test_generator: TestGeneratorOutput
    security_guard: SecurityGuardOutput
    delivery_manager: DeliveryManagerOutput


class AnalyzeResponse(BaseModel):
    readiness_score: int
    agents: AgentResults
    summary: str
    markdown_report: str
    score_breakdown: Dict[str, int]


class RepoSummary(BaseModel):
    file_tree: List[str]
    file_count: int
    detected_stack: List[str]
    readme_content: Optional[str] = None
    package_json: Optional[Dict[str, Any]] = None
    requirements_txt: Optional[str] = None
    key_files: Dict[str, str]
    repo_context: str
