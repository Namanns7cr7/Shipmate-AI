import { motion } from 'framer-motion';
import {
  Copy, GitBranch, ExternalLink, Shield, CheckCircle2, AlertTriangle,
  FlaskConical, LayoutDashboard, Clock, ChevronRight, Loader2,
} from 'lucide-react';
import type { AppState, AgentProgress, GitHubRepo, GitHubPR, ShipMateReport, SecurityFinding } from '../../types';

// ── helpers ─────────────────────────────────────────────────────────────────

function fmt(date: string) {
  return new Date(date).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function copyText(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

const REC_STYLE: Record<string, { label: string; dot: string; text: string; bg: string; border: string }> = {
  ready_to_ship: { label: 'Ready to Ship', dot: 'bg-emerald-400', text: 'text-emerald-300', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  mostly_ready:  { label: 'Mostly Ready',  dot: 'bg-yellow-400',  text: 'text-yellow-300',  bg: 'bg-yellow-500/10',  border: 'border-yellow-500/30'  },
  needs_review:  { label: 'Needs Review',  dot: 'bg-orange-400',  text: 'text-orange-300',  bg: 'bg-orange-500/10',  border: 'border-orange-500/30'  },
  risky_release: { label: 'Risky Release', dot: 'bg-red-400',     text: 'text-red-300',     bg: 'bg-red-500/10',     border: 'border-red-500/30'     },
  not_ready:     { label: 'Do NOT Ship',   dot: 'bg-red-500',     text: 'text-red-400',     bg: 'bg-red-500/15',     border: 'border-red-500/40'     },
};

// ── skeleton block ───────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return <div className={`rounded-lg bg-slate-800/60 animate-pulse ${className}`} />;
}

// ── animated bar ─────────────────────────────────────────────────────────────

function Bar({ value, color, delay = 0 }: { value: number; color: string; delay?: number }) {
  return (
    <div className="h-1.5 rounded-full bg-slate-700/50 overflow-hidden">
      <motion.div
        className={`h-full rounded-full ${color}`}
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 1, ease: 'easeOut', delay }}
      />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard Header
// ─────────────────────────────────────────────────────────────────────────────

function DashboardHeader({
  repo, branch, pull, generatedAt,
}: {
  repo: GitHubRepo;
  branch: string;
  pull: GitHubPR | null;
  generatedAt?: string;
}) {
  return (
    <div className="glass-card p-4 flex flex-wrap items-center gap-4">
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <img src={repo.owner.avatar_url} alt="" className="w-8 h-8 rounded-full ring-1 ring-slate-700 flex-shrink-0" />
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-slate-300">{repo.owner.login}</span>
            <span className="text-slate-600">/</span>
            <span className="text-sm font-black text-white">{repo.name}</span>
            <button
              onClick={() => copyText(repo.full_name)}
              className="p-1 rounded text-slate-600 hover:text-slate-300 transition-colors"
              title="Copy repo name"
            >
              <Copy size={12} />
            </button>
            <a
              href={repo.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1 rounded text-slate-600 hover:text-slate-300 transition-colors"
              title="Open on GitHub"
            >
              <ExternalLink size={12} />
            </a>
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <GitBranch size={10} />{branch}
            </span>
            {pull && <span>PR #{pull.number}</span>}
            {generatedAt && (
              <span className="flex items-center gap-1">
                <Clock size={10} />Last: {fmt(generatedAt)}
              </span>
            )}
          </div>
        </div>
      </div>
      {repo.description && (
        <p className="hidden lg:block text-xs text-slate-500 max-w-xs truncate">{repo.description}</p>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Empty state (no repo selected)
// ─────────────────────────────────────────────────────────────────────────────

function NoRepoState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4"
    >
      <div className="text-5xl mb-5">🚢</div>
      <h2 className="text-xl font-black text-slate-100 mb-2">Select a repository to begin</h2>
      <p className="text-sm text-slate-500 max-w-sm leading-relaxed">
        Choose a repository from the left sidebar. ShipMate AI will run 4 specialized agents — RepoLens, PlanForge, GuardRail, and TestPilot — to generate your release readiness score.
      </p>
      <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-3 w-full max-w-lg">
        {[
          { icon: '🔍', name: 'RepoLens',  accent: 'border-blue-500/20 bg-blue-500/5' },
          { icon: '📋', name: 'PlanForge', accent: 'border-purple-500/20 bg-purple-500/5' },
          { icon: '🔒', name: 'GuardRail', accent: 'border-amber-500/20 bg-amber-500/5' },
          { icon: '🧪', name: 'TestPilot', accent: 'border-emerald-500/20 bg-emerald-500/5' },
        ].map(a => (
          <div key={a.name} className={`rounded-xl border p-3 text-center ${a.accent}`}>
            <div className="text-2xl mb-1">{a.icon}</div>
            <p className="text-xs font-semibold text-slate-400">{a.name}</p>
            <div className="mt-1 h-0.5 rounded-full bg-slate-700/60" />
          </div>
        ))}
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Repo selected, waiting for analysis
// ─────────────────────────────────────────────────────────────────────────────

function ReadyToAnalyzeState({ repo, onAnalyze }: { repo: GitHubRepo; onAnalyze: () => void }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      {/* Agent preview cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { icon: '🔍', name: 'RepoLens',  desc: 'Repo structure & tech stack', accent: 'border-blue-500/20' },
          { icon: '📋', name: 'PlanForge', desc: 'Tasks & delivery plan',        accent: 'border-purple-500/20' },
          { icon: '🔒', name: 'GuardRail', desc: 'Security & risk analysis',     accent: 'border-amber-500/20' },
          { icon: '🧪', name: 'TestPilot', desc: 'Test coverage & QA gates',     accent: 'border-emerald-500/20' },
        ].map(a => (
          <div key={a.name} className={`glass-card border ${a.accent} p-4 text-center`}>
            <div className="text-3xl mb-2">{a.icon}</div>
            <p className="text-sm font-bold text-slate-200">{a.name}</p>
            <p className="text-xs text-slate-500 mt-1">{a.desc}</p>
            <div className="mt-3 flex items-center justify-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-600" />
              <span className="text-[10px] text-slate-600">Idle</span>
            </div>
          </div>
        ))}
      </div>

      {/* CTA banner */}
      <div className="glass-card p-6 flex flex-col sm:flex-row items-center gap-4 text-center sm:text-left">
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-bold text-white mb-1">Ready to analyze <span className="text-blue-400">{repo.full_name}</span></h3>
          <p className="text-sm text-slate-400">
            Click "Analyze Readiness" in the sidebar to run the 4-agent pipeline. Results appear here in real time.
          </p>
        </div>
        <button
          onClick={onAnalyze}
          className="btn-primary flex items-center gap-2 px-5 py-2.5 text-sm font-bold rounded-xl flex-shrink-0"
        >
          <span className="relative z-10">Run Analysis</span>
          <ChevronRight size={16} className="relative z-10" />
        </button>
      </div>

      {/* Placeholder cards */}
      <div className="grid lg:grid-cols-3 gap-4">
        {['Release Score', 'Risk Breakdown', 'Test Coverage'].map(title => (
          <div key={title} className="glass-card p-5">
            <p className="text-xs font-semibold text-slate-500 mb-3">{title}</p>
            <div className="space-y-2">
              <Skeleton className="h-10 w-24" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-3/4" />
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Analyzing state (skeletons + agent swarm)
// ─────────────────────────────────────────────────────────────────────────────

function AnalyzingState({ agents }: { agents: AgentProgress[] }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      {/* Agent cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {agents.map(a => {
          const isRunning = a.status === 'running';
          const isDone    = a.status === 'complete';
          const isError   = a.status === 'error';
          const colors = {
            repo_lens:  { border: 'border-blue-500/40',   ring: 'ring-blue-500/30',   dot: 'bg-blue-400'    },
            plan_forge: { border: 'border-purple-500/40', ring: 'ring-purple-500/30', dot: 'bg-purple-400'  },
            guardrail:  { border: 'border-amber-500/40',  ring: 'ring-amber-500/30',  dot: 'bg-amber-400'   },
            testpilot:  { border: 'border-emerald-500/40',ring: 'ring-emerald-500/30',dot: 'bg-emerald-400' },
          }[a.id];
          return (
            <div
              key={a.id}
              className={`glass-card border p-4 text-center transition-all duration-500 ${
                isRunning ? `${colors.border} ring-1 ${colors.ring}` :
                isDone    ? 'border-emerald-500/30' :
                isError   ? 'border-red-500/30' :
                            'border-slate-700/30'
              }`}
            >
              <div className="text-3xl mb-2">{a.icon}</div>
              <p className="text-sm font-bold text-slate-200">{a.label}</p>
              <div className="mt-3 flex items-center justify-center gap-1.5">
                {isRunning ? (
                  <><span className={`w-1.5 h-1.5 rounded-full ${colors.dot} animate-pulse`} />
                  <span className="text-[10px] text-slate-300">Analyzing…</span></>
                ) : isDone ? (
                  <><span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span className="text-[10px] text-emerald-400">Complete</span></>
                ) : isError ? (
                  <><span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  <span className="text-[10px] text-red-400">Error</span></>
                ) : (
                  <><span className="w-1.5 h-1.5 rounded-full bg-slate-600" />
                  <span className="text-[10px] text-slate-600">Waiting…</span></>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Skeleton cards */}
      <div className="grid lg:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map(i => (
          <div key={i} className="glass-card p-5 space-y-3">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-10 w-20" />
            <Skeleton className="h-2.5 w-full" />
            <Skeleton className="h-2.5 w-3/4" />
            <Skeleton className="h-2.5 w-1/2" />
          </div>
        ))}
      </div>

      <div className="flex items-center justify-center gap-3 py-2 text-sm text-slate-500">
        <Loader2 size={16} className="animate-spin" />
        Running 4-agent analysis pipeline…
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Results dashboard (real data)
// ─────────────────────────────────────────────────────────────────────────────

function ResultsDashboard({ report }: { report: ShipMateReport }) {
  const { agents, score_breakdown: sb, ship_recommendation: rec } = report;
  const recStyle = REC_STYLE[rec] ?? REC_STYLE.not_ready;

  // Risk counts
  const riskCounts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  agents.guardrail.findings.forEach((f: SecurityFinding) => {
    if (f.severity in riskCounts) riskCounts[f.severity as keyof typeof riskCounts]++;
  });
  const totalRisks = agents.guardrail.findings.length;

  // Language fake distribution (from tech_stack)
  const LANG_COLORS_HEX: Record<string, string> = {
    TypeScript: '#3178c6', JavaScript: '#f1e05a', Python: '#3572A5',
    Go: '#00ADD8', Rust: '#dea584', Java: '#b07219', CSS: '#563d7c',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-4"
    >
      {/* ── Row 1: Agent status cards ── */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          {
            icon: '🔍', name: 'RepoLens', border: 'border-blue-500/30', ring: 'ring-blue-500/20',
            metric: `${report.repo.file_count} files`, sub: agents.repo_lens.primary_language || agents.repo_lens.tech_stack[0] || 'Analyzed',
            score: sb.repo_score, scoreColor: 'text-blue-400',
          },
          {
            icon: '📋', name: 'PlanForge', border: 'border-purple-500/30', ring: 'ring-purple-500/20',
            metric: `${agents.plan_forge.milestones.length} tasks`, sub: agents.plan_forge.next_best_action.slice(0, 30) || 'Generated',
            score: sb.delivery_score, scoreColor: 'text-purple-400',
          },
          {
            icon: '🔒', name: 'GuardRail', border: 'border-amber-500/30', ring: 'ring-amber-500/20',
            metric: `${totalRisks} risks`, sub: `${riskCounts.critical} critical · ${riskCounts.high} high`,
            score: sb.security_score, scoreColor: 'text-amber-400',
          },
          {
            icon: '🧪', name: 'TestPilot', border: 'border-emerald-500/30', ring: 'ring-emerald-500/20',
            metric: `${agents.testpilot.suggested_tests.length} tests`, sub: `${agents.testpilot.existing_tests.coverage_estimate}% coverage`,
            score: sb.test_score, scoreColor: 'text-emerald-400',
          },
        ].map(a => (
          <div key={a.name} className={`glass-card border ${a.border} ring-1 ${a.ring} p-4`}>
            <div className="flex items-start justify-between mb-3">
              <span className="text-2xl">{a.icon}</span>
              <span className={`text-lg font-black ${a.scoreColor}`}>{a.score}</span>
            </div>
            <p className="text-xs font-bold text-slate-200 mb-0.5">{a.name}</p>
            <p className="text-base font-black text-white">{a.metric}</p>
            <p className="text-[10px] text-slate-500 mt-0.5 truncate">{a.sub}</p>
            <div className="mt-2.5">
              <Bar value={a.score} color={a.border.replace('border-', 'bg-').replace('/30', '/70')} />
            </div>
          </div>
        ))}
      </div>

      {/* ── Row 2: Score + AI Summary ── */}
      <div className="grid lg:grid-cols-5 gap-4">
        {/* Score card */}
        <div className="lg:col-span-2 glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <LayoutDashboard size={12} /> Readiness Score
            </p>
            <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${recStyle.bg} ${recStyle.border} ${recStyle.text} flex items-center gap-1.5`}>
              <span className={`w-1.5 h-1.5 rounded-full ${recStyle.dot}`} />
              {recStyle.label}
            </span>
          </div>
          <div className="flex items-end gap-2 mb-4">
            <span className="text-6xl font-black text-white">{report.readiness_score}</span>
            <span className="text-xl text-slate-500 mb-1">/100</span>
          </div>
          <div className="space-y-2.5">
            {[
              { label: 'Repo Structure', val: sb.repo_score,     w: '20%', bar: 'bg-blue-500' },
              { label: 'Delivery',       val: sb.delivery_score, w: '25%', bar: 'bg-purple-500' },
              { label: 'Security',       val: sb.security_score, w: '30%', bar: 'bg-amber-500' },
              { label: 'Tests',          val: sb.test_score,     w: '25%', bar: 'bg-emerald-500' },
            ].map((s, i) => (
              <div key={s.label}>
                <div className="flex justify-between text-[10px] mb-1">
                  <span className="text-slate-500">{s.label} ({s.w})</span>
                  <span className="font-bold text-slate-300">{s.val}</span>
                </div>
                <Bar value={s.val} color={s.bar} delay={i * 0.1} />
              </div>
            ))}
          </div>
        </div>

        {/* AI Summary */}
        <div className="lg:col-span-3 glass-card p-5">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-1.5">
            🤖 AI Summary
          </p>
          <p className="text-sm text-slate-300 leading-relaxed mb-4">
            {report.key_blockers.length > 0
              ? `Your repo has a readiness score of ${report.readiness_score}/100. ${recStyle.label === 'Ready to Ship' ? 'All key checks passed.' : `Main blockers: ${report.key_blockers.slice(0, 2).join(', ')}.`}`
              : `Your repository scored ${report.readiness_score}/100 and is ${recStyle.label.toLowerCase()}. Review the agent findings below.`
            }
          </p>
          {report.key_blockers.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {report.key_blockers.slice(0, 4).map((b, i) => (
                <span key={i} className="px-2 py-1 rounded-full text-[10px] font-semibold bg-red-500/10 border border-red-500/20 text-red-300">
                  {b.slice(0, 40)}
                </span>
              ))}
            </div>
          )}
          <div className="pt-3 border-t border-slate-700/40">
            <p className="text-[10px] text-slate-600 mb-2">Score formula</p>
            <p className="text-[10px] text-slate-500 font-mono">
              repo×20% + delivery×25% + security×30% + tests×25% = {report.readiness_score}
            </p>
          </div>
        </div>
      </div>

      {/* ── Row 3: Risk + Test Coverage + Repo Insights ── */}
      <div className="grid lg:grid-cols-3 gap-4">
        {/* Risk Breakdown */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Shield size={12} /> Risk Breakdown
            </p>
            <span className="text-xs text-slate-500">{totalRisks} total</span>
          </div>
          <div className="space-y-2.5">
            {([['critical', 'bg-red-500',    'text-red-400',    'Critical'],
               ['high',     'bg-orange-500', 'text-orange-400', 'High'   ],
               ['medium',   'bg-yellow-500', 'text-yellow-400', 'Medium' ],
               ['low',      'bg-blue-500',   'text-blue-400',   'Low'    ],
            ] as const).map(([sev, bar, text, label]) => (
              <div key={sev} className="flex items-center gap-3">
                <span className={`text-xs font-bold w-14 ${text}`}>{label}</span>
                <div className="flex-1 h-1.5 rounded-full bg-slate-700/50 overflow-hidden">
                  <motion.div
                    className={`h-full rounded-full ${bar}`}
                    initial={{ width: 0 }}
                    animate={{ width: totalRisks > 0 ? `${(riskCounts[sev] / totalRisks) * 100}%` : '0%' }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                  />
                </div>
                <span className="text-xs font-black text-slate-300 w-4 text-right">{riskCounts[sev]}</span>
              </div>
            ))}
          </div>
          {agents.guardrail.exposed_secrets.length > 0 && (
            <div className="mt-4 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2">
              <p className="text-xs text-red-300 flex items-center gap-1.5">
                <AlertTriangle size={11} />
                {agents.guardrail.exposed_secrets.length} exposed secret{agents.guardrail.exposed_secrets.length > 1 ? 's' : ''} detected
              </p>
            </div>
          )}
        </div>

        {/* Test Coverage */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <FlaskConical size={12} /> Test Coverage
            </p>
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${
              agents.testpilot.qa_readiness === 'ready'   ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' :
              agents.testpilot.qa_readiness === 'partial' ? 'bg-yellow-500/10  border-yellow-500/20  text-yellow-300' :
                                                            'bg-red-500/10     border-red-500/20     text-red-300'
            }`}>
              {agents.testpilot.qa_readiness === 'ready' ? 'QA Ready' : agents.testpilot.qa_readiness === 'partial' ? 'Partial' : 'Not Ready'}
            </span>
          </div>
          <div className="flex items-end gap-2 mb-3">
            <span className="text-4xl font-black text-white">{agents.testpilot.existing_tests.coverage_estimate}%</span>
            <span className="text-sm text-slate-500 mb-0.5">coverage</span>
          </div>
          <Bar
            value={agents.testpilot.existing_tests.coverage_estimate}
            color={agents.testpilot.existing_tests.coverage_estimate >= 70 ? 'bg-emerald-500' : agents.testpilot.existing_tests.coverage_estimate >= 40 ? 'bg-yellow-500' : 'bg-red-500'}
          />
          <p className="text-[10px] text-slate-500 mt-1.5">
            {agents.testpilot.existing_tests.count} test files · {agents.testpilot.existing_tests.frameworks.join(', ') || 'no framework'}
          </p>
          {agents.testpilot.missing_coverage_areas.length > 0 && (
            <div className="mt-3 space-y-1.5">
              <p className="text-[10px] text-slate-500 font-semibold">Missing coverage:</p>
              {agents.testpilot.missing_coverage_areas.slice(0, 3).map((area, i) => (
                <p key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                  <span className="text-orange-400 mt-0.5 flex-shrink-0">⚠</span>{area}
                </p>
              ))}
            </div>
          )}
        </div>

        {/* Repo Insights */}
        <div className="glass-card p-5">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Repository Insights</p>
          <div className="space-y-4">
            {agents.repo_lens.tech_stack.length > 0 && (
              <div>
                <p className="text-[10px] text-slate-500 mb-2">Tech Stack</p>
                <div className="flex flex-wrap gap-1.5">
                  {agents.repo_lens.tech_stack.slice(0, 6).map(t => (
                    <span key={t} className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800/80 border border-slate-700/50 text-slate-300 flex items-center gap-1">
                      {t in LANG_COLORS_HEX && (
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: LANG_COLORS_HEX[t] }} />
                      )}
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div>
              <p className="text-[10px] text-slate-500 mb-1.5">Architecture</p>
              <p className="text-xs text-slate-300 font-medium">{agents.repo_lens.architecture_pattern || 'Unknown'}</p>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {[
                  agents.repo_lens.has_ci_cd && 'CI/CD',
                  agents.repo_lens.has_dockerfile && 'Docker',
                  agents.repo_lens.has_tests && 'Tests',
                ].filter(Boolean).map(f => (
                  <span key={String(f)} className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                    ✓ {f}
                  </span>
                ))}
              </div>
            </div>
            {Object.keys(agents.repo_lens.dependency_summary).length > 0 && (
              <div>
                <p className="text-[10px] text-slate-500 mb-1.5">Key Dependencies</p>
                {Object.entries(agents.repo_lens.dependency_summary).slice(0, 2).map(([type, deps]) => (
                  <div key={type} className="mb-1.5">
                    <p className="text-[10px] text-slate-600 capitalize mb-1">{type}</p>
                    <div className="flex flex-wrap gap-1">
                      {(deps as string[]).slice(0, 4).map((d: string) => (
                        <span key={d} className="text-[10px] text-slate-400 font-mono bg-slate-800/60 border border-slate-700/40 rounded px-1.5 py-0.5">{d}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Row 4: Action Plan + Recent Activity ── */}
      <div className="grid lg:grid-cols-2 gap-4">
        {/* Action Plan */}
        <div className="glass-card p-5">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">⚡ Action Plan</p>
          <div className="space-y-2">
            {report.next_actions.slice(0, 5).map((action, i) => {
              const isBlocker = report.key_blockers.some(b => action.toLowerCase().includes(b.toLowerCase().slice(0, 15)));
              const priority = i === 0 || isBlocker ? 'critical' : i <= 2 ? 'medium' : 'low';
              return (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-slate-900/40 border border-slate-700/30">
                  <span className="text-xs font-black text-slate-500 flex-shrink-0 w-4 text-right mt-0.5">{i + 1}.</span>
                  <p className="text-xs text-slate-300 flex-1 leading-relaxed">{action}</p>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 ${
                    priority === 'critical' ? 'badge-critical' :
                    priority === 'medium'   ? 'badge-medium' :
                                             'badge-low'
                  }`}>
                    {priority}
                  </span>
                </div>
              );
            })}
            {report.next_actions.length === 0 && (
              <p className="text-xs text-slate-500 text-center py-4">No action items — great shape!</p>
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="glass-card p-5">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-1.5">
            <Clock size={12} /> Recent Activity
          </p>
          <div className="space-y-0">
            {[
              { icon: <CheckCircle2 size={12} className="text-emerald-400" />, text: 'Analysis pipeline complete', sub: fmt(report.generated_at), line: true },
              { icon: <span className="text-xs">🔍</span>, text: `RepoLens: ${report.repo.file_count} files analyzed`, sub: agents.repo_lens.architecture_pattern, line: true },
              { icon: <span className="text-xs">📋</span>, text: `PlanForge: ${agents.plan_forge.milestones.length} tasks generated`, sub: agents.plan_forge.estimated_effort, line: true },
              { icon: <span className="text-xs">🔒</span>, text: `GuardRail: ${totalRisks} risk${totalRisks !== 1 ? 's' : ''} found`, sub: `${riskCounts.critical} critical, ${riskCounts.high} high`, line: true },
              { icon: <span className="text-xs">🧪</span>, text: `TestPilot: ${agents.testpilot.suggested_tests.length} test${agents.testpilot.suggested_tests.length !== 1 ? 's' : ''} suggested`, sub: `${agents.testpilot.existing_tests.coverage_estimate}% current coverage`, line: false },
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="flex flex-col items-center flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-slate-800/80 border border-slate-700/40 flex items-center justify-center">
                    {item.icon}
                  </div>
                  {item.line && <div className="w-px h-4 bg-slate-700/40 my-0.5" />}
                </div>
                <div className="flex-1 pb-3 min-w-0">
                  <p className="text-xs text-slate-300 leading-snug">{item.text}</p>
                  {item.sub && <p className="text-[10px] text-slate-500 mt-0.5 truncate">{item.sub}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Report timestamp */}
      <p className="text-[10px] text-slate-700 text-center pb-2">
        Generated {fmt(report.generated_at)} · {report.repo.full_name} @ {report.repo.branch}
      </p>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Error state
// ─────────────────────────────────────────────────────────────────────────────

function ErrorState({ error, onReset }: { error: string; onReset: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="glass-card border border-red-500/30 bg-red-950/20 p-6"
    >
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle size={16} className="text-red-400" />
        <p className="text-sm font-bold text-red-300">Analysis failed</p>
      </div>
      <p className="text-xs text-slate-400 mb-4">{error}</p>
      <button
        onClick={onReset}
        className="px-4 py-2 rounded-lg bg-slate-700/40 border border-slate-600/40 text-xs text-slate-300 hover:bg-slate-700/60 transition-colors"
      >
        Try Again
      </button>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DashboardShell — top-level export
// ─────────────────────────────────────────────────────────────────────────────

interface DashboardShellProps {
  appState: AppState;
  selectedRepo: GitHubRepo | null;
  selectedBranch: string;
  selectedPull: GitHubPR | null;
  agents: AgentProgress[];
  report: ShipMateReport | null;
  error: string | null;
  onAnalyze: () => void;
  onReset: () => void;
}

export function DashboardShell({
  appState, selectedRepo, selectedBranch, selectedPull,
  agents, report, error, onAnalyze, onReset,
}: DashboardShellProps) {
  return (
    <div className="space-y-4">
      {/* Repo header bar */}
      {selectedRepo && (
        <DashboardHeader
          repo={selectedRepo}
          branch={selectedBranch}
          pull={selectedPull}
          generatedAt={report?.generated_at}
        />
      )}

      {/* State-based content */}
      {appState === 'connected' && !selectedRepo && <NoRepoState />}
      {appState === 'connected' && selectedRepo && !report && <ReadyToAnalyzeState repo={selectedRepo} onAnalyze={onAnalyze} />}
      {appState === 'analyzing' && <AnalyzingState agents={agents} />}
      {appState === 'error' && error && <ErrorState error={error} onReset={onReset} />}
      {appState === 'complete' && report && <ResultsDashboard report={report} />}
    </div>
  );
}
