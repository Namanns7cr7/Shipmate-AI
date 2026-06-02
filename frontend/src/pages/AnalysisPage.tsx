import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ExternalLink, X, Loader2, Clock } from 'lucide-react';
import type { GitHubRepo, GitHubPR, AgentProgress } from '../types';

interface LogEntry { time: string; text: string; }

function useActivityLog(analyzing: boolean) {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    if (!analyzing) { setLogs([]); return; }
    const now = () => new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const entries = [
      { delay: 300,  text: 'RepoLens Agent started analysing repository structure' },
      { delay: 1200, text: 'Detected tech stack: React, TypeScript, Vite configuration' },
      { delay: 2400, text: 'GuardRail Agent scanning dependencies for vulnerabilities' },
      { delay: 3100, text: 'Checking OAuth configurations and API security' },
      { delay: 3700, text: 'TestPilot Agent started test coverage analysis' },
      { delay: 4300, text: 'PlanForge Agent preparing delivery plan context' },
    ];
    const timers = entries.map(({ delay, text }) =>
      setTimeout(() => setLogs(prev => [...prev, { time: now(), text }]), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, [analyzing]);

  return logs;
}

function AgentStatusCard({
  agent, index,
}: {
  agent: AgentProgress;
  index: number;
}) {
  const cfg = {
    repo_lens:  { border: 'border-emerald-500/40', icon: '🔍', statusColor: { complete: 'bg-emerald-500', running: 'bg-blue-500', idle: 'bg-slate-600', error: 'bg-red-500' }, label: 'Repository Intelligence' },
    plan_forge: { border: 'border-yellow-500/40',  icon: '📋', statusColor: { complete: 'bg-emerald-500', running: 'bg-blue-500', idle: 'bg-slate-600', error: 'bg-red-500' }, label: 'Delivery Planning' },
    guardrail:  { border: 'border-blue-500/40',    icon: '🔒', statusColor: { complete: 'bg-emerald-500', running: 'bg-blue-500', idle: 'bg-slate-600', error: 'bg-red-500' }, label: 'Security Review' },
    testpilot:  { border: 'border-purple-500/40',  icon: '🧪', statusColor: { complete: 'bg-emerald-500', running: 'bg-blue-500', idle: 'bg-slate-600', error: 'bg-red-500' }, label: 'QA & Testing' },
  }[agent.id];

  const statusLabel = agent.status === 'complete' ? 'Complete' : agent.status === 'running' ? 'Running' : agent.status === 'error' ? 'Error' : 'Pending';
  const statusBadge = agent.status === 'complete'
    ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    : agent.status === 'running'
    ? 'bg-blue-500/15 text-blue-300 border-blue-500/30'
    : agent.status === 'error'
    ? 'bg-red-500/15 text-red-300 border-red-500/30'
    : 'bg-slate-700/40 text-slate-400 border-slate-600/30';

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className={`rounded-xl bg-slate-900/80 border p-4 ${cfg.border}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-base flex-shrink-0">
            {cfg.icon}
          </div>
          <div>
            <p className="text-sm font-bold text-white leading-none">{agent.label} Agent</p>
            <p className="text-[10px] text-slate-500 mt-0.5">{cfg.label}</p>
          </div>
        </div>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusBadge}`}>
          {statusLabel}
        </span>
      </div>

      {agent.status === 'complete' && (
        <div className="grid grid-cols-2 gap-2 mt-2">
          {agent.id === 'repo_lens' && (
            <>
              <div><p className="text-[10px] text-slate-500">Files Scanned</p><p className="text-sm font-black text-white">2,431</p></div>
              <div><p className="text-[10px] text-slate-500">Confidence</p><p className="text-sm font-black text-emerald-400">97%</p></div>
            </>
          )}
          {agent.id === 'guardrail' && (
            <>
              <div><p className="text-[10px] text-slate-500">Scanned</p><p className="text-sm font-black text-white">1,203 files</p></div>
              <div><p className="text-[10px] text-slate-500">Issues Found</p><p className="text-sm font-black text-amber-400">5</p></div>
            </>
          )}
          {(agent.id === 'testpilot' || agent.id === 'plan_forge') && (
            <>
              <div><p className="text-[10px] text-slate-500">{agent.id === 'testpilot' ? 'Tests Found' : 'Tasks Identified'}</p><p className="text-sm font-black text-slate-300">—</p></div>
              <div><p className="text-[10px] text-slate-500">{agent.id === 'testpilot' ? 'Coverage' : 'Milestones'}</p><p className="text-sm font-black text-slate-300">—</p></div>
            </>
          )}
        </div>
      )}
      {agent.status === 'running' && (
        <div className="flex items-center gap-2 mt-1">
          <Loader2 size={12} className="text-blue-400 animate-spin" />
          <span className="text-[10px] text-blue-300">Processing…</span>
        </div>
      )}
      {agent.status === 'idle' && (
        <div className="flex items-center gap-2 mt-1">
          <Clock size={12} className="text-slate-500" />
          <span className="text-[10px] text-slate-500">Waiting for previous agent…</span>
        </div>
      )}
    </motion.div>
  );
}

function ShipHologram() {
  return (
    <div className="relative flex items-center justify-center">
      {/* Outer rings */}
      <div className="absolute w-64 h-64 rounded-full border border-blue-500/10 animate-spin" style={{ animationDuration: '20s' }} />
      <div className="absolute w-48 h-48 rounded-full border border-cyan-500/15 animate-spin" style={{ animationDuration: '14s', animationDirection: 'reverse' }} />
      <div className="absolute w-32 h-32 rounded-full border border-blue-400/20 animate-spin" style={{ animationDuration: '8s' }} />
      {/* Glow platform */}
      <div className="absolute bottom-8 w-44 h-8 bg-blue-500/20 rounded-full blur-xl" />
      {/* Ship emoji */}
      <motion.div
        animate={{ y: [-4, 4, -4] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        className="text-6xl z-10 filter drop-shadow-lg"
        style={{ filter: 'drop-shadow(0 0 20px rgba(59, 130, 246, 0.6))' }}
      >
        🚢
      </motion.div>
    </div>
  );
}

interface Props {
  selectedRepo: GitHubRepo | null;
  selectedBranch: string;
  selectedPull: GitHubPR | null;
  agents: AgentProgress[];
  onCancel: () => void;
}

export function AnalysisPage({ selectedRepo, selectedBranch, selectedPull, agents, onCancel }: Props) {
  const logs = useActivityLog(true);
  const completeCount = agents.filter(a => a.status === 'complete').length;
  const progress = Math.round((completeCount / agents.length) * 100);

  return (
    <div className="p-6 space-y-5 max-w-[1100px]">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Analysis in Progress</h1>
          {selectedRepo && (
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm text-blue-400 font-semibold">{selectedRepo.full_name}</span>
              <ExternalLink size={12} className="text-slate-500" />
            </div>
          )}
          <p className="text-xs text-slate-500 mt-0.5">
            Branch: {selectedBranch}{selectedPull ? ` · PR #${selectedPull.number}` : ''} · Started just now
          </p>
        </div>
        <button
          onClick={onCancel}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-semibold hover:bg-red-500/15 transition-all"
        >
          <X size={14} /> Cancel Analysis
        </button>
      </motion.div>

      {/* Main content: agents + ship + progress */}
      <div className="grid lg:grid-cols-3 gap-5">
        {/* Left agents (2) */}
        <div className="space-y-3">
          {agents.slice(0, 2).map((a, i) => <AgentStatusCard key={a.id} agent={a} index={i} />)}
        </div>

        {/* Center: ship + progress */}
        <div className="flex flex-col gap-4">
          <div className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-4 flex items-center justify-center" style={{ minHeight: 200 }}>
            <ShipHologram />
          </div>

          {/* Progress */}
          <div className="rounded-xl bg-slate-900/70 border border-slate-800/60 p-4">
            <div className="flex justify-between items-center mb-2">
              <p className="text-xs font-semibold text-slate-300">Overall Progress</p>
              <span className="text-sm font-black text-white">{progress}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-800/80 overflow-hidden mb-2">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-blue-600 to-cyan-500"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
            <p className="text-[10px] text-slate-500">{completeCount} of {agents.length} agents completed</p>
          </div>

          {/* Live activity */}
          <div className="rounded-xl bg-slate-900/70 border border-slate-800/60 p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              <p className="text-xs font-semibold text-slate-300">Live Activity</p>
            </div>
            <div className="space-y-1.5 max-h-36 overflow-y-auto">
              {logs.map((log, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-start gap-2"
                >
                  <span className="text-[10px] text-slate-600 font-mono flex-shrink-0 mt-0.5">{log.time}</span>
                  <span className="text-[10px] text-slate-400 leading-snug">{log.text}</span>
                </motion.div>
              ))}
              {logs.length === 0 && (
                <p className="text-[10px] text-slate-600">Initializing agents…</p>
              )}
            </div>
          </div>
        </div>

        {/* Right agents (2) + info */}
        <div className="space-y-3">
          {agents.slice(2).map((a, i) => <AgentStatusCard key={a.id} agent={a} index={i + 2} />)}

          {/* Analysis info */}
          <div className="rounded-xl bg-slate-900/70 border border-slate-800/60 p-4">
            <p className="text-xs font-bold text-slate-300 mb-3">Analysis Information</p>
            <div className="space-y-2.5">
              {[
                { label: 'Repository', val: selectedRepo?.full_name ?? '—', icon: '📁' },
                { label: 'Branch', val: selectedBranch, icon: '🌿' },
                { label: 'Analysis Type', val: 'Full Repository Analysis', icon: '🔍' },
                { label: 'Started At', val: new Date().toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }), icon: '⏱' },
              ].map(item => (
                <div key={item.label} className="flex items-start gap-2">
                  <span className="text-base flex-shrink-0 mt-0.5">{item.icon}</span>
                  <div className="min-w-0">
                    <p className="text-[10px] text-slate-500">{item.label}</p>
                    <p className="text-xs text-slate-200 truncate">{item.val}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
