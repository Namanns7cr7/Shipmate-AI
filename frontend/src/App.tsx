import { useState, useCallback, useEffect } from 'react';
import { useGithubAuth } from './hooks/useGithubAuth';
import { api } from './lib/api';
import { LandingPage } from './components/landing/LandingPage';
import { AppSidebar } from './components/app/AppSidebar';
import { DashboardPage } from './pages/DashboardPage';
import { RepositoriesPage } from './pages/RepositoriesPage';
import { AnalysisPage } from './pages/AnalysisPage';
import { ReportsPage } from './pages/ReportsPage';
import type { Page } from './components/app/AppSidebar';
import type {
  AgentProgress, GitHubRepo, GitHubBranch, GitHubPR, ShipMateReport,
} from './types';

const INITIAL_AGENTS: AgentProgress[] = [
  { id: 'repo_lens',  label: 'RepoLens',  icon: '🔍', status: 'idle', description: 'Repo structure, tech stack & architecture risks' },
  { id: 'plan_forge', label: 'PlanForge', icon: '📋', status: 'idle', description: 'Delivery milestones, blockers & next actions' },
  { id: 'guardrail',  label: 'GuardRail', icon: '🔒', status: 'idle', description: 'Security findings, secrets & CORS analysis' },
  { id: 'testpilot',  label: 'TestPilot', icon: '🧪', status: 'idle', description: 'Test coverage, gaps & QA readiness' },
];

function useAgentSimulation(analyzing: boolean) {
  const [agents, setAgents] = useState<AgentProgress[]>(INITIAL_AGENTS);

  useEffect(() => {
    if (!analyzing) { setAgents(INITIAL_AGENTS); return; }
    const steps: { id: AgentProgress['id']; delay: number }[] = [
      { id: 'repo_lens',  delay: 200  },
      { id: 'plan_forge', delay: 2800 },
      { id: 'guardrail',  delay: 3200 },
      { id: 'testpilot',  delay: 3600 },
    ];
    const timers = steps.map(({ id, delay }) =>
      setTimeout(() => setAgents(prev => prev.map(a => a.id === id ? { ...a, status: 'running' } : a)), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, [analyzing]);

  function markAllComplete() { setAgents(prev => prev.map(a => ({ ...a, status: 'complete' }))); }
  function markAllError()    { setAgents(prev => prev.map(a => ({ ...a, status: a.status === 'running' ? 'error' : a.status }))); }

  return { agents, markAllComplete, markAllError };
}

export default function App() {
  const auth = useGithubAuth();

  // Navigation
  const [page, setPage] = useState<Page>('dashboard');

  // Data state
  const [repos, setRepos]                   = useState<GitHubRepo[]>([]);
  const [loadingRepos, setLoadingRepos]     = useState(false);
  const [selectedRepo, setSelectedRepo]     = useState<GitHubRepo | null>(null);
  const [_branches, setBranches]            = useState<GitHubBranch[]>([]);
  const [selectedBranch, setSelectedBranch] = useState('main');
  const [_pulls, setPulls]                  = useState<GitHubPR[]>([]);
  const [selectedPull]                      = useState<GitHubPR | null>(null);
  const [report, setReport]                 = useState<ShipMateReport | null>(null);
  const [analyzing, setAnalyzing]           = useState(false);

  const { agents, markAllComplete, markAllError } = useAgentSimulation(analyzing);

  // Load repos on auth
  useEffect(() => {
    if (!auth.isAuthenticated || !auth.accessToken) return;
    setLoadingRepos(true);
    api.getRepos(auth.accessToken)
      .then(setRepos)
      .catch(e => console.error('Failed to load repos', e))
      .finally(() => setLoadingRepos(false));
  }, [auth.isAuthenticated, auth.accessToken]);

  // Select repo + load branches/PRs
  const handleSelectRepo = useCallback(async (repo: GitHubRepo) => {
    setSelectedRepo(repo);
    setSelectedBranch(repo.default_branch || 'main');
    setBranches([]);
    setPulls([]);
    if (!auth.accessToken) return;
    const [owner, repoName] = repo.full_name.split('/');
    try {
      const [b, p] = await Promise.all([
        api.getBranches(owner, repoName, auth.accessToken),
        api.getPulls(owner, repoName, auth.accessToken),
      ]);
      setBranches(b);
      setPulls(p);
      setSelectedBranch(repo.default_branch || b[0]?.name || 'main');
    } catch (e) { console.error('Failed to load repo data', e); }
  }, [auth.accessToken]);

  // Analyze
  const handleAnalyze = useCallback(async (repo?: GitHubRepo) => {
    const target = repo ?? selectedRepo;
    if (!target || !auth.accessToken) return;

    if (repo && repo.id !== selectedRepo?.id) {
      await handleSelectRepo(repo);
    }

    setAnalyzing(true);
    setReport(null);
    setPage('analysis');

    const [owner, repoName] = target.full_name.split('/');
    try {
      const res = await api.analyze({
        owner, repo: repoName,
        branch: selectedBranch,
        access_token: auth.accessToken,
        pr_number: selectedPull?.number,
      });
      markAllComplete();
      setReport(res.report);
      setAnalyzing(false);
      setPage('reports');
    } catch (e: any) {
      markAllError();
      setAnalyzing(false);
      setPage('repos');
    }
  }, [selectedRepo, selectedBranch, selectedPull, auth.accessToken, markAllComplete, markAllError, handleSelectRepo]);

  const handleCancelAnalysis = useCallback(() => {
    setAnalyzing(false);
    setPage('repos');
  }, []);

  // ── Not authenticated ──────────────────────────────────────────────────────
  if (!auth.isAuthenticated) {
    return <LandingPage onLogin={auth.login} loading={auth.loading} error={auth.error} />;
  }

  // ── Authenticated: sidebar app ─────────────────────────────────────────────
  return (
    <div className="flex min-h-screen bg-[#080e1d] text-slate-100 font-sans" style={{ overflow: 'hidden' }}>
      {/* Left sidebar */}
      <AppSidebar
        activePage={analyzing ? 'analysis' : page}
        onNavigate={p => {
          if (p === 'analysis' && !analyzing) return;
          setPage(p);
        }}
        user={auth.user}
        onLogout={auth.logout}
      />

      {/* Main content */}
      <main className="flex-1 overflow-y-auto" style={{ height: '100vh' }}>
        {/* Top bar */}
        <div className="sticky top-0 z-40 bg-[#080e1d]/90 backdrop-blur-xl border-b border-slate-800/40 px-6 h-14 flex items-center justify-between">
          <p className="text-sm text-slate-400">
            {analyzing ? 'Analysis in Progress' :
             page === 'dashboard'  ? 'Dashboard' :
             page === 'repos'      ? 'Repositories' :
             page === 'reports'    ? 'Analysis Report' : 'ShipMate AI'}
          </p>
          {auth.user && (
            <div className="flex items-center gap-2">
              <img src={auth.user.avatar_url} alt="" className="w-6 h-6 rounded-full ring-1 ring-slate-700" />
              <span className="text-xs text-slate-400 hidden sm:block">{auth.user.login}</span>
            </div>
          )}
        </div>

        {/* Pages */}
        {analyzing && (
          <AnalysisPage
            selectedRepo={selectedRepo}
            selectedBranch={selectedBranch}
            selectedPull={selectedPull}
            agents={agents}
            onCancel={handleCancelAnalysis}
          />
        )}

        {!analyzing && page === 'dashboard' && (
          <DashboardPage
            user={auth.user}
            repos={repos}
            report={report}
            onNavigate={setPage}
          />
        )}

        {!analyzing && page === 'repos' && (
          <RepositoriesPage
            repos={repos}
            loadingRepos={loadingRepos}
            selectedRepo={selectedRepo}
            analyzing={analyzing}
            report={report}
            onAnalyze={handleAnalyze}
            onViewReport={() => setPage('reports')}
          />
        )}

        {!analyzing && page === 'reports' && report && (
          <ReportsPage
            report={report}
            onReRun={() => {
              if (selectedRepo) handleAnalyze(selectedRepo);
              else setPage('repos');
            }}
          />
        )}

        {!analyzing && page === 'reports' && !report && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-6">
            <div className="text-5xl mb-4">📊</div>
            <h2 className="text-xl font-black text-white mb-2">No report yet</h2>
            <p className="text-sm text-slate-500 mb-6">Run an analysis on one of your repositories to generate a report.</p>
            <button
              onClick={() => setPage('repos')}
              className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold transition-all"
            >
              Go to Repositories
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
