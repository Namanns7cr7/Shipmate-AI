import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';

const STEPS = [
  {
    icon: '📁',
    title: 'GitHub Repo',
    desc: 'OAuth connect — no zip, no upload required',
    color: 'border-blue-500/30 bg-blue-500/5',
    chip: 'bg-blue-500/20 text-blue-300',
    accent: 'text-blue-400',
  },
  {
    icon: '🤖',
    title: 'AI Agent Analysis',
    desc: '4 agents run concurrently on your live repo',
    color: 'border-purple-500/30 bg-purple-500/5',
    chip: 'bg-purple-500/20 text-purple-300',
    accent: 'text-purple-400',
  },
  {
    icon: '🛡',
    title: 'Risk + Test Review',
    desc: 'Security ranked and coverage measured',
    color: 'border-amber-500/30 bg-amber-500/5',
    chip: 'bg-amber-500/20 text-amber-300',
    accent: 'text-amber-400',
  },
  {
    icon: '📊',
    title: 'Readiness Score',
    desc: 'Deterministic 0–100 composite score',
    color: 'border-cyan-500/30 bg-cyan-500/5',
    chip: 'bg-cyan-500/20 text-cyan-300',
    accent: 'text-cyan-400',
  },
  {
    icon: '⚡',
    title: 'Action Plan',
    desc: 'Prioritized blockers and next steps',
    color: 'border-emerald-500/30 bg-emerald-500/5',
    chip: 'bg-emerald-500/20 text-emerald-300',
    accent: 'text-emerald-400',
  },
];

export function WorkflowSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <section id="workflow" className="bg-slate-900/30 border-y border-slate-800/40">
      <div className="max-w-[1180px] mx-auto px-6 py-24">
        {/* Header */}
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-14"
        >
          <p className="text-purple-400 text-xs font-semibold uppercase tracking-widest mb-3">
            How It Works
          </p>
          <h2 className="text-3xl sm:text-4xl font-black text-white mb-4">
            From commit to{' '}
            <span className="neon-text">ship-ready</span>
          </h2>
          <p className="text-slate-400 max-w-lg mx-auto text-sm leading-relaxed">
            A fully automated pipeline that runs against your live GitHub repo — no configuration, no waiting.
          </p>
        </motion.div>

        {/* Desktop: horizontal flex row with arrow connectors */}
        <div className="hidden md:flex items-stretch">
          {STEPS.map((step, i) => (
            <div key={step.title} className="flex items-center flex-1 min-w-0">
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.4, delay: i * 0.12 }}
                className={`flex-1 rounded-2xl border p-4 text-center flex flex-col items-center gap-2 ${step.color}`}
              >
                {/* Icon */}
                <span className="text-2xl leading-none">{step.icon}</span>

                {/* Step number chip */}
                <span
                  className={`inline-flex items-center justify-center rounded-full text-[10px] font-bold px-2 py-0.5 ${step.chip}`}
                >
                  Step {i + 1}
                </span>

                {/* Title */}
                <p className="text-sm font-bold text-white leading-tight">{step.title}</p>

                {/* Description */}
                <p className={`text-xs leading-snug ${step.accent}`}>{step.desc}</p>
              </motion.div>

              {/* Arrow connector between cards */}
              {i < STEPS.length - 1 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={inView ? { opacity: 1 } : {}}
                  transition={{ delay: i * 0.12 + 0.2 }}
                  className="flex-shrink-0 flex items-center justify-center px-1"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    className="w-5 h-5 text-slate-600"
                    aria-hidden="true"
                  >
                    <path
                      d="M9 18l6-6-6-6"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </motion.div>
              )}
            </div>
          ))}
        </div>

        {/* Mobile: vertical list with left-side step number */}
        <div className="md:hidden space-y-3">
          {STEPS.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, x: -20 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.4, delay: i * 0.1 }}
              className={`flex items-start gap-4 rounded-2xl border p-4 ${step.color}`}
            >
              {/* Left-side step number */}
              <div className="flex flex-col items-center gap-1.5 flex-shrink-0">
                <span
                  className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${step.chip}`}
                >
                  {i + 1}
                </span>
                {i < STEPS.length - 1 && (
                  <div className="w-px h-4 bg-slate-700/60" />
                )}
              </div>

              {/* Icon + content */}
              <div className="flex items-start gap-3 flex-1 min-w-0">
                <span className="text-2xl leading-none flex-shrink-0">{step.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-white leading-tight">{step.title}</p>
                  <p className={`text-xs mt-0.5 leading-snug ${step.accent}`}>{step.desc}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
