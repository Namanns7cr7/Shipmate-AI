import {
  GitHubUser,
  GitHubRepo,
  GitHubBranch,
  GitHubPR,
  Severity,
  ShipRecommendation,
  ArchitectureRisk,
  RepoLensOutput,
  Milestone,
  Blocker,
  PlanForgeOutput,
  SecurityFinding,
  GuardRailOutput,
  ExistingTests,
  SuggestedTest,
  TestPilotOutput,
  ScoreBreakdown,
  RepoInfo,
  AgentOutputs,
  ShipMateReport,
  AnalyzeResponse,
  AppState,
  AgentStatus,
  AgentProgress,
} from '../index';

describe('Type Definitions - GitHub Auth', () => {
  it('should allow valid GitHubUser object', () => {
    const user: GitHubUser = {
      id: 1,
      login: 'testuser',
      name: 'Test User',
      avatar_url: 'https://example.com/avatar.jpg',
      html_url: 'https://github.com/testuser',
      public_repos: 10,
      followers: 100,
      following: 50,
    };
    expect(user.id).toBe(1);
    expect(user.login).toBe('testuser');
  });

  it('should allow optional GitHubUser fields', () => {
    const user: GitHubUser = {
      id: 2,
      login: 'testuser2',
      name: 'Test User 2',
      avatar_url: 'https://example.com/avatar2.jpg',
      html_url: 'https://github.com/testuser2',
      email: 'test@example.com',
      bio: 'A test user',
      company: 'Test Corp',
      location: 'Test City',
      public_repos: 5,
      followers: 50,
      following: 25,
    };
    expect(user.email).toBe('test@example.com');
    expect(user.bio).toBe('A test user');
  });

  it('should allow valid GitHubRepo object', () => {
    const repo: GitHubRepo = {
      id: 1,
      name: 'test-repo',
      full_name: 'testuser/test-repo',
      description: 'A test repository',
      html_url: 'https://github.com/testuser/test-repo',
      private: false,
      default_branch: 'main',
      language: 'TypeScript',
      stargazers_count: 100,
      forks_count: 10,
      updated_at: '2024-01-01T00:00:00Z',
      owner: { login: 'testuser', avatar_url: 'https://example.com/avatar.jpg' },
    };
    expect(repo.name).toBe('test-repo');
    expect(repo.private).toBe(false);
  });

  it('should allow null values in GitHubRepo optional fields', () => {
    const repo: GitHubRepo = {
      id: 2,
      name: 'test-repo-2',
      full_name: 'testuser/test-repo-2',
      description: null,
      html_url: 'https://github.com/testuser/test-repo-2',
      private: true,
      default_branch: 'develop',
      language: null,
      stargazers_count: 50,
      forks_count: 5,
      updated_at: null,
      owner: { login: 'testuser', avatar_url: 'https://example.com/avatar.jpg' },
    };
    expect(repo.description).toBeNull();
    expect(repo.language).toBeNull();
  });

  it('should allow valid GitHubBranch object', () => {
    const branch: GitHubBranch = {
      name: 'main',
      commit: { sha: 'abc123def456' },
      protected: true,
    };
    expect(branch.name).toBe('main');
    expect(branch.protected).toBe(true);
  });

  it('should allow valid GitHubPR object', () => {
    const pr: GitHubPR = {
      number: 1,
      title: 'Test PR',
      state: 'open',
      html_url: 'https://github.com/testuser/test-repo/pull/1',
      user: { login: 'testuser' },
      created_at: '2024-01-01T00:00:00Z',
    };
    expect(pr.number).toBe(1);
    expect(pr.state).toBe('open');
  });
});

describe('Type Definitions - Agent Outputs', () => {
  it('should allow valid Severity type', () => {
    const severities: Severity[] = ['critical', 'high', 'medium', 'low', 'info'];
    expect(severities).toHaveLength(5);
  });

  it('should allow valid ShipRecommendation type', () => {
    const recommendations: ShipRecommendation[] = [
      'ready_to_ship',
      'mostly_ready',
      'needs_review',
      'risky_release',
      'not_ready',
    ];
    expect(recommendations).toHaveLength(5);
  });

  it('should allow valid ArchitectureRisk object', () => {
    const risk: ArchitectureRisk = {
      risk: 'Monolithic structure',
      impact: 'Difficult to scale',
      category: 'Architecture',
    };
    expect(risk.risk).toBe('Monolithic structure');
  });

  it('should allow valid RepoLensOutput object', () => {
    const output: RepoLensOutput = {
      tech_stack: ['TypeScript', 'React'],
      primary_language: 'TypeScript',
      architecture_pattern: 'MVC',
      key_modules: ['auth', 'api'],
      entry_points: ['frontend/src/index.ts'],
      config_files: ['tsconfig.json'],
      has_ci_cd: true,
      has_dockerfile: true,
      has_tests: true,
      architecture_risks: [],
      dependency_summary: { dependencies: ['react', 'typescript'] },
      file_count: 100,
      repo_score: 85,
    };
    expect(output.primary_language).toBe('TypeScript');
    expect(output.repo_score).toBe(85);
  });

  it('should allow valid Milestone object', () => {
    const milestone: Milestone = {
      title: 'Phase 1',
      description: 'Initial setup',
      estimated_days: 5,
      priority: 'high',
      category: 'setup',
    };
    expect(milestone.title).toBe('Phase 1');
  });

  it('should allow valid Blocker object', () => {
    const blocker: Blocker = {
      id: 'blocker-1',
      title: 'Missing dependency',
      description: 'React is not installed',
      severity: 'critical',
      resolution: 'Run npm install',
      category: 'dependency',
    };
    expect(blocker.id).toBe('blocker-1');
  });

  it('should allow valid PlanForgeOutput object', () => {
    const output: PlanForgeOutput = {
      milestones: [],
      blockers: [],
      dependencies: ['react'],
      next_best_action: 'Install dependencies',
      estimated_effort: 'low',
      delivery_score: 75,
    };
    expect(output.delivery_score).toBe(75);
  });

  it('should allow valid SecurityFinding object', () => {
    const finding: SecurityFinding = {
      id: 'finding-1',
      title: 'SQL Injection',
      severity: 'critical',
      category: 'injection',
      description: 'Potential SQL injection vulnerability',
      recommendation: 'Use parameterized queries',
      file: 'src/db.ts',
      cve: 'CVE-2024-1234',
    };
    expect(finding.severity).toBe('critical');
  });

  it('should allow SecurityFinding without optional fields', () => {
    const finding: SecurityFinding = {
      id: 'finding-2',
      title: 'XSS Risk',
      severity: 'high',
      category: 'xss',
      description: 'Potential XSS vulnerability',
      recommendation: 'Sanitize user input',
    };
    expect(finding.file).toBeUndefined();
    expect(finding.cve).toBeUndefined();
  });

  it('should allow valid GuardRailOutput object', () => {
    const output: GuardRailOutput = {
      findings: [],
      exposed_secrets: [],
      cors_issues: [],
      auth_risks: [],
      dependency_vulnerabilities: [],
      security_score: 90,
    };
    expect(output.security_score).toBe(90);
  });

  it('should allow valid ExistingTests object', () => {
    const tests: ExistingTests = {
      count: 50,
      coverage_estimate: 75,
      frameworks: ['Jest', 'React Testing Library'],
      test_files: ['src/__tests__/index.test.ts'],
    };
    expect(tests.count).toBe(50);
  });

  it('should allow valid SuggestedTest object', () => {
    const test: SuggestedTest = {
      name: 'test_auth_flow',
      type: 'integration',
      priority: 'high',
      description: 'Test authentication flow',
      target_file: 'src/auth.ts',
    };
    expect(test.name).toBe('test_auth_flow');
  });

  it('should allow SuggestedTest without optional fields', () => {
    const test: SuggestedTest = {
      name: 'test_utils',
      type: 'unit',
      priority: 'medium',
      description: 'Test utility functions',
    };
    expect(test.target_file).toBeUndefined();
  });

  it('should allow valid TestPilotOutput object', () => {
    const output: TestPilotOutput = {
      existing_tests: { count: 50, coverage_estimate: 75, frameworks: ['Jest'], test_files: [] },
      missing_coverage_areas: ['auth', 'api'],
      suggested_tests: [],
      qa_readiness: 'good',
      test_score: 80,
    };
    expect(output.test_score).toBe(80);
  });
});

describe('Type Definitions - Report', () => {
  it('should allow valid ScoreBreakdown object', () => {
    const breakdown: ScoreBreakdown = {
      repo_score: 85,
      delivery_score: 75,
      security_score: 90,
      test_score: 80,
    };
    expect(breakdown.repo_score).toBe(85);
  });

  it('should allow valid RepoInfo object', () => {
    const info: RepoInfo = {
      owner: 'testuser',
      name: 'test-repo',
      full_name: 'testuser/test-repo',
      branch: 'main',
      description: 'A test repository',
      language: 'TypeScript',
      stars: 100,
      file_count: 50,
      html_url: 'https://github.com/testuser/test-repo',
    };
    expect(info.owner).toBe('testuser');
  });

  it('should allow RepoInfo without optional fields', () => {
    const info: RepoInfo = {
      owner: 'testuser',
      name: 'test-repo',
      full_name: 'testuser/test-repo',
      branch: 'main',
      stars: 100,
      file_count: 50,
      html_url: 'https://github.com/testuser/test-repo',
    };
    expect(info.description).toBeUndefined();
    expect(info.language).toBeUndefined();
  });

  it('should allow valid AgentOutputs object', () => {
    const outputs: AgentOutputs = {
      repo_lens: {
        tech_stack: [],
        primary_language: 'TypeScript',
        architecture_pattern: 'MVC',
        key_modules: [],
        entry_points: [],
        config_files: [],
        has_ci_cd: true,
        has_dockerfile: true,
        has_tests: true,
        architecture_risks: [],
        dependency_summary: {},
        file_count: 0,
        repo_score: 0,
      },
      plan_forge: {
        milestones: [],
        blockers: [],
        dependencies: [],
        next_best_action: '',
        estimated_effort: '',
        delivery_score: 0,
      },
      guardrail: {
        findings: [],
        exposed_secrets: [],
        cors_issues: [],
        auth_risks: [],
        dependency_vulnerabilities: [],
        security_score: 0,
      },
      testpilot: {
        existing_tests: { count: 0, coverage_estimate: 0, frameworks: [], test_files: [] },
        missing_coverage_areas: [],
        suggested_tests: [],
        qa_readiness: '',
        test_score: 0,
      },
    };
    expect(outputs.repo_lens).toBeDefined();
    expect(outputs.plan_forge).toBeDefined();
    expect(outputs.guardrail).toBeDefined();
    expect(outputs.testpilot).toBeDefined();
  });

  it('should allow valid ShipMateReport object', () => {
    const report: ShipMateReport = {
      repo: {
        owner: 'testuser',
        name: 'test-repo',
        full_name: 'testuser/test-repo',
        branch: 'main',
        stars: 100,
        file_count: 50,
        html_url: 'https://github.com/testuser/test-repo',
      },
      readiness_score: 80,
      ship_recommendation: 'ready_to_ship',
      score_breakdown: {
        repo_score: 85,
        delivery_score: 75,
        security_score: 90,
        test_score: 80,
      },
      agents: {
        repo_lens: {
          tech_stack: [],
          primary_language: 'TypeScript',
          architecture_pattern: 'MVC',
          key_modules: [],
          entry_points: [],
          config_files: [],
          has_ci_cd: true,
          has_dockerfile: true,
          has_tests: true,
          architecture_risks: [],
          dependency_summary: {},
          file_count: 0,
          repo_score: 0,
        },
        plan_forge: {
          milestones: [],
          blockers: [],
          dependencies: [],
          next_best_action: '',
          estimated_effort: '',
          delivery_score: 0,
        },
        guardrail: {
          findings: [],
          exposed_secrets: [],
          cors_issues: [],
          auth_risks: [],
          dependency_vulnerabilities: [],
          security_score: 0,
        },
        testpilot: {
          existing_tests: { count: 0, coverage_estimate: 0, frameworks: [], test_files: [] },
          missing_coverage_areas: [],
          suggested_tests: [],
          qa_readiness: '',
          test_score: 0,
        },
      },
      key_blockers: [],
      next_actions: [],
      generated_at: '2024-01-01T00:00:00Z',
    };
    expect(report.readiness_score).toBe(80);
    expect(report.ship_recommendation).toBe('ready_to_ship');
  });

  it('should allow valid AnalyzeResponse object', () => {
    const response: AnalyzeResponse = {
      status: 'success',
      report: {
        repo: {
          owner: 'testuser',
          name: 'test-repo',
          full_name: 'testuser/test-repo',
          branch: 'main',
          stars: 100,
          file_count: 50,
          html_url: 'https://github.com/testuser/test-repo',
        },
        readiness_score: 80,
        ship_recommendation: 'ready_to_ship',
        score_breakdown: {
          repo_score: 85,
          delivery_score: 75,
          security_score: 90,
          test_score: 80,
        },
        agents: {
          repo_lens: {
            tech_stack: [],
            primary_language: 'TypeScript',
            architecture_pattern: 'MVC',
            key_modules: [],
            entry_points: [],
            config_files: [],
            has_ci_cd: true,
            has_dockerfile: true,
            has_tests: true,
            architecture_risks: [],
            dependency_summary: {},
            file_count: 0,
            repo_score: 0,
          },
          plan_forge: {
            milestones: [],
            blockers: [],
            dependencies: [],
            next_best_action: '',
            estimated_effort: '',
            delivery_score: 0,
          },
          guardrail: {
            findings: [],
            exposed_secrets: [],
            cors_issues: [],
            auth_risks: [],
            dependency_vulnerabilities: [],
            security_score: 0,
          },
          testpilot: {
            existing_tests: { count: 0, coverage_estimate: 0, frameworks: [], test_files: [] },
            missing_coverage_areas: [],
            suggested_tests: [],
            qa_readiness: '',
            test_score: 0,
          },
        },
        key_blockers: [],
        next_actions: [],
        generated_at: '2024-01-01T00:00:00Z',
      },
    };
    expect(response.status).toBe('success');
    expect(response.report).toBeDefined();
  });
});

describe('Type Definitions - App State', () => {
  it('should allow valid AppState type', () => {
    const states: AppState[] = ['not_connected', 'connected', 'analyzing', 'complete', 'error'];
    expect(states).toHaveLength(5);
  });

  it('should allow valid AgentStatus type', () => {
    const statuses: AgentStatus[] = ['idle', 'running', 'complete', 'error'];
    expect(statuses).toHaveLength(4);
  });

  it('should allow valid AgentProgress object', () => {
    const progress: AgentProgress = {
      id: 'repo_lens',
      label: 'Repository Analysis',
      icon: 'analysis',
      description: 'Analyzing repository structure',
      status: 'running',
    };
    expect(progress.id).toBe('repo_lens');
    expect(progress.status).toBe('running');
  });

  it('should allow all valid AgentProgress ids', () => {
    const ids: AgentProgress['id'][] = ['repo_lens', 'plan_forge', 'guardrail', 'testpilot'];
    expect(ids).toHaveLength(4);
  });

  it('should allow all valid AgentProgress statuses', () => {
    const progress: AgentProgress = {
      id: 'plan_forge',
      label: 'Plan Forge',
      icon: 'plan',
      description: 'Creating release plan',
      status: 'idle',
    };
    expect(progress.status).toBe('idle');

    progress.status = 'running';
    expect(progress.status).toBe('running');

    progress.status = 'complete';
    expect(progress.status).toBe('complete');

    progress.status = 'error';
    expect(progress.status).toBe('error');
  });
});

describe('Type Exports', () => {
  it('should export all GitHub auth types', () => {
    expect(GitHubUser).toBeDefined();
    expect(GitHubRepo).toBeDefined();
    expect(GitHubBranch).toBeDefined();
    expect(GitHubPR).toBeDefined();
  });

  it('should export all agent output types', () => {
    expect(Severity).toBeDefined();
    expect(ShipRecommendation).toBeDefined();
    expect(ArchitectureRisk).toBeDefined();
    expect(RepoLensOutput).toBeDefined();
    expect(Milestone).toBeDefined();
    expect(Blocker).toBeDefined();
    expect(PlanForgeOutput).toBeDefined();
    expect(SecurityFinding).toBeDefined();
    expect(GuardRailOutput).toBeDefined();
    expect(ExistingTests).toBeDefined();
    expect(SuggestedTest).toBeDefined();
    expect(TestPilotOutput).toBeDefined();
  });

  it('should export all report types', () => {
    expect(ScoreBreakdown).toBeDefined();
    expect(RepoInfo).toBeDefined();
    expect(AgentOutputs).toBeDefined();
    expect(ShipMateReport).toBeDefined();
    expect(AnalyzeResponse).toBeDefined();
  });

  it('should export all app state types', () => {
    expect(AppState).toBeDefined();
    expect(AgentStatus).toBeDefined();
    expect(AgentProgress).toBeDefined();
  });
});
