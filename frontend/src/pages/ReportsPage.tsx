import { useState } from 'react';
import { motion } from 'framer-motion';
import { Download, Share2, RotateCcw, ExternalLink, ChevronRight } from 'lucide-react';
import type { ShipMateReport, SecurityFinding } from '../types';

// ── Shared: animated score ring ──────────────────────────────────────────────

function ScoreRing({ score, size = 100, strokeWidth = 7 }: { score: number; size?: number; strokeWidth?: number }) {
  const r = (size - strokeWidth * 2) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#3b82f6' : score >= 40 ? '#f59e0b' : '#ef4444';
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={strokeWidth} />
        <motion.circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeLinecap="round" strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - dash }}
          transition={{ duration: 1.2, ease: 'easeOut' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-black text-white" style={{ fontSize: size * 0.24 }}>{score}</span>
      </div>
    </div>
  );
}

// ── Animated progress bar ─────────────────────────────────────────────────────

function AnimBar({ value, color, delay = 0 }: { value: number; color: string; delay?: number }) {
  return (
    <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
      <motion.div className="h-full rounded-full" style={{ background: color }}
        initial={{ width: 0 }} animate={{ width: `${value}%` }} transition={{ duration: 1, ease: 'easeOut', delay }} />
    </div>
  );
}

// ── Overview tab ──────────────────────────────────────────────────────────────

const REC: Record<string, { headline: string; verdict: string; textColor: string; bg: string; border: string }> = {
  ready_to_ship: { headline: '🚀 READY TO SHIP',       verdict: 'SHIP IT',           textColor: '#10b981', bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.25)'  },
  mostly_ready:  { headline: '✅ MOSTLY READY TO SHIP', verdict: 'SHIP WITH CONFIDENCE', textColor: '#3b82f6', bg: 'rgba(59,130,246,0.08)',  border: 'rgba(59,130,246,0.25)'  },
  needs_review:  { headline: '⚠ SHIP WITH CAUTION',    verdict: 'SHIP WITH CAUTION', textColor: '#f59e0b', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.25)'  },
  risky_release: { headline: '🔴 RISKY RELEASE',        verdict: 'DO NOT SHIP YET',   textColor: '#f97316', bg: 'rgba(249,115,22,0.08)',  border: 'rgba(249,115,22,0.25)'  },
  not_ready:     { headline: '🛑 DO NOT SHIP',           verdict: 'BLOCKED',           textColor: '#ef4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.25)'   },
};

function OverviewTab({ report }: { report: ShipMateReport }) {
  const { score_breakdown: sb, agents, ship_recommendation } = report;
  const rec = REC[ship_recommendation] ?? REC.not_ready;

  const riskCounts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  agents.guardrail.findings.forEach((f: SecurityFinding) => {
    if (f.severity in riskCounts) riskCounts[f.severity as keyof typeof riskCounts]++;
  });

  const breakdownItems = [
    { label: 'Repository Health', val: sb.repo_score,     weight: 20, color: '#3b82f6'  },
    { label: 'Delivery Planning', val: sb.delivery_score, weight: 25, color: '#8b5cf6'  },
    { label: 'Security',          val: sb.security_score, weight: 30, color: '#f59e0b'  },
    { label: 'Test Readiness',    val: sb.test_score,     weight: 25, color: '#10b981'  },
  ];

  return (
    <div className="space-y-5">
      {/* Top 3 cards */}
      <div className="grid lg:grid-cols-3 gap-4">
        {/* Score */}
        <div className="rounded-2xl p-6 flex flex-col items-center gap-4 border border-white/6" style={{ background: 'rgba(11,18,35,0.9)' }}>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider self-start">Readiness Score</p>
          <ScoreRing score={report.readiness_score} size={120} />
          <p className="text-sm font-black text-center" style={{ color: rec.textColor }}>{rec.headline}</p>
          <p className="text-xs text-slate-500 text-center leading-relaxed">
            {report.readiness_score >= 80 ? 'Great job! Repository is ready for production.' : 'Address the following issues before deploying to production.'}
          </p>
          <button className="text-xs text-blue-400 hover:underline">View Score Breakdown</button>
        </div>

        {/* Verdict */}
        <div className="rounded-2xl p-6 border flex flex-col gap-4" style={{ background: rec.bg, borderColor: rec.border }}>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Release Commander Verdict</p>
          <div className="inline-flex items-center gap-2 px-3 py-2 rounded-xl self-start"
            style={{ background: rec.bg, border: `1px solid ${rec.border}` }}>
            <span className="text-sm font-black" style={{ color: rec.textColor }}>{rec.verdict}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Confidence:</span>
            <span className="text-sm font-black text-white">{Math.min(99, Math.round(report.readiness_score * 1.07))}%</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed flex-1">
            {report.key_blockers.length > 0
              ? `Address these issues before deploying: ${report.key_blockers.slice(0, 2).join('; ')}.`
              : 'All critical checks passed. The team is confident in this release.'}
          </p>
        </div>

        {/* Top Issues */}
        <div className="rounded-2xl p-6 border border-white/6" style={{ background: 'rgba(11,18,35,0.9)' }}>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Top Issues</p>
          <div className="space-y-1">
            {[
              { sev: 'Critical', count: riskCounts.critical, c: '#ef4444', dot: '#ef4444' },
              { sev: 'High',     count: riskCounts.high,     c: '#f97316', dot: '#f97316' },
              { sev: 'Medium',   count: riskCounts.medium,   c: '#f59e0b', dot: '#f59e0b' },
              { sev: 'Low',      count: riskCounts.low,      c: '#3b82f6', dot: '#3b82f6' },
            ].map(s => (
              <div key={s.sev} className="flex items-center justify-between py-2.5 border-b border-white/5 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: s.dot }} />
                  <span className="text-sm font-semibold" style={{ color: s.c }}>{s.sev}</span>
                </div>
                <span className="text-sm font-black text-white">{s.count}</span>
              </div>
            ))}
          </div>
          <button className="mt-3 w-full py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-colors border border-white/6 hover:border-white/12">
            View All Issues
          </button>
        </div>
      </div>

      {/* Score breakdown: 4 rings */}
      <div className="rounded-2xl p-6 border border-white/6" style={{ background: 'rgba(11,18,35,0.9)' }}>
        <p className="text-sm font-bold text-white mb-6">Score Breakdown</p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
          {breakdownItems.map((s, i) => {
            const sub = s.val >= 80 ? 'Excellent' : s.val >= 60 ? 'Good' : 'Needs Work';
            return (
              <div key={s.label} className="flex flex-col items-center gap-3">
                <ScoreRing score={s.val} size={80} strokeWidth={6} />
                <div className="text-center">
                  <p className="text-[11px] font-semibold text-slate-300">{s.label}</p>
                  <p className="text-[10px] font-bold mt-0.5" style={{ color: s.color }}>{sub}</p>
                </div>
                <AnimBar value={s.val} color={s.color} delay={i * 0.1} />
              </div>
            );
          })}
        </div>
      </div>

      {/* Recommended actions */}
      {report.next_actions.length > 0 && (
        <div className="rounded-2xl p-6 border border-white/6" style={{ background: 'rgba(11,18,35,0.9)' }}>
          <p className="text-sm font-bold text-white mb-4">Recommended Actions</p>
          <div className="space-y-1">
            {report.next_actions.slice(0, 5).map((action, i) => {
              const isHigh = i < 2;
              const isMed  = i < 4;
              const badgeCls = isHigh ? { bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.25)', color: '#fca5a5', label: 'High' }
                : isMed ? { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.25)', color: '#fcd34d', label: 'Medium' }
                : { bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.25)', color: '#93c5fd', label: 'Low' };
              return (
                <div key={i} className="flex items-center gap-3 py-3 border-b border-white/5 last:border-0">
                  <span className="text-xs font-black text-slate-600 w-5 text-right flex-shrink-0">{i + 1}.</span>
                  <p className="text-[13px] text-slate-300 flex-1 leading-snug">{action}</p>
                  <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full flex-shrink-0"
                    style={{ background: badgeCls.bg, border: `1px solid ${badgeCls.border}`, color: badgeCls.color }}>
                    {badgeCls.label}
                  </span>
                </div>
              );
            })}
          </div>
          {report.next_actions.length > 5 && (
            <button className="mt-3 w-full py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white border border-white/6 transition-colors">
              View All Recommendations
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── RepoLens tab ──────────────────────────────────────────────────────────────

function RepoLensTab({ report }: { report: ShipMateReport }) {
  const rl = report.agents.repo_lens;
  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div className="rounded-2xl p-5 border border-white/6 space-y-4" style={{ background: 'rgba(11,18,35,0.9)' }}>
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2.5">Tech Stack</p>
          <div className="flex flex-wrap gap-2">{rl.tech_stack.map(t => (
            <span key={t} className="px-3 py-1 rounded-full text-xs font-medium border" style={{ background: 'rgba(59,130,246,0.08)', borderColor: 'rgba(59,130,246,0.2)', color: '#93c5fd' }}>{t}</span>
          ))}</div>
        </div>
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Architecture</p>
          <p className="text-sm text-slate-200">{rl.architecture_pattern}</p>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {rl.has_ci_cd      && <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold border" style={{ background: 'rgba(16,185,129,0.08)', borderColor: 'rgba(16,185,129,0.2)', color: '#6ee7b7' }}>✓ CI/CD</span>}
            {rl.has_dockerfile && <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold border" style={{ background: 'rgba(59,130,246,0.08)', borderColor: 'rgba(59,130,246,0.2)', color: '#93c5fd' }}>✓ Docker</span>}
            {rl.has_tests      && <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold border" style={{ background: 'rgba(139,92,246,0.08)', borderColor: 'rgba(139,92,246,0.2)', color: '#c4b5fd' }}>✓ Tests</span>}
          </div>
        </div>
      </div>
      <div className="rounded-2xl p-5 border border-white/6 space-y-4" style={{ background: 'rgba(11,18,35,0.9)' }}>
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2.5">Dependencies</p>
          {Object.entries(rl.dependency_summary).map(([type, deps]) => (
            <div key={type} className="mb-3">
              <p className="text-[10px] text-slate-600 capitalize mb-1.5">{type}</p>
              <div className="flex flex-wrap gap-1.5">
                {(deps as string[]).slice(0, 6).map((d: string) => (
                  <span key={d} className="text-[10px] font-mono text-slate-300 px-2 py-0.5 rounded border" style={{ background: 'rgba(255,255,255,0.04)', borderColor: 'rgba(255,255,255,0.08)' }}>{d}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
        {rl.architecture_risks.length > 0 && (
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Architecture Risks</p>
            {rl.architecture_risks.map((r, i) => (
              <p key={i} className="text-xs text-slate-400 flex items-start gap-1.5 mb-1">
                <span className="text-amber-400 flex-shrink-0">⚠</span>{r.risk}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── GuardRail tab ─────────────────────────────────────────────────────────────

function GuardRailTab({ report }: { report: ShipMateReport }) {
  const gr = report.agents.guardrail;
  const SEV: Record<string, { bg: string; border: string; color: string }> = {
    critical: { bg: 'rgba(239,68,68,0.08)',  border: 'rgba(239,68,68,0.2)',  color: '#fca5a5' },
    high:     { bg: 'rgba(249,115,22,0.08)', border: 'rgba(249,115,22,0.2)', color: '#fdba74' },
    medium:   { bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.2)', color: '#fcd34d' },
    low:      { bg: 'rgba(59,130,246,0.08)', border: 'rgba(59,130,246,0.2)', color: '#93c5fd' },
    info:     { bg: 'rgba(100,116,139,0.08)',border: 'rgba(100,116,139,0.2)',color: '#94a3b8' },
  };
  return (
    <div className="space-y-3">
      {gr.findings.length > 0 ? gr.findings.map((f, i) => {
        const s = SEV[f.severity] ?? SEV.info;
        return (
          <div key={i} className="rounded-2xl p-5 border" style={{ background: s.bg, borderColor: s.border }}>
            <div className="flex items-start justify-between gap-3 mb-2">
              <p className="text-sm font-bold text-white">{f.title}</p>
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full border capitalize flex-shrink-0"
                style={{ background: s.bg, borderColor: s.border, color: s.color }}>{f.severity}</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed mb-2">{f.description}</p>
            <p className="text-xs flex items-center gap-1.5" style={{ color: '#6ee7b7' }}>
              <ChevronRight size={11} /> {f.recommendation}
            </p>
            {f.file && <p className="text-[10px] text-slate-600 font-mono mt-1.5">📁 {f.file}</p>}
          </div>
        );
      }) : (
        <div className="rounded-2xl p-10 text-center border border-white/6" style={{ background: 'rgba(11,18,35,0.9)' }}>
          <p className="text-emerald-400 text-sm font-semibold">✓ No security findings detected</p>
        </div>
      )}
    </div>
  );
}

// ── PlanForge tab ─────────────────────────────────────────────────────────────

function PlanForgeTab({ report }: { report: ShipMateReport }) {
  const pf = report.agents.plan_forge;
  return (
    <div className="space-y-4">
      <div className="rounded-2xl p-4 border" style={{ background: 'rgba(59,130,246,0.06)', borderColor: 'rgba(59,130,246,0.2)' }}>
        <p className="text-[10px] font-bold text-blue-400 uppercase tracking-wider mb-1">Next Best Action</p>
        <p className="text-sm font-semibold text-slate-200">{pf.next_best_action}</p>
        <p className="text-xs text-slate-500 mt-1">Estimated effort: {pf.estimated_effort}</p>
      </div>
      {pf.milestones.map((m, i) => {
        const pri = m.priority === 'high' || m.priority === 'critical'
          ? { bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.2)', color: '#fca5a5' }
          : m.priority === 'medium'
          ? { bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.2)', color: '#fcd34d' }
          : { bg: 'rgba(59,130,246,0.08)', border: 'rgba(59,130,246,0.2)', color: '#93c5fd' };
        return (
          <div key={i} className="rounded-2xl p-5 border border-white/6" style={{ background: 'rgba(11,18,35,0.9)' }}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-bold text-white">{m.title}</p>
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full border capitalize"
                style={{ background: pri.bg, borderColor: pri.border, color: pri.color }}>{m.priority}</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">{m.description}</p>
            <p className="text-[10px] text-slate-600 mt-2">Est. {m.estimated_days} days · {m.category}</p>
          </div>
        );
      })}
    </div>
  );
}

// ── TestPilot tab ─────────────────────────────────────────────────────────────

function TestPilotTab({ report }: { report: ShipMateReport }) {
  const tp = report.agents.testpilot;
  const qaColor = tp.qa_readiness === 'ready' ? '#10b981' : tp.qa_readiness === 'partial' ? '#f59e0b' : '#ef4444';
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        {[
          { val: tp.existing_tests.count, label: 'Test Files', color: '#fff' },
          { val: `${tp.existing_tests.coverage_estimate}%`, label: 'Coverage', color: '#10b981' },
          { val: tp.qa_readiness === 'ready' ? 'QA Ready' : tp.qa_readiness === 'partial' ? 'Partial' : 'Not Ready', label: 'QA Status', color: qaColor },
        ].map(s => (
          <div key={s.label} className="rounded-xl p-4 text-center border border-white/6" style={{ background: 'rgba(11,18,35,0.9)' }}>
            <p className="text-2xl font-black" style={{ color: s.color }}>{s.val}</p>
            <p className="text-xs text-slate-500 mt-1">{s.label}</p>
          </div>
        ))}
      </div>
      {tp.suggested_tests.map((t, i) => {
        const pri = t.priority === 'critical' || t.priority === 'high'
          ? { bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.2)', color: '#fca5a5' }
          : { bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.2)', color: '#fcd34d' };
        return (
          <div key={i} className="rounded-2xl p-5 border border-white/6" style={{ background: 'rgba(11,18,35,0.9)' }}>
            <div className="flex items-center justify-between gap-3 mb-2">
              <p className="text-sm font-bold text-white font-mono">{t.name}</p>
              <div className="flex gap-1.5 flex-shrink-0">
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full border"
                  style={{ background: 'rgba(139,92,246,0.08)', borderColor: 'rgba(139,92,246,0.2)', color: '#c4b5fd' }}>{t.type}</span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full border"
                  style={{ background: pri.bg, borderColor: pri.border, color: pri.color }}>{t.priority}</span>
              </div>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">{t.description}</p>
          </div>
        );
      })}
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

const TABS = ['Overview', 'RepoLens', 'PlanForge', 'GuardRail', 'TestPilot'] as const;
type Tab = typeof TABS[number];

interface Props { report: ShipMateReport; onReRun: () => void; }

export function ReportsPage({ report, onReRun }: Props) {
  const [tab, setTab] = useState<Tab>('Overview');
  const fmt = (d: string) => new Date(d).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

  return (
    <div className="px-8 py-7 max-w-[1080px] space-y-5">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-[22px] font-black text-white tracking-tight">Analysis Report</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm font-semibold text-blue-400">{report.repo.full_name}</span>
            <ExternalLink size={11} className="text-slate-600" />
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Completed {fmt(report.generated_at)} · <span className="text-blue-400">Full Analysis</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border border-white/8 text-slate-300 hover:text-white hover:border-white/15 transition-all">
            <Download size={12} /> Download PDF
          </button>
          <button className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border border-white/8 text-slate-300 hover:text-white hover:border-white/15 transition-all">
            <Share2 size={12} /> Share Report
          </button>
          <button onClick={onReRun} className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all"
            style={{ background: 'linear-gradient(135deg, #1d4ed8, #0891b2)' }}>
            <RotateCcw size={12} /> Re-run Analysis
          </button>
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="flex items-center gap-0 border-b border-white/6">
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-5 py-3 text-sm font-semibold border-b-2 -mb-px transition-all ${
              tab === t ? 'text-white border-blue-500' : 'text-slate-500 border-transparent hover:text-slate-300'
            }`}>
            {t}
          </button>
        ))}
      </div>

      {/* Content */}
      <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18 }}>
        {tab === 'Overview'  && <OverviewTab  report={report} />}
        {tab === 'RepoLens'  && <RepoLensTab  report={report} />}
        {tab === 'PlanForge' && <PlanForgeTab report={report} />}
        {tab === 'GuardRail' && <GuardRailTab report={report} />}
        {tab === 'TestPilot' && <TestPilotTab report={report} />}
      </motion.div>
    </div>
  );
}
