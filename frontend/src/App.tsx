import { useState, useCallback, useEffect, useRef } from 'react';
import { Zap, Bell, BookOpen, Clock, Sparkles } from 'lucide-react';
import { useGithubAuth } from './hooks/useGithubAuth';
import { api } from './lib/api';
import { LandingPage } from './components/landing/LandingPage';
import { AppSidebar } from './components/app/AppSidebar';
import { DashboardPage } from './pages/DashboardPage';
import { RepositoriesPage } from './pages/RepositoriesPage';
import { AnalysisPage } from './pages/AnalysisPage';
import { ReportsPage } from './pages/ReportsPage';
import { Spinner } from './components/ui/GitHubConnectButton';
import { BranchPicker } from './components/ui/BranchPicker';
import { AutoFixDrawer } from './components/ui/AutoFixDrawer';
import type { Page } from './components/app/AppSidebar';
import type { AgentProgress, GitHubRepo, GitHubPR, ShipMateReport } from './types';

const INITIAL_AGENTS: AgentProgress[] = [
  { id: 'repo_lens',  label: 'RepoLens',  icon: '🔍', status: 'idle', description: 'Repo structure, tech stack & architecture risks' },
  { id: 'plan_forge', label: 'PlanForge', icon: '📋', status: 'idle', description: 'Delivery milestones, blockers & next actions' },
  { id: 'guardrail',  label: 'GuardRail', icon: '🔒', status: 'idle', description: 'Security findings, secrets & CORS analysis' },
  { id: 'testpilot',  label: 'TestPilot', icon: '🧪', status: 'idle', description: 'Test coverage, gaps & QA readiness' },
];

/**
 * Elapsed-time-driven progress simulation.
 *
 * Real `/api/analyze` takes ~25-40s end-to-end (RepoLens fetch + 3x heuristic
 * agents + 3x Bedrock enhance + 2x Bedrock discovery). The backend is sync —
 * no SSE / polling — so we model expected latency against a wall clock and
 * snap to 100% when the API resolves.
 *
 * Stages (cumulative wall-clock):
 *   0.0 - 0.5s   : kickoff (repo_lens spinning up)
 *   0.5 - 5s     : repo_lens running
 *   5s  - 8s     : repo_lens done, others spinning up sequentially
 *   8s  - 32s    : plan_forge / guardrail / testpilot running in stagger
 *   32s+         : hold at 95% until API resolves (markAllComplete) or errors
 *
 * Each agent gets fractional progress (0..1) within its window so
 * AgentCard can render a smooth bar instead of always-55%-while-running.
 */
const TOTAL_SIM_MS = 32_000;       // expected wall-clock for a typical analyze
const HOLD_AT_PCT = 95;            // hold here until real API resolves

interface AgentTiming {
  id: AgentProgress['id'];
  startMs: number;
  endMs: number;
}
const TIMINGS: AgentTiming[] = [
  { id: 'repo_lens',  startMs: 200,    endMs: 5_500  },
  { id: 'plan_forge', startMs: 5_500,  endMs: 22_000 },  // PlanForge does enhance + discovery
  { id: 'guardrail',  startMs: 6_500,  endMs: 26_000 },  // GuardRail does enhance + discovery
  { id: 'testpilot',  startMs: 7_500,  endMs: 30_000 },  // TestPilot now does discovery too
];

function useAgentSimulation(analyzing: boolean) {
  const [agents, setAgents] = useState<AgentProgress[]>(INITIAL_AGENTS);
  // Per-agent fractional progress (0..100). Rendered by AgentCard.
  const [progressByAgent, setProgressByAgent] = useState<Record<AgentProgress['id'], number>>({
    repo_lens: 0, plan_forge: 0, guardrail: 0, testpilot: 0,
  });
  const [overallPct, setOverallPct] = useState(0);
  const tickerRef = useRef<number | null>(null);
  const startedAtRef = useRef<number | null>(null);

  useEffect(() => {
    if (!analyzing) {
      // Reset on the next tick to avoid synchronous setState in effect body.
      const t = setTimeout(() => {
        setAgents(INITIAL_AGENTS);
        setProgressByAgent({ repo_lens: 0, plan_forge: 0, guardrail: 0, testpilot: 0 });
        setOverallPct(0);
        startedAtRef.current = null;
      }, 0);
      return () => clearTimeout(t);
    }

    startedAtRef.current = performance.now();

    const tick = () => {
      const elapsed = performance.now() - (startedAtRef.current ?? performance.now());

      // Compute per-agent status + progress.
      setAgents(prev => prev.map(a => {
        const t = TIMINGS.find(t => t.id === a.id);
        if (!t) return a;
        if (elapsed < t.startMs) return { ...a, status: 'idle' };
        if (elapsed >= t.endMs)   return { ...a, status: a.status === 'error' ? 'error' : 'running' };
        return { ...a, status: 'running' };
      }));

      const newProgress = { ...progressByAgent };
      let touched = false;
      for (const t of TIMINGS) {
        const dur = t.endMs - t.startMs;
        let p: number;
        if (elapsed < t.startMs) p = 0;
        else if (elapsed >= t.endMs) p = 95;       // never claim "complete" until API resolves
        else p = Math.round(((elapsed - t.startMs) / dur) * 95);
        if (newProgress[t.id] !== p) { newProgress[t.id] = p; touched = true; }
      }
      if (touched) setProgressByAgent(newProgress);

      // Overall = avg of per-agent, capped at HOLD_AT_PCT until API resolves.
      const avg = (newProgress.repo_lens + newProgress.plan_forge + newProgress.guardrail + newProgress.testpilot) / 4;
      setOverallPct(Math.min(HOLD_AT_PCT, Math.round(avg)));

      if (elapsed < TOTAL_SIM_MS + 60_000) {  // keep ticking (capped) for very slow runs
        tickerRef.current = requestAnimationFrame(tick);
      }
    };

    tickerRef.current = requestAnimationFrame(tick);
    return () => {
      if (tickerRef.current !== null) cancelAnimationFrame(tickerRef.current);
    };
  }, [analyzing]);  // eslint-disable-line react-hooks/exhaustive-deps

  function markAllComplete() {
    setAgents(prev => prev.map(a => ({ ...a, status: 'complete' })));
    setProgressByAgent({ repo_lens: 100, plan_forge: 100, guardrail: 100, testpilot: 100 });
    setOverallPct(100);
  }

  function markAllError() {
    setAgents(prev => prev.map(a => ({ ...a, status: a.status === 'running' ? 'error' : a.status })));
  }

  return { agents, progressByAgent, overallPct, markAllComplete, markAllError };
}

export default function App() {
  const auth = useGithubAuth();

  const [page, setPage]                     = useState<Page>('dashboard');
  const [repos, setRepos]                   = useState<GitHubRepo[]>([]);
  const [loadingRepos, setLoadingRepos]     = useState(false);
  const [selectedRepo, setSelectedRepo]     = useState<GitHubRepo | null>(null);
  const [selectedBranch, setSelectedBranch] = useState('main');
  const [selectedPull]                      = useState<GitHubPR | null>(null);
  const [report, setReport]                 = useState<ShipMateReport | null>(null);
  const [analyzing, setAnalyzing]           = useState(false);
  const [autoFixOpen, setAutoFixOpen]       = useState(false);

  const { agents, progressByAgent, overallPct, markAllComplete, markAllError } = useAgentSimulation(analyzing);

  useEffect(() => {
    if (!auth.isAuthenticated || !auth.accessToken) return;
    let cancelled = false;
    setTimeout(() => { if (!cancelled) setLoadingRepos(true); }, 0);
    api.getRepos(auth.accessToken)
      .then(r => { if (!cancelled) { setRepos(r); if (r.length > 0) setSelectedRepo(prev => prev ?? r[0]); } })
      .catch(e => console.error('Failed to load repos', e))
      .finally(() => { if (!cancelled) setLoadingRepos(false); });
    return () => { cancelled = true; };
  }, [auth.isAuthenticated, auth.accessToken]);

  const handleSelectRepo = useCallback(async (repo: GitHubRepo) => {
    setSelectedRepo(repo);
    // Pick the default branch on repo switch. The BranchPicker dropdown
    // lets the user override before analyze fires; once the user picks
    // a non-default branch it stays sticky until they switch repos.
    setSelectedBranch(repo.default_branch || 'main');
  }, []);

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
                  <BranchPicker
                    repoFullName={selectedRepo.full_name}
                    defaultBranch={selectedRepo.default_branch}
                    selected={selectedBranch}
                    onChange={setSelectedBranch}
                    accessToken={auth.accessToken}
                    disabled={analyzing}
                  />
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
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setAutoFixOpen(true)}
              disabled={analyzing || !selectedRepo}
              title="Run the autonomous fix loop: analyze → fix → pytest gate → PR → watch CI"
            >
              <Sparkles size={14} /> Auto-fix
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
            progressByAgent={progressByAgent}
            overallPct={overallPct}
            onCancel={() => { setAnalyzing(false); setPage('repos'); }}
          />
        )}
        {activePage === 'reports' && report && (
          <ReportsPage
            report={report}
            accessToken={auth.accessToken}
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

      {selectedRepo && (
        <AutoFixDrawer
          open={autoFixOpen}
          onClose={() => setAutoFixOpen(false)}
          owner={selectedRepo.full_name.split('/')[0]}
          repo={selectedRepo.name}
          branch={selectedBranch}
          accessToken={auth.accessToken}
        />
      )}
    </div>
  );
}
