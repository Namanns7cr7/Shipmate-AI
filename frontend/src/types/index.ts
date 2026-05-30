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
  readiness_score: number;
  agents: AgentResults;
  summary: string;
  markdown_report: string;
  score_breakdown: Record<string, number>;
}

export interface RepoSummary {
  file_tree: string[];
  file_count: number;
  detected_stack: string[];
  readme_content?: string;
  package_json?: Record<string, unknown>;
  requirements_txt?: string;
  key_files: Record<string, string>;
  repo_context: string;
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
