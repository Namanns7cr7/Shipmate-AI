import { useState, useCallback, useEffect } from 'react';
import { Zap, Bell, GitBranch, BookOpen, Clock } from 'lucide-react';
import { useGithubAuth } from './hooks/useGithubAuth';
import { api } from './lib/api';
import { LandingPage } from './components/landing/LandingPage';
import { AppSidebar } from './components/app/AppSidebar';
import { DashboardPage } from './pages/DashboardPage';
import { RepositoriesPage } from './pages/RepositoriesPage';
import { AnalysisPage } from './pages/AnalysisPage';
import { ReportsPage } from './pages/ReportsPage';
import { Spinner } from './components/ui/GitHubConnectButton';
import type { Page } from './components/app/AppSidebar';
import type { AgentProgress, GitHubRepo, GitHubBranch, GitHubPR, ShipMateReport } from './types';

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
      setTimeout(() => setAgents(prev => prev.map(a => a.id === id ? { ...a, status: 'running' } : a)), delay),
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
      .then(r => { setRepos(r); if (r.length > 0 && !selectedRepo) setSelectedRepo(r[0]); })
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
  const lastScan = report ? new Date(report.generated_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : null;

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)', color: 'var(--ink)' }}>
      <AppSidebar
        activePage={activePage}
        onNavigate={p => { if (p === 'analysis' && !analyzing) return; setPage(p); }}
        user={auth.user}
        onLogout={auth.logout}
        repos={repos}
        selectedRepo={selectedRepo}
        onSelectRepo={r => { handleSelectRepo(r); }}
        hasReport={!!report}
      />

      <main style={{ flex: 1, height: '100vh', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        {/* Topbar */}
        <div style={{
          position: 'sticky', top: 0, zIndex: 40, height: 60,
          background: 'rgba(7,12,24,0.82)', backdropFilter: 'blur(16px)',
          borderBottom: '1px solid var(--line)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 28px',
          flexShrink: 0,
        }}>
          {/* Left: breadcrumb + chips */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
              <span className="muted">ShipMate</span>
              <span style={{ color: 'var(--ink-4)' }}>›</span>
              <span style={{ color: '#fff', fontWeight: 600, textTransform: 'capitalize' }}>
                {activePage === 'repos' ? 'Repositories' : activePage}
              </span>
            </div>
            <span style={{ width: 1, height: 18, background: 'var(--line-2)' }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {selectedRepo && (
                <>
                  <span className="mono chip tone-slate"><BookOpen size={12} /> {selectedRepo.name}</span>
                  <span className="mono chip tone-slate"><GitBranch size={12} /> {selectedBranch}</span>
                </>
              )}
              <span className="chip tone-slate">
                <Clock size={12} /> {lastScan ? `scanned ${lastScan}` : 'never scanned'}
              </span>
            </div>
          </div>

          {/* Right: run button + bell + user */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => handleAnalyze()}
              disabled={analyzing || !selectedRepo}
            >
              {analyzing ? <><Spinner size={13} /> Running…</> : <><Zap size={14} /> Run Analysis</>}
            </button>
            <button style={{ padding: 8, borderRadius: 8, background: 'none', border: 'none', color: 'var(--ink-3)', cursor: 'pointer' }}>
              <Bell size={16} />
            </button>
            {auth.user && (
              <div className="pill" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 5px 5px 11px' }}>
                <span className="dot dot-pulse" style={{ background: '#34d399' }} />
                <span className="mono" style={{ fontSize: 11.5, color: 'var(--ink-2)' }}>@{auth.user.login}</span>
                {auth.user.avatar_url
                  ? <img src={auth.user.avatar_url} alt="" style={{ width: 24, height: 24, borderRadius: 7, objectFit: 'cover' }} />
                  : <div style={{ width: 24, height: 24, borderRadius: 7, background: 'linear-gradient(135deg,#8b5cf6,#3b82f6)', display: 'grid', placeItems: 'center', fontSize: 10, fontWeight: 700, color: '#fff' }}>
                      {auth.user.login.slice(0, 2).toUpperCase()}
                    </div>
                }
              </div>
            )}
          </div>
        </div>

        {/* Page content */}
        {activePage === 'dashboard' && (
          <DashboardPage
            user={auth.user} repos={repos} report={report}
            onNavigate={setPage} onAnalyze={handleAnalyze}
          />
        )}
        {activePage === 'repos' && (
          <RepositoriesPage
            repos={repos} loadingRepos={loadingRepos} selectedRepo={selectedRepo}
            analyzing={analyzing} report={report}
            onAnalyze={handleAnalyze} onViewReport={() => setPage('reports')}
            onConnect={auth.login}
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
          <ReportsPage
            report={report}
            onReRun={() => selectedRepo ? handleAnalyze(selectedRepo) : setPage('repos')}
          />
        )}
        {activePage === 'reports' && !report && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '80vh', textAlign: 'center', padding: 24 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📊</div>
            <h2 style={{ fontSize: 20, fontWeight: 800, color: '#fff', margin: '0 0 8px' }}>No report yet</h2>
            <p style={{ fontSize: 14, color: 'var(--ink-3)', marginBottom: 24 }}>Run an analysis on a repository to generate your first report.</p>
            <button className="btn btn-primary" onClick={() => setPage('repos')}>
              Go to Repositories
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
