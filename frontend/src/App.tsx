import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload, Play, X, FolderOpen, Sparkles,
  CheckCircle, AlertCircle, ChevronRight, Boxes
} from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { AgentSwarm } from './components/AgentSwarm';
import { ReadinessScore } from './components/ReadinessScore';
import { ReportTabs } from './components/ReportTabs';
import { api } from './lib/api';
import type { AnalyzeResponse, AgentState, AgentName, RepoSummary } from './types';

const SAMPLE_FEATURE_REQUEST = `Add login with role-based access and dashboard analytics.

Requirements:
- Support email/password login and Google OAuth
- Three roles: Admin, Editor, Viewer with different permissions
- Admin dashboard with user management
- Analytics dashboard showing MAU, DAU, retention metrics
- All data endpoints secured behind RBAC middleware`;

const INITIAL_AGENTS: AgentState[] = [
  {
    name: 'planner',
    label: 'Planner Agent',
    icon: '🧠',
    status: 'idle',
    description: 'Converts feature request into structured frontend, backend, database, and test tasks with story points.',
  },
  {
    name: 'repo_analyst',
    label: 'Repo Analyst Agent',
    icon: '🔍',
    status: 'idle',
    description: 'Analyzes repository to identify files requiring changes, affected APIs, and risky dependencies.',
  },
  {
    name: 'test_generator',
    label: 'Test Generator Agent',
    icon: '🧪',
    status: 'idle',
    description: 'Generates comprehensive unit tests, API tests, edge cases, and a regression checklist.',
  },
  {
    name: 'security_guard',
    label: 'Security Guard Agent',
    icon: '🛡️',
    status: 'idle',
    description: 'Scans for security risks, exposed secrets, CVEs, auth bypass vectors, and compliance issues.',
  },
  {
    name: 'delivery_manager',
    label: 'Delivery Manager Agent',
    icon: '🚢',
    status: 'idle',
    description: 'Creates sprint plan, standup summary, PR review, CI/CD recommendations, and release readiness.',
  },
];

const AGENT_SEQUENCE: AgentName[] = ['planner', 'repo_analyst', 'test_generator', 'security_guard', 'delivery_manager'];
const AGENT_DELAY_MS = 1200;

export default function App() {
  const [featureRequest, setFeatureRequest] = useState('');
  const [repoFile, setRepoFile] = useState<File | null>(null);
  const [repoSummary, setRepoSummary] = useState<RepoSummary | null>(null);
  const [useSample, setUseSample] = useState(false);
  const [agents, setAgents] = useState<AgentState[]>(INITIAL_AGENTS);
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragRef = useRef<boolean>(false);
  const [isDragging, setIsDragging] = useState(false);

  const updateAgentStatus = useCallback((name: AgentName, status: AgentState['status']) => {
    setAgents(prev => prev.map(a => a.name === name ? { ...a, status } : a));
  }, []);

  async function handleLoadSample() {
    setUseSample(true);
    setRepoFile(null);
    setUploadStatus('uploading');
    try {
      const summary = await api.getSampleRepo();
      setRepoSummary(summary);
      setUploadStatus('done');
    } catch {
      setUploadStatus('error');
      setUseSample(false);
    }
  }

  async function handleFileUpload(file: File) {
    if (!file.name.endsWith('.zip')) {
      setError('Please upload a ZIP file containing your repository.');
      return;
    }
    setRepoFile(file);
    setUseSample(false);
    setUploadStatus('uploading');
    try {
      const summary = await api.uploadRepo(file);
      setRepoSummary(summary);
      setUploadStatus('done');
    } catch (e: any) {
      setUploadStatus('error');
      setError(e?.response?.data?.detail || 'Failed to process repository ZIP.');
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  }

  async function runSwarm() {
    if (!featureRequest.trim() || featureRequest.trim().length < 10) {
      setError('Please enter a feature request (at least 10 characters).');
      return;
    }
    setError(null);
    setResult(null);
    setIsRunning(true);
    setAgents(INITIAL_AGENTS);

    // Animate agents one by one
    for (let i = 0; i < AGENT_SEQUENCE.length; i++) {
      const name = AGENT_SEQUENCE[i];
      updateAgentStatus(name, 'running');
      await new Promise(res => setTimeout(res, AGENT_DELAY_MS));
    }

    // Now call backend
    try {
      const data = await api.analyze(featureRequest, repoSummary?.repo_context);
      // Mark all complete
      setAgents(prev => prev.map(a => ({ ...a, status: 'complete' })));
      setResult(data);
    } catch (e: any) {
      setAgents(prev => prev.map(a => a.status === 'running' ? { ...a, status: 'error' } : a));
      setError(e?.response?.data?.detail || 'Analysis failed. Make sure the backend is running on port 8000.');
    } finally {
      setIsRunning(false);
    }
  }

  const completedAgents = agents.filter(a => a.status === 'complete').length;

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }} className="grid-bg">
      <Sidebar />

      {/* Main content */}
      <main style={{
        marginLeft: 260,
        flex: 1,
        padding: '32px 32px 60px',
        minHeight: '100vh',
        maxWidth: 'calc(100vw - 260px)',
      }}>
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ marginBottom: 32 }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <h1 style={{
                fontSize: 28, fontWeight: 900, lineHeight: 1.2, marginBottom: 6,
                background: 'linear-gradient(135deg, #f0f6ff, #93c5fd)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
              }}>
                Production Swarm Command Center
              </h1>
              <p style={{ fontSize: 14, color: '#4a6180', maxWidth: 560 }}>
                Transform a feature request into a complete engineering execution plan — tasks, tests, security analysis, and release strategy.
              </p>
            </div>
            {result && (
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                style={{
                  padding: '10px 20px',
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: 12,
                  display: 'flex', alignItems: 'center', gap: 8,
                }}
              >
                <CheckCircle size={16} color="#10b981" />
                <span style={{ fontSize: 13, color: '#34d399', fontWeight: 600 }}>Analysis Complete</span>
              </motion.div>
            )}
          </div>
        </motion.div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24, alignItems: 'start' }}>
          {/* Left column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

            {/* Feature request input */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              style={{
                padding: '24px',
                background: 'rgba(17, 24, 39, 0.85)',
                border: '1px solid rgba(99, 179, 237, 0.1)',
                borderRadius: 18,
                backdropFilter: 'blur(12px)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Sparkles size={16} color="#a78bfa" />
                  <span style={{ fontWeight: 700, fontSize: 14, color: '#f0f6ff' }}>Feature Request</span>
                </div>
                <button
                  onClick={() => setFeatureRequest(SAMPLE_FEATURE_REQUEST)}
                  style={{
                    padding: '5px 12px', borderRadius: 8,
                    border: '1px solid rgba(139, 92, 246, 0.3)',
                    background: 'rgba(139, 92, 246, 0.08)',
                    color: '#a78bfa', fontSize: 12, fontWeight: 600,
                    cursor: 'pointer', fontFamily: 'Inter, sans-serif',
                    transition: 'all 0.15s',
                  }}
                >
                  Use Sample
                </button>
              </div>
              <textarea
                value={featureRequest}
                onChange={e => setFeatureRequest(e.target.value)}
                placeholder="Describe your feature request, bug report, or team discussion here...&#10;&#10;Example: Add login with role-based access and dashboard analytics."
                style={{
                  width: '100%', minHeight: 140,
                  background: 'rgba(8, 12, 20, 0.6)',
                  border: '1px solid rgba(99, 179, 237, 0.1)',
                  borderRadius: 12,
                  padding: '14px 16px',
                  color: '#e2e8f0', fontSize: 13, lineHeight: 1.7,
                  fontFamily: 'Inter, sans-serif',
                  resize: 'vertical',
                  outline: 'none',
                  transition: 'border-color 0.2s',
                }}
                onFocus={e => { e.target.style.borderColor = 'rgba(59, 130, 246, 0.4)'; }}
                onBlur={e => { e.target.style.borderColor = 'rgba(99, 179, 237, 0.1)'; }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                <span style={{ fontSize: 11, color: '#4a6180' }}>{featureRequest.length} chars</span>
              </div>
            </motion.div>

            {/* Repo upload */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              style={{
                padding: '24px',
                background: 'rgba(17, 24, 39, 0.85)',
                border: '1px solid rgba(99, 179, 237, 0.1)',
                borderRadius: 18,
                backdropFilter: 'blur(12px)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                <FolderOpen size={16} color="#60a5fa" />
                <span style={{ fontWeight: 700, fontSize: 14, color: '#f0f6ff' }}>Repository Context</span>
                <span style={{ fontSize: 11, color: '#4a6180' }}>(optional)</span>
              </div>

              {/* Drop zone */}
              <div
                onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                style={{
                  padding: '24px',
                  border: `2px dashed ${isDragging ? 'rgba(59, 130, 246, 0.6)' : repoFile || useSample ? 'rgba(16, 185, 129, 0.4)' : 'rgba(99, 179, 237, 0.15)'}`,
                  borderRadius: 12,
                  textAlign: 'center',
                  cursor: 'pointer',
                  background: isDragging ? 'rgba(59, 130, 246, 0.05)' : repoFile || useSample ? 'rgba(16, 185, 129, 0.04)' : 'rgba(8, 12, 20, 0.4)',
                  transition: 'all 0.2s',
                  marginBottom: 12,
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip"
                  style={{ display: 'none' }}
                  onChange={e => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); }}
                />

                {uploadStatus === 'uploading' && (
                  <div>
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      style={{ display: 'inline-block', marginBottom: 8 }}
                    >
                      <Upload size={24} color="#60a5fa" />
                    </motion.div>
                    <div style={{ fontSize: 13, color: '#60a5fa' }}>Processing repository...</div>
                  </div>
                )}

                {uploadStatus === 'done' && (
                  <div>
                    <CheckCircle size={24} color="#10b981" style={{ marginBottom: 8 }} />
                    <div style={{ fontSize: 13, color: '#34d399', fontWeight: 600 }}>
                      {useSample ? '📦 Sample Repo Loaded' : `📁 ${repoFile?.name}`}
                    </div>
                    {repoSummary && (
                      <div style={{ fontSize: 11, color: '#4a6180', marginTop: 4 }}>
                        {repoSummary.file_count} files · {repoSummary.detected_stack.join(', ')}
                      </div>
                    )}
                  </div>
                )}

                {uploadStatus === 'error' && (
                  <div>
                    <AlertCircle size={24} color="#ef4444" style={{ marginBottom: 8 }} />
                    <div style={{ fontSize: 13, color: '#f87171' }}>Upload failed. Try again or use sample.</div>
                  </div>
                )}

                {uploadStatus === 'idle' && (
                  <div>
                    <Upload size={24} color="#4a6180" style={{ marginBottom: 8 }} />
                    <div style={{ fontSize: 13, color: '#4a6180' }}>Drop a repo ZIP here or click to browse</div>
                    <div style={{ fontSize: 11, color: '#2d4160', marginTop: 4 }}>Accepts .zip files up to 50MB</div>
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                {(uploadStatus === 'done' || uploadStatus === 'error') && (
                  <button
                    onClick={e => { e.stopPropagation(); setRepoFile(null); setRepoSummary(null); setUseSample(false); setUploadStatus('idle'); }}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 6,
                      padding: '8px 14px', borderRadius: 8, flex: 1,
                      border: '1px solid rgba(239, 68, 68, 0.25)',
                      background: 'rgba(239, 68, 68, 0.06)',
                      color: '#f87171', fontSize: 12, fontWeight: 600,
                      cursor: 'pointer', fontFamily: 'Inter, sans-serif',
                      justifyContent: 'center',
                    }}
                  >
                    <X size={12} /> Clear
                  </button>
                )}
                <button
                  onClick={handleLoadSample}
                  disabled={uploadStatus === 'uploading'}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '8px 14px', borderRadius: 8, flex: 1,
                    border: '1px solid rgba(59, 130, 246, 0.25)',
                    background: 'rgba(59, 130, 246, 0.08)',
                    color: '#60a5fa', fontSize: 12, fontWeight: 600,
                    cursor: 'pointer', fontFamily: 'Inter, sans-serif',
                    justifyContent: 'center',
                    opacity: uploadStatus === 'uploading' ? 0.5 : 1,
                  }}
                >
                  <Boxes size={12} /> Load Sample Repo
                </button>
              </div>

              {/* Repo summary preview */}
              {repoSummary && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  style={{
                    marginTop: 12, padding: '12px 14px',
                    background: 'rgba(8, 12, 20, 0.5)',
                    border: '1px solid rgba(99, 179, 237, 0.08)',
                    borderRadius: 10,
                  }}
                >
                  <div style={{ fontSize: 11, color: '#4a6180', fontWeight: 600, marginBottom: 8, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                    Repo Summary
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {repoSummary.detected_stack.map(s => (
                      <span key={s} style={{
                        padding: '2px 8px', borderRadius: 6, fontSize: 11,
                        background: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa',
                        border: '1px solid rgba(59, 130, 246, 0.2)',
                      }}>{s}</span>
                    ))}
                  </div>
                  <div style={{ marginTop: 8, fontSize: 11, color: '#4a6180' }}>
                    {repoSummary.file_count} files indexed
                  </div>
                </motion.div>
              )}
            </motion.div>

            {/* Error */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  style={{
                    padding: '14px 18px',
                    background: 'rgba(239, 68, 68, 0.08)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    borderRadius: 12,
                    display: 'flex', alignItems: 'flex-start', gap: 10,
                  }}
                >
                  <AlertCircle size={16} color="#f87171" style={{ flexShrink: 0, marginTop: 1 }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#fca5a5', marginBottom: 2 }}>Error</div>
                    <div style={{ fontSize: 12, color: '#f87171' }}>{error}</div>
                  </div>
                  <button
                    onClick={() => setError(null)}
                    style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#4a6180' }}
                  >
                    <X size={14} />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Run button */}
            <motion.button
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              onClick={runSwarm}
              disabled={isRunning}
              whileHover={!isRunning ? { scale: 1.01 } : {}}
              whileTap={!isRunning ? { scale: 0.99 } : {}}
              style={{
                width: '100%',
                padding: '18px 24px',
                borderRadius: 14,
                border: 'none',
                background: isRunning
                  ? 'rgba(59, 130, 246, 0.15)'
                  : 'linear-gradient(135deg, #2563eb 0%, #7c3aed 50%, #0891b2 100%)',
                color: 'white',
                fontSize: 16, fontWeight: 800,
                cursor: isRunning ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
                boxShadow: isRunning ? 'none' : '0 8px 40px rgba(59, 130, 246, 0.3)',
                transition: 'all 0.3s',
                fontFamily: 'Inter, sans-serif',
                letterSpacing: '-0.2px',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {isRunning ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                  >
                    <Play size={20} />
                  </motion.div>
                  Running Production Swarm... ({completedAgents}/5 agents)
                </>
              ) : (
                <>
                  <Play size={20} />
                  Run Production Swarm
                  <ChevronRight size={18} />
                </>
              )}

              {/* Shimmer effect when not running */}
              {!isRunning && (
                <motion.div
                  animate={{ x: ['-100%', '200%'] }}
                  transition={{ duration: 2.5, repeat: Infinity, ease: 'linear', repeatDelay: 1 }}
                  style={{
                    position: 'absolute',
                    top: 0, bottom: 0,
                    width: '30%',
                    background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent)',
                  }}
                />
              )}
            </motion.button>

            {/* Results */}
            <AnimatePresence>
              {result && (
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                  style={{ display: 'flex', flexDirection: 'column', gap: 20 }}
                >
                  {/* Summary banner */}
                  <div style={{
                    padding: '16px 20px',
                    background: 'rgba(16, 185, 129, 0.06)',
                    border: '1px solid rgba(16, 185, 129, 0.2)',
                    borderRadius: 14,
                    fontSize: 13, color: '#6ee7b7', lineHeight: 1.6,
                  }}>
                    ✅ {result.summary}
                  </div>

                  <ReadinessScore score={result.readiness_score} breakdown={result.score_breakdown} />
                  <ReportTabs data={result} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Right column — Agent Swarm */}
          <div style={{ position: 'sticky', top: 32 }}>
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
            >
              <div style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: isRunning ? '#06b6d4' : completedAgents === 5 ? '#10b981' : '#4a6180',
                  boxShadow: isRunning ? '0 0 8px #06b6d4' : completedAgents === 5 ? '0 0 8px #10b981' : 'none',
                }} />
                <span style={{ fontWeight: 700, fontSize: 14, color: '#f0f6ff' }}>Agent Swarm</span>
                {completedAgents > 0 && (
                  <span style={{ fontSize: 11, color: '#4a6180' }}>{completedAgents}/5 complete</span>
                )}
              </div>
              <AgentSwarm agents={agents} />
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  );
}
