import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  GitBranch,
  Plus,
  Loader,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Download,
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
  const [appState, setAppState] = useState<AppState>('notConnected');
  const [githubUser, setGithubUser] = useState<any>(null);
  const [repos, setRepos] = useState<GitHubRepository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepository | null>(null);
  const [branches, setBranches] = useState<GitHubBranch[]>([]);
  const [selectedBranch, setSelectedBranch] = useState<string>('main');
  const [featureRequest, setFeatureRequest] = useState<string>(SAMPLE_FEATURE_REQUEST);
  const [agents, setAgents] = useState<AgentState[]>(INITIAL_AGENTS);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Handle GitHub connection
  const handleConnectGitHub = useCallback(async () => {
    setAppState('connecting');
    try {
      const urlData = await api.getGitHubAppInstallUrl();
      // In production, this would redirect to GitHub OAuth
      // For demo, we simulate the connection
      window.open(urlData.install_url, '_blank');
      
      // Simulate callback after user authorizes
      setTimeout(async () => {
        try {
          const mockUser = {
            login: 'demo-user',
            id: 12345,
            avatar_url: 'https://avatars.githubusercontent.com/u/12345?v=4',
          };
          setGithubUser(mockUser);
          setAppState('connected');
          
          // Load repositories
          const repos = await api.getRepositories();
          setRepos(repos);
        } catch (err) {
          setError('Failed to load repositories');
          setAppState('error');
        }
      }, 2000);
    } catch (err) {
      setError('Failed to connect GitHub');
      setAppState('error');
    }
  }, []);

  // Handle repo selection
  const handleSelectRepo = useCallback(async (repo: GitHubRepository) => {
    setSelectedRepo(repo);
    setAppState('repoSelected');
    
    try {
      const repoBranches = await api.getBranches(repo.id);
      setBranches(repoBranches);
      setSelectedBranch('main');
    } catch (err) {
      setError('Failed to load branches');
    }
  }, []);

  // Handle analysis
  const handleAnalyze = useCallback(async () => {
    if (!selectedRepo || !featureRequest.trim()) {
      setError('Please select a repository and enter a feature request');
      return;
    }

    setAppState('analyzing');
    setLoading(true);
    setError(null);

    try {
      // Simulate agent execution with delays
      const agentSequence = ['planner', 'repo_analyst', 'test_generator', 'security_guard', 'delivery_manager'];
      
      for (const agentName of agentSequence) {
        setAgents(prev =>
          prev.map(a => a.name === agentName ? { ...a, status: 'running' as const } : a)
        );
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        setAgents(prev =>
          prev.map(a => a.name === agentName ? { ...a, status: 'complete' as const } : a)
        );
      }

      // Call API
      const result = await api.analyze(
        selectedRepo.id,
        selectedBranch,
        featureRequest,
        githubUser?.token
      );

      setAnalysis(result);
      setAppState('analysisComplete');
    } catch (err) {
      setError(`Analysis failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setAppState('error');
      setAgents(INITIAL_AGENTS);
    } finally {
      setLoading(false);
    }
  }, [selectedRepo, selectedBranch, featureRequest, githubUser]);

  // Handle export
  const handleExport = useCallback(async () => {
    if (!analysis) return;
    
    try {
      // Create markdown file
      const element = document.createElement('a');
      const file = new Blob([analysis.markdown_report], { type: 'text/markdown' });
      element.href = URL.createObjectURL(file);
      element.download = `shipmate-report-${Date.now()}.md`;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    } catch (err) {
      setError('Failed to export report');
    }
  }, [analysis]);

  const handleReset = useCallback(() => {
    setSelectedRepo(null);
    setSelectedBranch('main');
    setFeatureRequest(SAMPLE_FEATURE_REQUEST);
    setAnalysis(null);
    setAgents(INITIAL_AGENTS);
    setError(null);
    setAppState('connected');
  }, []);

  return (
    <div className="flex h-screen bg-slate-950">
      {/* Sidebar Navigation */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {/* Header */}
        <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">ShipMate AI</h1>
              <p className="text-sm text-slate-400">Powered by Azure AI Foundry + Azure OpenAI</p>
            </div>
            {githubUser && (
              <div className="flex items-center gap-3">
                <img
                  src={githubUser.avatar_url}
                  alt={githubUser.login}
                  className="w-8 h-8 rounded-full"
                />
                <span className="text-sm text-slate-300">{githubUser.login}</span>
              </div>
            )}
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8">
          <AnimatePresence mode="wait">
            {/* Not Connected State */}
            {appState === 'notConnected' && (
              <motion.div
                key="not-connected"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="max-w-2xl mx-auto"
              >
                <div className="rounded-xl bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 p-12 text-center">
                  <GitBranch className="w-16 h-16 text-blue-400 mx-auto mb-4" />
                  <h2 className="text-2xl font-bold text-white mb-2">Connect GitHub</h2>
                  <p className="text-slate-400 mb-6">
                    ShipMate AI uses read-only GitHub access. We analyze selected repositories
                    only and never modify your code.
                  </p>
                  <button
                    onClick={handleConnectGitHub}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-8 rounded-lg inline-flex items-center gap-2 transition"
                  >
                    <GitBranch className="w-5 h-5" />
                    Connect GitHub Account
                  </button>
                  <div className="mt-8 pt-8 border-t border-slate-700">
                    <p className="text-sm text-slate-400 mb-4">Minimum permissions requested:</p>
                    <ul className="text-sm text-slate-400 space-y-1">
                      <li>✓ Contents: read-only</li>
                      <li>✓ Metadata: read-only</li>
                      <li>✓ Pull requests: read-only</li>
                      <li>✓ Issues: read-only</li>
                    </ul>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Connected State - Repo Selection */}
            {(appState === 'connected' || appState === 'repoSelected') && (
              <motion.div
                key="repo-selection"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-6"
              >
                {/* Repository Selector */}
                <div className="rounded-xl bg-slate-800/50 border border-slate-700 p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Select Repository</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {repos.map(repo => (
                      <button
                        key={repo.id}
                        onClick={() => handleSelectRepo(repo)}
                        className={`p-4 rounded-lg border-2 transition text-left ${
                          selectedRepo?.id === repo.id
                            ? 'border-blue-500 bg-blue-500/10'
                            : 'border-slate-700 bg-slate-900/50 hover:border-slate-600'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="font-semibold text-white">{repo.name}</h4>
                            <p className="text-sm text-slate-400 mt-1">{repo.description}</p>
                            <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                              <span>⭐ {repo.stars}</span>
                              <span>🍴 {repo.forks}</span>
                              <span>{repo.language}</span>
                            </div>
                          </div>
                          {selectedRepo?.id === repo.id && (
                            <CheckCircle className="w-5 h-5 text-blue-500" />
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Branch & Feature Request */}
                {selectedRepo && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-6"
                  >
                    {/* Branch Selector */}
                    <div className="rounded-xl bg-slate-800/50 border border-slate-700 p-6">
                      <h3 className="text-lg font-semibold text-white mb-4">Select Branch</h3>
                      <select
                        value={selectedBranch}
                        onChange={e => setSelectedBranch(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-4 py-3"
                      >
                        {branches.map(branch => (
                          <option key={branch.name} value={branch.name}>
                            {branch.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Feature Request Input */}
                    <div className="rounded-xl bg-slate-800/50 border border-slate-700 p-6">
                      <label className="block text-lg font-semibold text-white mb-4">
                        Feature Request / Issue Description
                      </label>
                      <textarea
                        value={featureRequest}
                        onChange={e => setFeatureRequest(e.target.value)}
                        placeholder="Describe the feature you want to implement or the issue you want to fix..."
                        className="w-full h-32 bg-slate-900 border border-slate-700 text-white rounded-lg px-4 py-3 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                      />
                    </div>

                    {/* Error Message */}
                    {error && (
                      <div className="rounded-lg bg-red-500/10 border border-red-500/50 p-4 flex items-center gap-3">
                        <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                        <p className="text-red-300 text-sm">{error}</p>
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex gap-4">
                      <button
                        onClick={handleAnalyze}
                        disabled={loading}
                        className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 text-white font-semibold py-3 px-6 rounded-lg transition flex items-center justify-center gap-2"
                      >
                        {loading ? (
                          <>
                            <Loader className="w-5 h-5 animate-spin" />
                            Analyzing...
                          </>
                        ) : (
                          <>
                            <RefreshCw className="w-5 h-5" />
                            Analyze Delivery Readiness
                          </>
                        )}
                      </button>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            )}

            {/* Analyzing State */}
            {appState === 'analyzing' && (
              <motion.div
                key="analyzing"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-6"
              >
                <AgentSwarm agents={agents} />
              </motion.div>
            )}

            {/* Analysis Complete State */}
            {appState === 'analysisComplete' && analysis && (
              <motion.div
                key="analysis-complete"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-6"
              >
                {/* Repo Summary */}
                <div className="rounded-xl bg-slate-800/50 border border-slate-700 p-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <h2 className="text-2xl font-bold text-white">{analysis.repo_summary.name}</h2>
                      <p className="text-slate-400 mt-1">
                        {analysis.repo_summary.language} • {analysis.repo_summary.stars} stars
                      </p>
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        {analysis.repo_summary.tech_stack.map(tech => (
                          <span
                            key={tech}
                            className="px-3 py-1 bg-slate-700 text-slate-300 text-xs rounded-full"
                          >
                            {tech}
                          </span>
                        ))}
                      </div>
                    </div>
                    <ReadinessScore score={analysis.readiness_score} breakdown={analysis.score_breakdown} />
                  </div>

                  {/* Recommendation */}
                  <div className="mt-6 pt-6 border-t border-slate-700">
                    <div
                      className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg font-semibold ${
                        analysis.recommendation === 'Ready to ship'
                          ? 'bg-green-500/20 text-green-300'
                          : analysis.recommendation === 'Needs fixes before shipping'
                          ? 'bg-yellow-500/20 text-yellow-300'
                          : 'bg-red-500/20 text-red-300'
                      }`}
                    >
                      {analysis.recommendation === 'Ready to ship' ? (
                        <CheckCircle className="w-5 h-5" />
                      ) : (
                        <AlertCircle className="w-5 h-5" />
                      )}
                      {analysis.recommendation}
                    </div>
                  </div>
                </div>

                {/* Report Tabs */}
                <ReportTabs data={analysis} />

                {/* Export and Reset Buttons */}
                <div className="flex gap-4">
                  <button
                    onClick={handleExport}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 px-6 rounded-lg transition flex items-center justify-center gap-2"
                  >
                    <Download className="w-5 h-5" />
                    Export Report (Markdown)
                  </button>
                  <button
                    onClick={handleReset}
                    className="flex-1 bg-slate-700 hover:bg-slate-600 text-white font-semibold py-3 px-6 rounded-lg transition flex items-center justify-center gap-2"
                  >
                    <Plus className="w-5 h-5" />
                    Analyze Another Feature
                  </button>
                </div>
              </motion.div>
            )}

            {/* Error State */}
            {appState === 'error' && (
              <motion.div
                key="error"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="max-w-2xl mx-auto"
              >
                <div className="rounded-xl bg-red-500/10 border border-red-500/50 p-8 text-center">
                  <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                  <h2 className="text-2xl font-bold text-white mb-2">Error</h2>
                  <p className="text-red-300 mb-6">{error}</p>
                  <button
                    onClick={() => {
                      setAppState('connected');
                      setError(null);
                    }}
                    className="bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-8 rounded-lg transition"
                  >
                    Try Again
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
