import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Menu,
  X,
  ChevronRight,
  Loader,
  AlertCircle,
  Code,
  Zap,
} from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { AgentSwarm } from './components/AgentSwarm';
import { ReadinessScore } from './components/ReadinessScore';
import { ReportTabs } from './components/ReportTabs';
import { GitHubConnectButton } from './components/GitHubConnectButton';
import { LandingPage } from './components/LandingPage';
import { GitHubUserProfile } from './components/GitHubUserProfile';
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
  { id: 'repo_lens', label: 'RepoLens', icon: '🔍', status: 'idle', description: 'Repo structure, tech stack & architecture risks' },
  { id: 'plan_forge', label: 'PlanForge', icon: '📋', status: 'idle', description: 'Delivery milestones, blockers & next actions' },
  { id: 'guardrail', label: 'GuardRail', icon: '🔒', status: 'idle', description: 'Security findings, secrets & CORS analysis' },
  { id: 'testpilot', label: 'TestPilot', icon: '🧪', status: 'idle', description: 'Test coverage, gaps & QA readiness' },
];

function useAgentSimulation(analyzing: boolean) {
  const [agents, setAgents] = useState<AgentProgress[]>(INITIAL_AGENTS);

  useEffect(() => {
    if (!analyzing) { setAgents(INITIAL_AGENTS); return; }
    const steps: { id: AgentProgress['id']; delay: number }[] = [
      { id: 'repo_lens', delay: 200 },
      { id: 'plan_forge', delay: 2800 },
      { id: 'guardrail', delay: 3200 },
      { id: 'testpilot', delay: 3600 },
    ];
    const timers = steps.map(({ id, delay }) =>
      setTimeout(() => setAgents(prev => prev.map(a => a.id === id ? { ...a, status: 'running' } : a)), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, [analyzing]);

  function markAllComplete() { setAgents(prev => prev.map(a => ({ ...a, status: 'complete' }))); }
  function markAllError() { setAgents(prev => prev.map(a => ({ ...a, status: a.status === 'running' ? 'error' : a.status }))); }

  return { agents, markAllComplete, markAllError };
}

export default function App() {
  const auth = useGithubAuth();

  // ========== App State ==========
  const [appState, setAppState] = useState<AppState>('notConnected');

  // Repository & branch selection
  const [repos, setRepos] = useState<GitHubRepository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepository | null>(null);
  const [branches, setBranches] = useState<GitHubBranch[]>([]);
  const [selectedBranch, setSelectedBranch] = useState<string>('main');

  // PR & Issue selection
  const [pulls, setPulls] = useState<any[]>([]);
  const [selectedPull, setSelectedPull] = useState<any | null>(null);
  const [issues, setIssues] = useState<any[]>([]);
  const [selectedIssue, setSelectedIssue] = useState<any | null>(null);

  // Feature & analysis
  const [featureRequest, setFeatureRequest] = useState<string>(SAMPLE_FEATURE_REQUEST);
  const [agents, setAgents] = useState<AgentState[]>(INITIAL_AGENTS);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);

  // UI state
  const [error, setError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const updateAgentStatus = useCallback((name: AgentName, status: AgentState['status']) => {
    setAgents(prev => prev.map(a => a.name === name ? { ...a, status } : a));
  }, []);

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

  // ========== Refresh auth after callback ==========
  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('github_access_token');
      if (token && !githubAuth.isAuthenticated) {
        githubAuth.refreshAuth();
      }
    };

    // Check on window focus (for when callback page redirects)
    window.addEventListener('focus', checkAuth);
    return () => window.removeEventListener('focus', checkAuth);
  }, [githubAuth]);

  // Show loading state
  if (githubAuth.loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950">
        <div className="text-center">
          <Loader size={48} className="animate-spin text-blue-400 mx-auto mb-4" />
          <p className="text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Landing page (not connected) — full screen, no app shell
  if (appState === 'notConnected' && !githubAuth.isAuthenticated) {
    return (
      <LandingPage
        onLogin={githubAuth.initiateLogin}
        loginLoading={githubAuth.loading}
        loginError={githubAuth.error}
      />
    );
  }

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
              page === 'dashboard' ? 'Dashboard' :
                page === 'repos' ? 'Repositories' :
                  page === 'reports' ? 'Analysis Report' : 'ShipMate AI'}
          </p>
          {auth.user && (
            <div className="flex items-center gap-2">
              <img src={auth.user.avatar_url} alt="" className="w-6 h-6 rounded-full ring-1 ring-slate-700" />
              <span className="text-xs text-slate-400 hidden sm:block">{auth.user.login}</span>
            </div>

            {/* User Profile or Connect Button */}
          {githubAuth.isAuthenticated && githubAuth.user ? (
            <GitHubUserProfile
              user={githubAuth.user}
              onLogout={handleLogout}
              loading={githubAuth.loading}
            />
          ) : null}
        </div>
      </header>

      {/* ========== Content Area ========== */}
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          <AnimatePresence mode="wait">

            {/* ========== REPOSITORY SELECTION STATE ========== */}
            {appState === 'connected' && !selectedRepo && githubAuth.isAuthenticated && (
              <motion.div
                key="repo-list"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                <h2 className="text-2xl font-bold text-white mb-6">Your Repositories</h2>

                {repos.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-slate-400">No repositories found</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {repos.map(repo => (
                      <motion.button
                        key={repo.id}
                        onClick={() => handleSelectRepository(repo)}
                        whileHover={{ scale: 1.02 }}
                        className="p-4 rounded-lg border border-slate-700 bg-slate-800/50 hover:bg-slate-800 transition text-left"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <Code size={24} className="text-blue-400" />
                          {repo.is_private && (
                            <span className="text-xs bg-slate-700 px-2 py-1 rounded">Private</span>
                          )}
                        </div>
                        <h3 className="font-semibold text-white mb-1">{repo.name}</h3>
                        <p className="text-xs text-slate-400 mb-3 line-clamp-2">
                          {repo.description || 'No description'}
                        </p>
                        <div className="flex items-center gap-4 text-xs text-slate-500">
                          {repo.language && <span>{repo.language}</span>}
                          <span>⭐ {repo.stars}</span>
                        </div>
                      </motion.button>
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            {/* ========== ANALYSIS INPUT STATE ========== */}
            {selectedRepo && appState === 'repoSelected' && (
              <motion.div
                key="analysis-input"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                <button
                  onClick={() => { setSelectedRepo(null); setAppState('connected'); }}
                  className="mb-6 flex items-center gap-2 text-blue-400 hover:text-blue-300 transition"
                >
                  <ChevronRight size={18} className="rotate-180" />
                  Back to repositories
                </button>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Main Analysis Panel */}
                  <div className="lg:col-span-2 space-y-6">
                    {/* Repository Info */}
                    <div className="p-6 rounded-lg bg-slate-800 border border-slate-700">
                      <div className="flex items-center gap-4">
                        <Code size={32} className="text-blue-400" />
                        <div>
                          <h3 className="text-xl font-semibold text-white">{selectedRepo.name}</h3>
                          <p className="text-slate-400 text-sm">{selectedRepo.full_name}</p>
                        </div>
                      </div>
                    </div>

                    {/* Branch Selector */}
                    {branches.length > 0 && (
                      <div>
                        <label className="block text-sm font-semibold text-white mb-2">
                          Branch
                        </label>
                        <select
                          value={selectedBranch}
                          onChange={(e) => setSelectedBranch(e.target.value)}
                          className="w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                        >
                          {branches.map((branch) => (
                            <option key={branch.name} value={branch.name}>
                              {branch.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* Pull Requests Selector */}
                    {pulls.length > 0 && (
                      <div>
                        <label className="block text-sm font-semibold text-white mb-2">
                          Pull Request (Optional)
                        </label>
                        <select
                          value={selectedPull?.number || ''}
                          onChange={(e) => {
                            const prNum = e.target.value ? parseInt(e.target.value) : null;
                            setSelectedPull(pulls.find(p => p.number === prNum) || null);
                          }}
                          className="w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                        >
                          <option value="">None</option>
                          {pulls.map((pr) => (
                            <option key={pr.number} value={pr.number}>
                              #{pr.number} - {pr.title}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* Feature Request */}
                    <div>
                      <label className="block text-sm font-semibold text-white mb-2">
                        Feature Request / Issue Description
                      </label>
                      <textarea
                        value={featureRequest}
                        onChange={(e) => setFeatureRequest(e.target.value)}
                        placeholder="Describe the feature you want to implement..."
                        rows={6}
                        className="w-full px-4 py-3 rounded-lg bg-slate-800 border border-slate-700 text-white placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition resize-none"
                      />
                    </div>
                  </div>

                  {/* Side Panel - Actions */}
                  <div className="space-y-4">
                    <div className="p-6 rounded-lg bg-blue-900/30 border border-blue-700/50">
                      <Zap size={24} className="text-blue-400 mb-2" />
                      <h4 className="font-semibold text-white mb-2">Ready to Analyze?</h4>
                      <p className="text-sm text-slate-300 mb-4">
                        ShipMate will run 5 AI agents to assess your delivery readiness.
                      </p>
                      <button
                        onClick={handleAnalyze}
                        disabled={loading || !featureRequest.trim()}
                        className="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 text-white font-semibold py-2 px-4 rounded-lg transition"
                      >
                        {loading ? 'Analyzing...' : 'Analyze Delivery Readiness'}
                      </button>
                    </div>

                    {error && (
                      <div className="p-4 rounded-lg bg-red-900/30 border border-red-700/50 text-red-200 text-sm flex items-start gap-2">
                        <AlertCircle size={18} className="mt-0.5 flex-shrink-0" />
                        <span>{error}</span>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {/* ========== ANALYZING STATE ========== */}
            {appState === 'analyzing' && (
              <motion.div
                key="analyzing"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                <h2 className="text-2xl font-bold text-white">Analyzing Delivery Readiness</h2>
                <AgentSwarm agents={agents} />
              </motion.div>
            )}

            {/* ========== ANALYSIS COMPLETE STATE ========== */}
            {appState === 'analysisComplete' && analysis && (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-6"
              >
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-white">Analysis Results</h2>
                  <button
                    onClick={() => { setSelectedRepo(null); setAnalysis(null); setAppState('connected'); }}
                    className="text-blue-400 hover:text-blue-300 transition"
                  >
                    Analyze Another Repository
                  </button>
                </div>

                {analysis && (
                  <>
                    <ReadinessScore score={analysis.readiness_score} breakdown={analysis.score_breakdown} />
                    <ReportTabs
                      planner={analysis.agents.planner}
                      repoAnalyst={analysis.agents.repo_analyst}
                      testGenerator={analysis.agents.test_generator}
                      securityGuard={analysis.agents.security_guard}
                      deliveryManager={analysis.agents.delivery_manager}
                    />
                  </>
                )}
              </motion.div>
            )}

            {/* ========== ERROR STATE ========== */}
            {appState === 'error' && (
              <motion.div
                key="error"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="max-w-lg mx-auto p-6 rounded-lg bg-red-900/30 border border-red-700"
              >
                <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-white text-center mb-2">Analysis Failed</h3>
                <p className="text-red-200 text-center mb-6">{error}</p>
                <button
                  onClick={() => { setAppState('repoSelected'); setError(null); }}
                  className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition"
                >
                  Try Again
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        )}
      </main>
    </div>
  );
}
