// ── GitHub auth ───────────────────────────────────────────────────────────────

export interface GitHubUser {
  id: number;
  login: string;
  name: string;
  avatar_url: string;
  html_url: string;
  email?: string;
  bio?: string;
  company?: string;
  location?: string;
  public_repos: number;
  followers: number;
  following: number;
}

export interface GitHubRepo {
  id: number;
  name: string;
  full_name: string;
  description: string | null;
  html_url: string;
  private: boolean;
  default_branch: string;
  language: string | null;
  stargazers_count: number;
  forks_count: number;
  updated_at: string | null;
  owner: { login: string; avatar_url: string };
}

export interface GitHubBranch {
  name: string;
  commit: { sha: string };
  protected: boolean;
}

export interface GitHubPR {
  number: number;
  title: string;
  state: string;
  html_url: string;
  user: { login: string };
  created_at: string;
}

// ── Agent outputs ─────────────────────────────────────────────────────────────

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type ShipRecommendation =
  | 'ready_to_ship'
  | 'mostly_ready'
  | 'needs_review'
  | 'risky_release'
  | 'not_ready';

export interface ArchitectureRisk {
  risk: string;
  impact: string;
  category: string;
}

export interface RepoLensOutput {
  tech_stack: string[];
  primary_language: string;
  architecture_pattern: string;
  key_modules: string[];
  entry_points: string[];
  config_files: string[];
  has_ci_cd: boolean;
  has_dockerfile: boolean;
  has_tests: boolean;
  architecture_risks: ArchitectureRisk[];
  dependency_summary: Record<string, string[]>;
  file_count: number;
  repo_score: number;
}

export interface Milestone {
  title: string;
  description: string;
  estimated_days: number;
  priority: string;
  category: string;
}

export interface Blocker {
  id: string;
  title: string;
  description: string;
  severity: string;
  resolution: string;
  category: string;
}

export interface PlanForgeOutput {
  milestones: Milestone[];
  blockers: Blocker[];
  dependencies: string[];
  next_best_action: string;
  estimated_effort: string;
  delivery_score: number;
}

export interface SecurityFinding {
  id: string;
  title: string;
  severity: Severity;
  category: string;
  description: string;
  recommendation: string;
  file?: string;
  cve?: string;
}

export interface GuardRailOutput {
  findings: SecurityFinding[];
  exposed_secrets: string[];
  cors_issues: string[];
  auth_risks: string[];
  dependency_vulnerabilities: string[];
  security_score: number;
}

export interface ExistingTests {
  count: number;
  coverage_estimate: number;
  frameworks: string[];
  test_files: string[];
}

export interface SuggestedTest {
  name: string;
  type: string;
  priority: string;
  description: string;
  target_file?: string;
}

export interface TestPilotOutput {
  existing_tests: ExistingTests;
  missing_coverage_areas: string[];
  suggested_tests: SuggestedTest[];
  qa_readiness: string;
  test_score: number;
}

// ── Report ────────────────────────────────────────────────────────────────────

export interface ScoreBreakdown {
  repo_score: number;
  delivery_score: number;
  security_score: number;
  test_score: number;
}

export interface RepoInfo {
  owner: string;
  name: string;
  full_name: string;
  branch: string;
  description?: string;
  language?: string;
  stars: number;
  file_count: number;
  html_url: string;
}

export interface AgentOutputs {
  repo_lens: RepoLensOutput;
  plan_forge: PlanForgeOutput;
  guardrail: GuardRailOutput;
  testpilot: TestPilotOutput;
}

export interface ShipMateReport {
  repo: RepoInfo;
  readiness_score: number;
  ship_recommendation: ShipRecommendation;
  score_breakdown: ScoreBreakdown;
  agents: AgentOutputs;
  key_blockers: string[];
  next_actions: string[];
  generated_at: string;
}

export interface AnalyzeResponse {
  status: string;
  report: ShipMateReport;
}

// ── Analysis History ──────────────────────────────────────────────────────────

export interface AnalysisHistoryRecord {
  id: string;
  repo: string;
  readiness_score: number;
  ship_recommendation: ShipRecommendation;
  score_breakdown: ScoreBreakdown;
  created_at: string;
}

export interface AnalysisHistoryResponse {
  repo: string;
  history: AnalysisHistoryRecord[];
  total_count: number;
}

// ── App state ─────────────────────────────────────────────────────────────────

export type AppState =
  | 'not_connected'
  | 'connected'
  | 'analyzing'
  | 'complete'
  | 'error';

export type AgentStatus = 'idle' | 'running' | 'complete' | 'error';

export interface AgentProgress {
  id: 'repo_lens' | 'plan_forge' | 'guardrail' | 'testpilot';
  label: string;
  icon: string;
  description: string;
  status: AgentStatus;
}
