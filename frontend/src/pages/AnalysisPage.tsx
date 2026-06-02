import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ExternalLink, X, Loader2, Clock, CheckCircle2 } from 'lucide-react';
import type { GitHubRepo, GitHubPR, AgentProgress } from '../types';

function useActivityLog(running: boolean) {
  const [logs, setLogs] = useState<{ time: string; text: string }[]>([]);
  useEffect(() => {
    if (!running) { setLogs([]); return; }
    const now = () => new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const entries = [
      { delay: 400,  text: 'RepoLens Agent started analysing repository structure' },
      { delay: 1300, text: 'Detected React, TypeScript, Vite configuration' },
      { delay: 2500, text: 'GuardRail Agent scanning dependencies for vulnerabilities' },
      { delay: 3200, text: 'Checking OAuth configurations and API security' },
      { delay: 3800, text: 'TestPilot Agent started test coverage analysis' },
      { delay: 4500, text: 'PlanForge Agent preparing delivery plan context' },
    ];
    const timers = entries.map(e => setTimeout(() => setLogs(prev => [...prev, { time: now(), text: e.text }]), e.delay));
    return () => timers.forEach(clearTimeout);
  }, [running]);
  return logs;
}

const AGENT_META: Record<string, { label: string; color: string; borderColor: string; bgColor: string }> = {
  repo_lens:  { label: 'Repository Intelligence', color: '#10b981', borderColor: 'rgba(16,185,129,0.3)',  bgColor: 'rgba(16,185,129,0.06)' },
  plan_forge: { label: 'Delivery Planning',        color: '#f59e0b', borderColor: 'rgba(245,158,11,0.3)',  bgColor: 'rgba(245,158,11,0.06)' },
  guardrail:  { label: 'Security Review',          color: '#3b82f6', borderColor: 'rgba(59,130,246,0.3)',  bgColor: 'rgba(59,130,246,0.06)' },
  testpilot:  { label: 'QA & Testing',             color: '#8b5cf6', borderColor: 'rgba(139,92,246,0.3)', bgColor: 'rgba(139,92,246,0.06)' },
};

function AgentCard({ agent, index }: { agent: AgentProgress; index: number }) {
  const meta = AGENT_META[agent.id];
  const isComplete = agent.status === 'complete';
  const isRunning  = agent.status === 'running';

  const statBadge = isComplete
    ? { label: 'Complete', cls: 'text-emerald-300 bg-emerald-500/15 border-emerald-500/25' }
    : isRunning
    ? { label: 'Running',  cls: 'text-blue-300   bg-blue-500/15   border-blue-500/25' }
    : agent.status === 'error'
    ? { label: 'Error',    cls: 'text-red-300     bg-red-500/15    border-red-500/25' }
    : { label: 'Pending',  cls: 'text-slate-400   bg-slate-700/30  border-slate-600/25' };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="rounded-2xl p-4"
      style={{ background: meta.bgColor, border: `1px solid ${meta.borderColor}` }}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center text-xl flex-shrink-0 border border-white/8"
            style={{ background: 'rgba(255,255,255,0.04)' }}>
            {agent.icon}
          </div>
          <div>
            <p className="text-[13px] font-bold text-white leading-tight">{agent.label}</p>
            <p className="text-[10px] text-slate-500">{meta.label}</p>
          </div>
        </div>
        <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${statBadge.cls}`}>{statBadge.label}</span>
      </div>

      {isComplete && (
        <div className="grid grid-cols-2 gap-2">
          {agent.id === 'repo_lens' && <>
            <div className="rounded-lg p-2 bg-black/20"><p className="text-[9px] text-slate-500">Files Scanned</p><p className="text-sm font-black text-white">2,431</p></div>
            <div className="rounded-lg p-2 bg-black/20"><p className="text-[9px] text-slate-500">Confidence</p><p className="text-sm font-black" style={{ color: meta.color }}>97%</p></div>
          </>}
          {agent.id === 'guardrail' && <>
            <div className="rounded-lg p-2 bg-black/20"><p className="text-[9px] text-slate-500">Scanned</p><p className="text-sm font-black text-white">1,203</p></div>
            <div className="rounded-lg p-2 bg-black/20"><p className="text-[9px] text-slate-500">Issues Found</p><p className="text-sm font-black text-amber-400">5</p></div>
          </>}
          {agent.id === 'testpilot' && <>
            <div className="rounded-lg p-2 bg-black/20"><p className="text-[9px] text-slate-500">Tests Found</p><p className="text-sm font-black text-white">—</p></div>
            <div className="rounded-lg p-2 bg-black/20"><p className="text-[9px] text-slate-500">Coverage</p><p className="text-sm font-black text-white">—</p></div>
          </>}
          {agent.id === 'plan_forge' && <>
            <div className="rounded-lg p-2 bg-black/20"><p className="text-[9px] text-slate-500">Tasks</p><p className="text-sm font-black text-white">—</p></div>
            <div className="rounded-lg p-2 bg-black/20"><p className="text-[9px] text-slate-500">Milestones</p><p className="text-sm font-black text-white">—</p></div>
          </>}
        </div>
      )}
      {isRunning && (
        <div className="flex items-center gap-2">
          <Loader2 size={12} className="animate-spin" style={{ color: meta.color }} />
          <span className="text-[11px]" style={{ color: meta.color }}>Processing…</span>
        </div>
      )}
      {!isComplete && !isRunning && (
        <div className="flex items-center gap-2">
          <Clock size={11} className="text-slate-600" />
          <span className="text-[11px] text-slate-600">Waiting…</span>
        </div>
      )}
    </motion.div>
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
    <div className="px-8 py-7 max-w-[1080px] space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-black text-white tracking-tight">Analysis in Progress</h1>
          {selectedRepo && (
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm font-semibold text-blue-400">{selectedRepo.full_name}</span>
              <ExternalLink size={12} className="text-slate-600" />
            </div>
          )}
          <p className="text-xs text-slate-500 mt-0.5">
            {selectedBranch}{selectedPull ? ` · PR #${selectedPull.number}` : ''} · Started just now
          </p>
        </div>
        <button onClick={onCancel}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-red-400 transition-all"
          style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
          <X size={14} /> Cancel Analysis
        </button>
      </motion.div>

      {/* 3-column grid */}
      <div className="grid grid-cols-3 gap-5">
        {/* Left agents */}
        <div className="space-y-3">
          {agents.slice(0, 2).map((a, i) => <AgentCard key={a.id} agent={a} index={i} />)}
        </div>

        {/* Center: ship + progress + log */}
        <div className="space-y-4">
          {/* Ship hologram */}
          <div className="rounded-2xl flex items-center justify-center relative overflow-hidden"
            style={{ height: 200, background: 'radial-gradient(ellipse at center, rgba(37,99,235,0.12) 0%, rgba(7,12,24,0.9) 70%)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="absolute w-48 h-48 rounded-full border border-blue-500/10 animate-spin" style={{ animationDuration: '18s' }} />
            <div className="absolute w-32 h-32 rounded-full border border-cyan-500/15 animate-spin" style={{ animationDuration: '12s', animationDirection: 'reverse' }} />
            <div className="absolute bottom-6 w-36 h-5 rounded-full blur-xl" style={{ background: 'rgba(59,130,246,0.3)' }} />
            <motion.span className="text-5xl z-10" animate={{ y: [-4, 4, -4] }} transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              style={{ filter: 'drop-shadow(0 0 24px rgba(59,130,246,0.7))' }}>🚢</motion.span>
          </div>

          {/* Progress */}
          <div className="rounded-2xl p-4 space-y-3" style={{ background: 'rgba(11,18,35,0.9)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="flex justify-between items-center">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Overall Progress</p>
              <span className="text-base font-black text-white">{progress}%</span>
            </div>
            <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
              <motion.div className="h-full rounded-full" style={{ background: 'linear-gradient(90deg, #1d4ed8, #0891b2)' }}
                initial={{ width: 0 }} animate={{ width: `${progress}%` }} transition={{ duration: 0.5 }} />
            </div>
            <p className="text-[10px] text-slate-600">{completeCount} of {agents.length} agents completed</p>
          </div>

          {/* Live log */}
          <div className="rounded-2xl p-4" style={{ background: 'rgba(11,18,35,0.9)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="flex items-center gap-2 mb-3">
              <motion.span className="w-1.5 h-1.5 rounded-full bg-blue-400" animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.5, repeat: Infinity }} />
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Live Activity</p>
            </div>
            <div className="space-y-1.5 max-h-32 overflow-y-auto">
              {logs.map((l, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} className="flex gap-2">
                  <span className="text-[9px] font-mono text-slate-700 flex-shrink-0 mt-0.5">{l.time}</span>
                  <span className="text-[10px] text-slate-400 leading-snug">{l.text}</span>
                </motion.div>
              ))}
              {logs.length === 0 && <p className="text-[10px] text-slate-700">Initializing agents…</p>}
            </div>
          </div>
        </div>

        {/* Right agents + info */}
        <div className="space-y-3">
          {agents.slice(2).map((a, i) => <AgentCard key={a.id} agent={a} index={i + 2} />)}

          {/* Analysis info */}
          <div className="rounded-2xl p-4" style={{ background: 'rgba(11,18,35,0.9)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Analysis Information</p>
            <div className="space-y-3">
              {[
                { icon: '📁', label: 'Repository',   val: selectedRepo?.full_name ?? '—' },
                { icon: '🌿', label: 'Branch',        val: selectedBranch },
                { icon: '🔍', label: 'Analysis Type', val: 'Full Repository' },
                { icon: '⏱', label: 'Started At',    val: new Date().toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) },
              ].map(item => (
                <div key={item.label} className="flex items-start gap-2.5">
                  <span className="text-sm mt-0.5 flex-shrink-0">{item.icon}</span>
                  <div className="min-w-0">
                    <p className="text-[10px] text-slate-600">{item.label}</p>
                    <p className="text-[12px] text-slate-300 font-medium truncate">{item.val}</p>
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

// Suppress unused import warning
const _CheckCircle2 = CheckCircle2;
void _CheckCircle2;
