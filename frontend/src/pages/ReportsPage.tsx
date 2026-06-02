import { useState } from 'react';
import { motion } from 'framer-motion';
import { Download, Share2, RotateCcw, ExternalLink } from 'lucide-react';
import type { ShipMateReport, SecurityFinding } from '../types';

// ── Score ring ────────────────────────────────────────────────────────────────

function ScoreRing({ score, size = 120, label }: { score: number; size?: number; label?: string }) {
  const r = (size - 14) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#3b82f6' : score >= 40 ? '#f59e0b' : '#ef4444';
  const textColor = score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-blue-400' : score >= 40 ? 'text-yellow-400' : 'text-red-400';
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="7" />
          <motion.circle
            cx={size/2} cy={size/2} r={r} fill="none"
            stroke={color} strokeWidth="7" strokeLinecap="round"
            strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ - dash }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-black text-white">{score}</span>
        </div>
      </div>
      {label && <p className={`text-xs font-bold text-center ${textColor}`}>{label}</p>}
    </div>
  );
}

// ── Tab: Overview ─────────────────────────────────────────────────────────────

const REC_CONFIG: Record<string, { label: string; verdict: string; color: string; bg: string; border: string }> = {
  ready_to_ship: { label: '🚀 READY TO SHIP',      verdict: 'READY TO SHIP',   color: 'text-emerald-300', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  mostly_ready:  { label: '✅ MOSTLY READY TO SHIP', verdict: 'SHIP WITH CONFIDENCE', color: 'text-blue-300', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
  needs_review:  { label: '⚠ SHIP WITH CAUTION',   verdict: 'SHIP WITH CAUTION', color: 'text-yellow-300', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30' },
  risky_release: { label: '🔴 RISKY RELEASE',       verdict: 'DO NOT SHIP YET',  color: 'text-orange-300', bg: 'bg-orange-500/10', border: 'border-orange-500/30' },
  not_ready:     { label: '🛑 DO NOT SHIP',          verdict: 'DO NOT SHIP',      color: 'text-red-300',    bg: 'bg-red-500/10',    border: 'border-red-500/30'    },
};

function OverviewTab({ report }: { report: ShipMateReport }) {
  const rec = REC_CONFIG[report.ship_recommendation] ?? REC_CONFIG.not_ready;
  const { score_breakdown: sb, agents } = report;

  const riskCounts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  agents.guardrail.findings.forEach((f: SecurityFinding) => {
    if (f.severity in riskCounts) riskCounts[f.severity as keyof typeof riskCounts]++;
  });

  return (
    <div className="space-y-5">
      {/* Top row: score + verdict + top issues */}
      <div className="grid lg:grid-cols-3 gap-4">
        {/* Score */}
        <div className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-6 flex flex-col items-center gap-3">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider self-start">Readiness Score</p>
          <ScoreRing score={report.readiness_score} size={120} />
          <p className={`text-sm font-black text-center ${rec.color}`}>
            {rec.label}
          </p>
          <p className="text-xs text-slate-500 text-center leading-relaxed">
            {report.readiness_score >= 80
              ? 'Great job! Your repository is ready for production.'
              : 'Your codebase is in good shape but address the following issues before production deployment.'}
          </p>
          <button className="text-xs text-blue-400 hover:underline mt-1">View Score Breakdown</button>
        </div>

        {/* Verdict */}
        <div className={`rounded-2xl border p-6 ${rec.bg} ${rec.border}`}>
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Release Commander Verdict</p>
          <div className="flex items-center gap-2 mb-3">
            <span className={`text-sm font-black px-3 py-1.5 rounded-lg ${rec.bg} ${rec.border} border ${rec.color}`}>
              {rec.verdict}
            </span>
          </div>
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs text-slate-400">Confidence:</span>
            <span className="text-sm font-black text-white">
              {Math.min(99, Math.round(report.readiness_score * 1.07))}%
            </span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            {report.key_blockers.length > 0
              ? `Address the following issues before production: ${report.key_blockers.slice(0, 2).join(', ')}.`
              : 'All critical checks passed. The team is ready to release.'}
          </p>
        </div>

        {/* Top Issues */}
        <div className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-6">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Top Issues</p>
          <div className="space-y-2">
            {[
              { sev: 'Critical', count: riskCounts.critical, color: 'text-red-400',    dot: 'bg-red-500'    },
              { sev: 'High',     count: riskCounts.high,     color: 'text-orange-400', dot: 'bg-orange-500' },
              { sev: 'Medium',   count: riskCounts.medium,   color: 'text-yellow-400', dot: 'bg-yellow-500' },
              { sev: 'Low',      count: riskCounts.low,      color: 'text-blue-400',   dot: 'bg-blue-500'   },
            ].map(s => (
              <div key={s.sev} className="flex items-center justify-between py-1.5 border-b border-slate-800/40 last:border-0">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${s.dot}`} />
                  <span className={`text-sm font-semibold ${s.color}`}>{s.sev}</span>
                </div>
                <span className="text-sm font-black text-white">{s.count}</span>
              </div>
            ))}
          </div>
          <button className="mt-4 w-full py-2 rounded-xl bg-slate-800/60 border border-slate-700/40 text-xs font-semibold text-slate-300 hover:text-white transition-colors">
            View All Issues
          </button>
        </div>
      </div>

      {/* Score breakdown: 4 rings */}
      <div className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-6">
        <p className="text-sm font-bold text-white mb-5">Score Breakdown</p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { label: 'Repository Health', val: sb.repo_score,     sub: sb.repo_score >= 80 ? 'Excellent' : 'Good' },
            { label: 'Delivery Planning', val: sb.delivery_score, sub: sb.delivery_score >= 80 ? 'Excellent' : 'Good' },
            { label: 'Security',          val: sb.security_score, sub: sb.security_score >= 70 ? 'Good' : 'Needs Work' },
            { label: 'Test Readiness',    val: sb.test_score,     sub: sb.test_score >= 80 ? 'Excellent' : 'Good' },
          ].map(s => (
            <div key={s.label} className="flex flex-col items-center gap-2">
              <ScoreRing score={s.val} size={80} />
              <div className="text-center">
                <p className="text-xs font-semibold text-slate-300">{s.label}</p>
                <p className={`text-[10px] font-bold mt-0.5 ${s.val >= 80 ? 'text-emerald-400' : s.val >= 60 ? 'text-blue-400' : 'text-yellow-400'}`}>{s.sub}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recommended actions */}
      <div className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-6">
        <p className="text-sm font-bold text-white mb-4">Recommended Actions</p>
        <div className="space-y-2">
          {report.next_actions.slice(0, 5).map((action, i) => {
            const isHigh = i < 2 || report.key_blockers.some(b => action.toLowerCase().includes(b.toLowerCase().slice(0, 10)));
            const badge = isHigh
              ? 'bg-red-500/15 text-red-300 border-red-500/30'
              : i < 4
              ? 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30'
              : 'bg-blue-500/15 text-blue-300 border-blue-500/30';
            const priority = isHigh ? 'High' : i < 4 ? 'Medium' : 'Low';
            return (
              <div key={i} className="flex items-start gap-3 py-2.5 border-b border-slate-800/40 last:border-0">
                <span className="text-xs font-black text-slate-500 w-5 text-right flex-shrink-0 mt-0.5">{i + 1}.</span>
                <p className="text-xs text-slate-300 flex-1 leading-relaxed">{action}</p>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border flex-shrink-0 ${badge}`}>{priority}</span>
              </div>
            );
          })}
        </div>
        {report.next_actions.length > 5 && (
          <button className="mt-4 w-full py-2 rounded-xl bg-slate-800/60 border border-slate-700/40 text-xs font-semibold text-slate-300 hover:text-white transition-colors">
            View All Recommendations
          </button>
        )}
      </div>
    </div>
  );
}

// ── Tab: RepoLens ─────────────────────────────────────────────────────────────

function RepoLensTab({ report }: { report: ShipMateReport }) {
  const rl = report.agents.repo_lens;
  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-5 space-y-3">
        <p className="text-sm font-bold text-white">Tech Stack</p>
        <div className="flex flex-wrap gap-2">
          {rl.tech_stack.map(t => (
            <span key={t} className="px-3 py-1 rounded-full text-xs font-medium bg-blue-500/10 border border-blue-500/20 text-blue-300">{t}</span>
          ))}
        </div>
        <p className="text-sm font-bold text-white pt-2">Architecture</p>
        <p className="text-xs text-slate-300">{rl.architecture_pattern}</p>
        <div className="flex gap-2 flex-wrap">
          {rl.has_ci_cd && <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">✓ CI/CD</span>}
          {rl.has_dockerfile && <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold bg-blue-500/10 border border-blue-500/20 text-blue-400">✓ Docker</span>}
          {rl.has_tests && <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold bg-purple-500/10 border border-purple-500/20 text-purple-400">✓ Tests</span>}
        </div>
      </div>
      <div className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-5 space-y-3">
        <p className="text-sm font-bold text-white">Dependencies</p>
        {Object.entries(rl.dependency_summary).map(([type, deps]) => (
          <div key={type}>
            <p className="text-[10px] text-slate-500 capitalize mb-1.5">{type}</p>
            <div className="flex flex-wrap gap-1.5">
              {(deps as string[]).slice(0, 6).map((d: string) => (
                <span key={d} className="text-[10px] font-mono text-slate-300 bg-slate-800/60 border border-slate-700/40 rounded px-2 py-0.5">{d}</span>
              ))}
            </div>
          </div>
        ))}
        <p className="text-sm font-bold text-white pt-2">Architecture Risks</p>
        {rl.architecture_risks.length > 0 ? rl.architecture_risks.map((r, i) => (
          <div key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
            <span className="text-amber-400 flex-shrink-0">⚠</span>{r.risk}
          </div>
        )) : <p className="text-xs text-emerald-400">No architecture risks detected.</p>}
      </div>
    </div>
  );
}

// ── Tab: GuardRail ────────────────────────────────────────────────────────────

function GuardRailTab({ report }: { report: ShipMateReport }) {
  const gr = report.agents.guardrail;
  const SEV_COLOR: Record<string, string> = {
    critical: 'text-red-400 bg-red-500/10 border-red-500/20',
    high: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
    medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
    low: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    info: 'text-slate-400 bg-slate-700/30 border-slate-600/30',
  };
  return (
    <div className="space-y-4">
      {gr.findings.length > 0 ? gr.findings.map((f, i) => (
        <div key={i} className="rounded-xl bg-slate-900/70 border border-slate-800/60 p-4">
          <div className="flex items-start justify-between gap-3 mb-2">
            <p className="text-sm font-bold text-white">{f.title}</p>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border capitalize flex-shrink-0 ${SEV_COLOR[f.severity] ?? SEV_COLOR.info}`}>{f.severity}</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed mb-2">{f.description}</p>
          <p className="text-xs text-emerald-400">→ {f.recommendation}</p>
          {f.file && <p className="text-[10px] text-slate-600 font-mono mt-1">📁 {f.file}</p>}
        </div>
      )) : <p className="text-sm text-emerald-400 p-4">No security findings detected.</p>}
    </div>
  );
}

// ── Tab: PlanForge ────────────────────────────────────────────────────────────

function PlanForgeTab({ report }: { report: ShipMateReport }) {
  const pf = report.agents.plan_forge;
  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-blue-500/8 border border-blue-500/20 p-4">
        <p className="text-xs text-slate-400 mb-1">Next Best Action</p>
        <p className="text-sm font-semibold text-blue-300">{pf.next_best_action}</p>
        <p className="text-xs text-slate-500 mt-1">Estimated effort: {pf.estimated_effort}</p>
      </div>
      {pf.milestones.map((m, i) => (
        <div key={i} className="rounded-xl bg-slate-900/70 border border-slate-800/60 p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-bold text-white">{m.title}</p>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
              m.priority === 'high' || m.priority === 'critical' ? 'text-red-300 bg-red-500/10 border-red-500/20'
              : m.priority === 'medium' ? 'text-yellow-300 bg-yellow-500/10 border-yellow-500/20'
              : 'text-blue-300 bg-blue-500/10 border-blue-500/20'
            }`}>{m.priority}</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">{m.description}</p>
          <p className="text-[10px] text-slate-500 mt-2">Est. {m.estimated_days} days · {m.category}</p>
        </div>
      ))}
    </div>
  );
}

// ── Tab: TestPilot ────────────────────────────────────────────────────────────

function TestPilotTab({ report }: { report: ShipMateReport }) {
  const tp = report.agents.testpilot;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl bg-slate-900/70 border border-slate-800/60 p-4 text-center">
          <p className="text-2xl font-black text-white">{tp.existing_tests.count}</p>
          <p className="text-xs text-slate-500 mt-1">Test Files</p>
        </div>
        <div className="rounded-xl bg-slate-900/70 border border-slate-800/60 p-4 text-center">
          <p className="text-2xl font-black text-emerald-400">{tp.existing_tests.coverage_estimate}%</p>
          <p className="text-xs text-slate-500 mt-1">Coverage</p>
        </div>
        <div className="rounded-xl bg-slate-900/70 border border-slate-800/60 p-4 text-center">
          <p className={`text-sm font-bold mt-1 ${tp.qa_readiness === 'ready' ? 'text-emerald-400' : tp.qa_readiness === 'partial' ? 'text-yellow-400' : 'text-red-400'}`}>
            {tp.qa_readiness === 'ready' ? 'QA Ready' : tp.qa_readiness === 'partial' ? 'Partial' : 'Not Ready'}
          </p>
          <p className="text-xs text-slate-500 mt-1">QA Status</p>
        </div>
      </div>
      {tp.suggested_tests.map((t, i) => (
        <div key={i} className="rounded-xl bg-slate-900/70 border border-slate-800/60 p-4">
          <div className="flex items-center justify-between gap-3 mb-2">
            <p className="text-sm font-bold text-white font-mono">{t.name}</p>
            <div className="flex gap-1.5">
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300">{t.type}</span>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                t.priority === 'critical' ? 'bg-red-500/10 border-red-500/20 text-red-300'
                : t.priority === 'high' ? 'bg-orange-500/10 border-orange-500/20 text-orange-300'
                : 'bg-yellow-500/10 border-yellow-500/20 text-yellow-300'
              }`}>{t.priority}</span>
            </div>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">{t.description}</p>
        </div>
      ))}
    </div>
  );
}

// ── Main ReportsPage ──────────────────────────────────────────────────────────

const TABS = ['Overview', 'RepoLens', 'PlanForge', 'GuardRail', 'TestPilot'] as const;
type Tab = typeof TABS[number];

interface Props {
  report: ShipMateReport;
  onReRun: () => void;
}

export function ReportsPage({ report, onReRun }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('Overview');

  const fmt = (d: string) => new Date(d).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

  return (
    <div className="p-6 space-y-5 max-w-[1100px]">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-black text-white">Analysis Report</h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm text-blue-400 font-semibold">{report.repo.full_name}</span>
              <ExternalLink size={12} className="text-slate-500" />
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Completed {fmt(report.generated_at)} ·{' '}
              <span className="text-blue-400">Full Analysis</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border border-slate-700/50 text-slate-300 hover:text-white hover:border-slate-600 transition-all">
              <Download size={13} /> Download PDF
            </button>
            <button className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border border-slate-700/50 text-slate-300 hover:text-white hover:border-slate-600 transition-all">
              <Share2 size={13} /> Share Report
            </button>
            <button
              onClick={onReRun}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-all"
            >
              <RotateCcw size={13} /> Re-run Analysis
            </button>
          </div>
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-800/60">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2.5 text-sm font-semibold transition-all border-b-2 -mb-px ${
              activeTab === tab
                ? 'text-white border-blue-500'
                : 'text-slate-500 border-transparent hover:text-slate-300 hover:border-slate-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        {activeTab === 'Overview'  && <OverviewTab report={report} />}
        {activeTab === 'RepoLens'  && <RepoLensTab report={report} />}
        {activeTab === 'PlanForge' && <PlanForgeTab report={report} />}
        {activeTab === 'GuardRail' && <GuardRailTab report={report} />}
        {activeTab === 'TestPilot' && <TestPilotTab report={report} />}
      </motion.div>
    </div>
  );
}
