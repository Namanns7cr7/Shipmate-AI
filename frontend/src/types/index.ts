// ============================================================================
// GitHub Integration Types
// ============================================================================

export interface GitHubUser {
  login: string;
  id: number;
  avatar_url: string;
  name?: string;
  bio?: string;
  company?: string;
  public_repos?: number;
  followers?: number;
}

export interface GitHubRepository {
  id: string;
  name: string;
  full_name: string;
  description: string;
  url: string;
  language: string;
  stars: number;
  watchers: number;
  forks: number;
  is_private?: boolean;
  default_branch?: string;
  created_at?: string;
  updated_at?: string;
  tech_stack: string[];
}

export interface GitHubCommit {
  sha: string;
  message: string;
  author?: string;
  author_date?: string;
}

export interface GitHubBranch {
  name: string;
  commit: GitHubCommit;
  protected?: boolean;
}

export interface GitHubPullRequest {
  number: number;
  title: string;
  body?: string;
  state: 'open' | 'closed' | 'merged';
  author: string;
  author_avatar?: string;
  created_at: string;
  updated_at?: string;
  merged?: boolean;
  merged_at?: string;
  head_branch: string;
  base_branch: string;
  additions: number;
  deletions: number;
  changed_files: number;
  url?: string;
}

export interface GitHubIssue {
  number: number;
  title: string;
  body?: string;
  state: 'open' | 'closed';
  author: string;
  author_avatar?: string;
  created_at: string;
  updated_at?: string;
  closed_at?: string;
  labels?: string[];
  assignees?: string[];
  comments?: number;
  url?: string;
}

export interface GitHubConnection {
  success: boolean;
  access_token: string;
  token_type: string;
  scope: string;
  user: GitHubUser;
  installed_at: string;
  message?: string;
}

export type AppState = 'notConnected' | 'connecting' | 'connected' | 'repoSelected' | 'analyzing' | 'analysisComplete' | 'error';

// ============================================================================
// Repo Analysis Types
// ============================================================================

export interface RepoSummary {
  name: string;
  branch: string;
  tech_stack: string[];
  file_count: number;
  files_to_modify: string[];
  language: string;
  stars: number;
}

export interface Task {
  id: string;
  title: string;
  type: 'frontend' | 'backend' | 'database' | 'test' | 'devops';
  priority: 'high' | 'medium' | 'low';
  effort: 'S' | 'M' | 'L' | 'XL';
  description: string;
}

export interface PlannerOutput {
  frontend_tasks: Task[];
  backend_tasks: Task[];
  database_changes: Task[];
  test_requirements: Task[];
  deployment_risks: string[];
  total_story_points: number;
  recommended_sprint_count: number;
}

export interface RepoFile {
  path: string;
  risk_level: 'high' | 'medium' | 'low';
  change_type: 'modify' | 'create' | 'delete';
  reason: string;
}

export interface RepoAnalystOutput {
  files_to_change: RepoFile[];
  affected_apis: string[];
  risky_dependencies: string[];
  patterns_to_follow: string[];
  impact_score: number;
  architecture_notes: string;
}

export interface TestCase {
  id: string;
  name: string;
  type: 'unit' | 'integration' | 'e2e' | 'security';
  priority: 'high' | 'medium' | 'low';
  description: string;
  assertions: string[];
}

export interface TestGeneratorOutput {
  unit_tests: TestCase[];
  api_tests: TestCase[];
  edge_cases: TestCase[];
  regression_checklist: string[];
  total_coverage_estimate: number;
}

export interface SecurityRisk {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  description: string;
  recommendation: string;
  cve_reference?: string;
}

export interface SecurityGuardOutput {
  risks: SecurityRisk[];
  prompt_injection_risks: string[];
  exposed_secrets: string[];
  unsafe_tool_calls: string[];
  auth_bypass_risks: string[];
  dependency_warnings: string[];
  overall_security_score: number;
}

export interface SprintTask {
  day: string;
  tasks: string[];
  owner: string;
}

export interface DeliveryManagerOutput {
  sprint_plan: SprintTask[];
  standup_summary: string;
  pr_review_summary: string;
  cicd_recommendations: string[];
  release_readiness_score: number;
  next_actions: string[];
  estimated_release_date: string;
}

export interface AgentResults {
  planner: PlannerOutput;
  repo_analyst: RepoAnalystOutput;
  test_generator: TestGeneratorOutput;
  security_guard: SecurityGuardOutput;
  delivery_manager: DeliveryManagerOutput;
}

export interface AnalyzeResponse {
  repo_summary: RepoSummary;
  agents: AgentResults;
  readiness_score: number;
  recommendation: 'Ready to ship' | 'Needs fixes before shipping' | 'Major issues to address';
  summary: string;
  markdown_report: string;
  score_breakdown: Record<string, number>;
}

export type AgentName = 'planner' | 'repo_analyst' | 'test_generator' | 'security_guard' | 'delivery_manager';
export type AgentStatus = 'idle' | 'running' | 'complete' | 'error';

export interface AgentState {
  name: AgentName;
  label: string;
  icon: string;
  status: AgentStatus;
  description: string;
}
