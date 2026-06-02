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

  const [page, setPage]                     = useState<Page>('dashboard');
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

  useEffect(() => {
    if (!auth.isAuthenticated || !auth.accessToken) return;
    setLoadingRepos(true);
    api.getRepos(auth.accessToken)
      .then(setRepos)
      .catch(e => console.error('Failed to load repos', e))
      .finally(() => setLoadingRepos(false));
  }, [auth.isAuthenticated, auth.accessToken]);

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

  const handleAnalyze = useCallback(async (repo?: GitHubRepo) => {
    const target = repo ?? selectedRepo;
    if (!target || !auth.accessToken) return;
    if (repo && repo.id !== selectedRepo?.id) await handleSelectRepo(repo);

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
    } catch {
      markAllError();
      setAnalyzing(false);
      setPage('repos');
    }
  }, [selectedRepo, selectedBranch, selectedPull, auth.accessToken, markAllComplete, markAllError, handleSelectRepo]);

  if (!auth.isAuthenticated) {
    return <LandingPage onLogin={auth.login} loading={auth.loading} error={auth.error} />;
  }

  const activePage: Page = analyzing ? 'analysis' : page;

  return (
    <div className="flex min-h-screen bg-[#070c18] text-slate-100 font-sans overflow-hidden">
      <AppSidebar
        activePage={activePage}
        onNavigate={p => { if (p === 'analysis' && !analyzing) return; setPage(p); }}
        user={auth.user}
        onLogout={auth.logout}
      />

      <main className="flex-1 overflow-y-auto h-screen">
        {/* Topbar */}
        <div className="sticky top-0 z-40 bg-[#070c18]/95 backdrop-blur-xl border-b border-slate-800/50 px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">ShipMate AI</span>
            <span className="text-slate-700">/</span>
            <span className="text-slate-300 font-semibold capitalize">{activePage === 'repos' ? 'Repositories' : activePage === 'analysis' ? 'Analysis' : activePage}</span>
          </div>
          {auth.user && (
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs text-slate-400 hidden sm:block">@{auth.user.login}</span>
              <img src={auth.user.avatar_url} alt="" className="w-7 h-7 rounded-full ring-2 ring-slate-700" />
            </div>
          )}
        </div>

        {/* Page content */}
        {activePage === 'dashboard' && (
          <DashboardPage user={auth.user} repos={repos} report={report} onNavigate={setPage} />
        )}
        {activePage === 'repos' && (
          <RepositoriesPage
            repos={repos} loadingRepos={loadingRepos} selectedRepo={selectedRepo}
            analyzing={analyzing} report={report}
            onAnalyze={handleAnalyze} onViewReport={() => setPage('reports')}
          />
        )}
        {activePage === 'analysis' && (
          <AnalysisPage
            selectedRepo={selectedRepo} selectedBranch={selectedBranch}
            selectedPull={selectedPull} agents={agents}
            onCancel={() => { setAnalyzing(false); setPage('repos'); }}
          />
        )}
        {activePage === 'reports' && report && (
          <ReportsPage report={report} onReRun={() => selectedRepo ? handleAnalyze(selectedRepo) : setPage('repos')} />
        )}
        {activePage === 'reports' && !report && (
          <div className="flex flex-col items-center justify-center h-[80vh] text-center p-6">
            <div className="text-5xl mb-4">📊</div>
            <h2 className="text-xl font-black text-white mb-2">No report yet</h2>
            <p className="text-sm text-slate-500 mb-6">Run an analysis on a repository to generate your first report.</p>
            <button onClick={() => setPage('repos')} className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold transition-all">
              Go to Repositories
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
