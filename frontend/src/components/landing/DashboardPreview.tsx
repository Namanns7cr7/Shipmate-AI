import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';

function AnimatedBar({ value, color, delay = 0 }: { value: number; color: string; delay?: number }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  return (
    <div ref={ref} className="h-1.5 rounded-full bg-slate-700/60 overflow-hidden">
      <motion.div
        className={`h-full rounded-full ${color}`}
        initial={{ width: 0 }}
        animate={inView ? { width: `${value}%` } : {}}
        transition={{ duration: 1, ease: 'easeOut', delay: delay + 0.3 }}
      />
    </div>
  );
}

const BREAKDOWN = [
  { label: 'Repo Structure', val: 82, weight: 20, bar: 'bg-blue-500' },
  { label: 'Delivery Plan',  val: 91, weight: 25, bar: 'bg-purple-500' },
  { label: 'Security',       val: 74, weight: 30, bar: 'bg-amber-500' },
  { label: 'Test Coverage',  val: 72, weight: 25, bar: 'bg-emerald-500' },
];

const AGENT_RESULTS = [
  {
    icon: '🔍', name: 'RepoLens',  status: 'Completed',
    detail: 'React + TypeScript · Vite · Tailwind CSS',
    color: 'text-blue-400', bg: 'bg-blue-500/5 border-blue-500/20',
  },
  {
    icon: '📋', name: 'PlanForge', status: 'Generated 9 tasks',
    detail: '3 blockers · 6 recommended · Sprint-ready',
    color: 'text-purple-400', bg: 'bg-purple-500/5 border-purple-500/20',
  },
  {
    icon: '🔒', name: 'GuardRail', status: 'Found 3 risks',
    detail: '1 high · 1 medium · 1 low severity',
    color: 'text-amber-400', bg: 'bg-amber-500/5 border-amber-500/20',
  },
  {
    icon: '🧪', name: 'TestPilot', status: 'Suggested 12 tests',
    detail: 'Coverage ~72% · Missing: auth, API routes',
    color: 'text-emerald-400', bg: 'bg-emerald-500/5 border-emerald-500/20',
  },
];

export function DashboardPreview() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="dashboard">
      <div className="max-w-[1180px] mx-auto px-6 py-24">
        {/* Header */}
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-14"
        >
          <p className="text-cyan-400 text-sm font-semibold uppercase tracking-widest mb-3">
            Live Dashboard
          </p>
          <h2 className="text-3xl sm:text-4xl font-black text-white mb-4">
            Everything in{' '}
            <span className="neon-text">one structured report</span>
          </h2>
          <p className="text-slate-400 max-w-lg mx-auto">
            A report from all 4 agents — scored, ranked, and ready for your next standup or release meeting.
          </p>
        </motion.div>

        {/* Main preview card */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="relative max-w-3xl mx-auto"
        >
          <div className="gradient-border">
            <div className="glass-card p-6 sm:p-8">
              {/* Repo header */}
              <div className="flex flex-wrap items-center justify-between gap-3 pb-5 mb-5 border-b border-slate-700/40">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-lg">
                    🚢
                  </div>
                  <div>
                    <p className="text-sm font-bold text-white">shipmate-ai / frontend</p>
                    <p className="text-xs text-slate-500 font-mono">Branch: main · 4 agents complete</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs font-semibold text-emerald-400">Analysis complete</span>
                </div>
              </div>

              {/* Content grid */}
              <div className="grid md:grid-cols-5 gap-5">
                {/* Left: Score card + progress bars */}
                <div className="md:col-span-2 space-y-4">
                  <div className="rounded-xl bg-slate-900/60 border border-slate-700/30 p-5 text-center">
                    <div className="text-5xl font-black text-white mb-0.5">87</div>
                    <div className="text-xs text-slate-500 mb-3">Readiness Score / 100</div>
                    <span className="px-3 py-1.5 rounded-full text-xs font-bold bg-yellow-500/15 border border-yellow-500/30 text-yellow-300">
                      Mostly Ready
                    </span>
                  </div>

                  <div className="space-y-3.5">
                    {BREAKDOWN.map((s, i) => (
                      <div key={s.label}>
                        <div className="flex justify-between text-xs mb-1.5">
                          <span className="text-slate-400">{s.label} ({s.weight}%)</span>
                          <span className="font-bold text-slate-200">{s.val}</span>
                        </div>
                        <AnimatedBar value={s.val} color={s.bar} delay={i * 0.1} />
                      </div>
                    ))}
                    <p className="text-xs text-slate-600 mt-2">
                      Formula: repo×20% + delivery×25% + security×30% + tests×25%
                    </p>
                  </div>
                </div>

                {/* Right: Agent result rows + AI summary */}
                <div className="md:col-span-3 space-y-3">
                  {AGENT_RESULTS.map((a, i) => (
                    <motion.div
                      key={a.name}
                      initial={{ opacity: 0, x: 20 }}
                      animate={inView ? { opacity: 1, x: 0 } : {}}
                      transition={{ duration: 0.4, delay: 0.3 + i * 0.08 }}
                      className={`rounded-xl border p-4 ${a.bg} flex items-start gap-3`}
                    >
                      <span className="text-xl flex-shrink-0 mt-0.5">{a.icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <span className="font-bold text-sm text-white">{a.name}</span>
                          <span className={`text-xs font-semibold ${a.color}`}>{a.status}</span>
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">{a.detail}</p>
                      </div>
                      <span className="text-emerald-400 flex-shrink-0 text-sm">✓</span>
                    </motion.div>
                  ))}

                  {/* AI Summary */}
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={inView ? { opacity: 1, y: 0 } : {}}
                    transition={{ duration: 0.4, delay: 0.65 }}
                    className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span>🤖</span>
                      <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">AI Summary</span>
                    </div>
                    <p className="text-sm text-slate-300 leading-relaxed">
                      Your repo is close to release. Main blockers are{' '}
                      <span className="text-amber-300 font-medium">missing integration tests</span>,{' '}
                      <span className="text-red-300 font-medium">exposed environment config</span>, and{' '}
                      <span className="text-yellow-300 font-medium">incomplete GitHub OAuth error handling</span>.
                    </p>
                  </motion.div>
                </div>
              </div>
            </div>
          </div>

          {/* Glow underneath card */}
          <div className="absolute -inset-6 bg-blue-600/5 rounded-3xl blur-3xl -z-10" />
        </motion.div>
      </div>
    </section>
  );
}
