import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Github,
  LogOut,
  Menu,
  X,
  ChevronRight,
  Loader,
  AlertCircle,
  CheckCircle,
  Star,
  GitFork,
  Code,
  GitPullRequest,
  AlertTriangle,
  Settings,
  FileText,
  Zap,
} from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { AgentSwarm } from './components/AgentSwarm';
import { ReadinessScore } from './components/ReadinessScore';
import { ReportTabs } from './components/ReportTabs';
import { api } from './lib/api';
import type {
  AppState,
  GitHubRepository,
  GitHubBranch,
  AnalyzeResponse,
  AgentState,
} from './types';

const INITIAL_AGENTS: AgentState[] = [
  {
    name: 'planner',
    label: 'Planner Agent',
    icon: '🧠',
    status: 'idle',
    description: 'Converts feature request into structured engineering tasks with story points.',
  },
  {
    name: 'repo_analyst',
    label: 'Repo Analyst Agent',
    icon: '🔍',
    status: 'idle',
    description: 'Maps feature impact across the codebase and identifies affected files.',
  },
  {
    name: 'test_generator',
    label: 'Test Architect Agent',
    icon: '🧪',
    status: 'idle',
    description: 'Creates comprehensive unit, API, and edge case tests.',
  },
  {
    name: 'security_guard',
    label: 'Security Guard Agent',
    icon: '🛡️',
    status: 'idle',
    description: 'Identifies security vulnerabilities, CVEs, and compliance risks.',
  },
  {
    name: 'delivery_manager',
    label: 'Delivery Manager Agent',
    icon: '🚢',
    status: 'idle',
    description: 'Produces sprint plan, CI/CD recommendations, and release readiness.',
  },
];

const SAMPLE_FEATURE_REQUEST = `Add social login with GitHub OAuth.

Requirements:
- Support GitHub login via OAuth2 flow
- Link GitHub account to user profile
- Show linked repositories in dashboard
- Allow one-click analysis of selected repos
- Secure token storage in backend`;

export default function App() {
  // ========== State Management ==========
  const [appState, setAppState] = useState<AppState>('notConnected');
  const [githubUser, setGithubUser] = useState<any>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  
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
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentView, setCurrentView] = useState<'dashboard' | 'repos' | 'prs' | 'issues'>('dashboard');

  // ========== GitHub Connection Handler ==========
  const handleConnectGitHub = useCallback(async () => {
    setAppState('connecting');
    setError(null);
    
    try {
      // Get the OAuth URL from backend
      const { auth_url } = await api.getGitHubAuthUrl();
      
      // Create popup window for OAuth
      const width = 500;
      const height = 600;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;
      
      const popup = window.open(
        auth_url,
        'GitHub Login',
        `width=${width},height=${height},left=${left},top=${top}`
      );
      
      // Listen for postMessage from callback
      const handleMessage = async (event: MessageEvent) => {
        if (event.data.type === 'GITHUB_AUTH_SUCCESS') {
          window.removeEventListener('message', handleMessage);
          popup?.close();
          
          const { access_token, user } = event.data;
          setAccessToken(access_token);
          setGithubUser(user);
          setAppState('connected');
          
          // Load user's repositories
          try {
            const userRepos = await api.getUserRepositories(access_token);
            setRepos(userRepos);
          } catch (err) {
            setError('Failed to load repositories');
          }
        }
      };
      
      window.addEventListener('message', handleMessage);
    } catch (err) {
      setError('Failed to initiate GitHub connection');
      setAppState('notConnected');
    }
  }, []);

  // ========== Repository Selection Handler ==========
  const handleSelectRepository = useCallback(async (repo: GitHubRepository) => {
    setSelectedRepo(repo);
    setSelectedBranch('main');
    setSelectedPull(null);
    setSelectedIssue(null);
    setAppState('repoSelected');
    
    if (!accessToken) return;
    
    try {
      // Extract owner and repo name from full_name
      const [owner, repoName] = repo.full_name.split('/');
      
      // Fetch branches
      const repoBranches = await api.getRepositoryBranches(owner, repoName, accessToken);
      setBranches(repoBranches);
      
      // Fetch PRs
      const repoPulls = await api.getRepositoryPulls(owner, repoName, accessToken);
      setPulls(repoPulls);
      
      // Fetch issues
      const repoIssues = await api.getRepositoryIssues(owner, repoName, accessToken);
      setIssues(repoIssues);
    } catch (err) {
      setError('Failed to load repository data');
    }
  }, [accessToken]);

  // ========== Analysis Handler ==========
  const handleAnalyze = useCallback(async () => {
    if (!selectedRepo || !featureRequest || !accessToken) {
      setError('Please select a repository and enter a feature request');
      return;
    }
    
    setLoading(true);
    setError(null);
    setAppState('analyzing');
    
    // Animate agents
    const animateAgents = async () => {
      for (let i = 0; i < INITIAL_AGENTS.length; i++) {
        setAgents(prev => prev.map((a, idx) => 
          idx === i ? { ...a, status: 'running' } : a
        ));
        await new Promise(resolve => setTimeout(resolve, 1500));
        setAgents(prev => prev.map((a, idx) => 
          idx === i ? { ...a, status: 'complete' } : a
        ));
      }
    };
    
    try {
      // Extract owner and repo name
      const [owner, repoName] = selectedRepo.full_name.split('/');
      
      // Call analysis endpoint
      const result = await api.analyzeDeliveryReadiness(
        owner,
        repoName,
        selectedBranch,
        featureRequest,
        selectedPull?.number,
        selectedIssue?.number,
        accessToken
      );
      
      setAnalysis(result);
      setAgents(INITIAL_AGENTS);
      setAppState('analysisComplete');
      
      // Animate agents while loading
      animateAgents();
    } catch (err) {
      setError('Analysis failed. Please try again.');
      setAppState('error');
    } finally {
      setLoading(false);
    }
  }, [selectedRepo, featureRequest, selectedBranch, selectedPull, selectedIssue, accessToken]);

  // ========== Logout Handler ==========
  const handleLogout = useCallback(() => {
    setAppState('notConnected');
    setGithubUser(null);
    setAccessToken(null);
    setRepos([]);
    setSelectedRepo(null);
    setBranches([]);
    setAnalysis(null);
    setError(null);
  }, []);

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      {/* ========== Sidebar Navigation ========== */}
      {appState !== 'notConnected' && (
        <motion.div
          initial={{ x: -280 }}
          animate={{ x: sidebarOpen ? 0 : -280 }}
          transition={{ type: 'spring', stiffness: 100 }}
          className="fixed left-0 top-0 h-screen w-80 bg-slate-900 border-r border-slate-800 z-50 overflow-y-auto"
        >
          <Sidebar />
        </motion.div>
      )}

      {/* ========== Main Content ========== */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* ========== Header ========== */}
        <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {appState !== 'notConnected' && (
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="p-2 hover:bg-slate-800 rounded-lg transition text-slate-400 hover:text-white"
                  title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
                >
                  {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
                </button>
              )}
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                  ShipMate AI
                </h1>
                <p className="text-xs text-slate-400 mt-0.5">
                  Powered by Azure AI Foundry + Azure OpenAI
                </p>
              </div>
            </div>

            {/* User Profile & Logout */}
            {githubUser && (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-3 px-3 py-2 bg-slate-800/50 rounded-lg">
                  <img
                    src={githubUser.avatar_url}
                    alt={githubUser.login}
                    className="w-8 h-8 rounded-full"
                  />
                  <div>
                    <p className="text-sm font-medium">{githubUser.login}</p>
                    <p className="text-xs text-slate-400">{githubUser.company || 'Developer'}</p>
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 hover:bg-slate-800 rounded-lg transition text-slate-400 hover:text-red-400"
                  title="Logout"
                >
                  <LogOut size={20} />
                </button>
              </div>
            )}
          </div>
        </header>

        {/* ========== Content Area ========== */}
        <div className="flex-1 overflow-auto">
          <div className="p-8">
            <AnimatePresence mode="wait">
              {/* ========== NOT CONNECTED STATE ========== */}
              {appState === 'notConnected' && (
                <motion.div
                  key="not-connected"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="max-w-2xl mx-auto"
                >
                  <div className="rounded-xl bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 p-12 text-center">
                    <Github className="w-16 h-16 text-blue-400 mx-auto mb-6" />
                    
                    <h2 className="text-3xl font-bold text-white mb-4">
                      Connect Your GitHub Account
                    </h2>
                    
                    <p className="text-slate-300 mb-8 text-lg">
                      ShipMate AI analyzes your repositories using AI agents to assess delivery readiness.
                      We use read-only access and never modify your code.
                    </p>
                    
                    <button
                      onClick={handleConnectGitHub}
                      disabled={appState === 'connecting'}
                      className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 text-white font-semibold py-3 px-8 rounded-lg inline-flex items-center gap-3 transition transform hover:scale-105"
                    >
                      {appState === 'connecting' ? (
                        <>
                          <Loader size={20} className="animate-spin" />
                          Connecting...
                        </>
                      ) : (
                        <>
                          <Github size={20} />
                          Connect GitHub Account
                        </>
                      )}
                    </button>
                    
                    {error && (
                      <div className="mt-6 p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-200 text-sm">
                        {error}
                      </div>
                    )}
                    
                    <div className="mt-12 pt-8 border-t border-slate-700">
                      <p className="text-sm text-slate-400 mb-6 font-semibold">
                        Required Permissions (Read-Only)
                      </p>
                      <div className="grid grid-cols-2 gap-3 text-sm text-slate-400">
                        <div className="flex items-center gap-2">
                          <CheckCircle size={16} className="text-green-400" />
                          <span>Repository contents</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <CheckCircle size={16} className="text-green-400" />
                          <span>Metadata</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <CheckCircle size={16} className="text-green-400" />
                          <span>Pull requests</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <CheckCircle size={16} className="text-green-400" />
                          <span>Issues</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* ========== ANALYSIS INPUT STATE ========== */}
              {selectedRepo && appState !== 'analyzing' && appState !== 'analysisComplete' && (
                <motion.div
                  key="analysis-input"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <button
                    onClick={() => setSelectedRepo(null)}
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
                      onClick={() => setSelectedRepo(null)}
                      className="text-blue-400 hover:text-blue-300 transition"
                    >
                      Analyze Another Repository
                    </button>
                  </div>
                  
                  <ReadinessScore analysis={analysis} />
                  <ReportTabs analysis={analysis} />
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
                    onClick={() => setSelectedRepo(null)}
                    className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition"
                  >
                    Try Again
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>
    </div>
  );
}
