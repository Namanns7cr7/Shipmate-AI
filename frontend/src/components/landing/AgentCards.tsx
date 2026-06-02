import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';

const AGENTS = [
  {
    icon: '🔍',
    name: 'RepoLens',
    tagline: 'Repo Intelligence',
    from: 'from-blue-600/20',
    to: 'to-blue-900/10',
    border: 'border-blue-500/20 hover:border-blue-400/50',
    glow: 'hover:shadow-blue-500/10',
    accent: 'text-blue-400',
    badge: 'bg-blue-500/10 border-blue-500/20 text-blue-300',
    tagBorder: 'border-blue-500/30 text-blue-300',
    description:
      'Maps repo structure, dependencies, tech stack, architecture patterns, and code ownership. Identifies complexity hotspots and critical entry points.',
    features: ['Tech stack', 'Dependency graph', 'Code ownership'],
  },
  {
    icon: '📋',
    name: 'PlanForge',
    tagline: 'Delivery Planning',
    from: 'from-purple-600/20',
    to: 'to-purple-900/10',
    border: 'border-purple-500/20 hover:border-purple-400/50',
    glow: 'hover:shadow-purple-500/10',
    accent: 'text-purple-400',
    badge: 'bg-purple-500/10 border-purple-500/20 text-purple-300',
    tagBorder: 'border-purple-500/30 text-purple-300',
    description:
      'Turns GitHub issues and feature requests into sprint-ready engineering tasks. Generates milestones, priorities, and estimated delivery timelines.',
    features: ['Sprint milestones', 'Task prioritization', 'Timeline estimates'],
  },
  {
    icon: '🔒',
    name: 'GuardRail',
    tagline: 'Security Audit',
    from: 'from-amber-600/20',
    to: 'to-amber-900/10',
    border: 'border-amber-500/20 hover:border-amber-400/50',
    glow: 'hover:shadow-amber-500/10',
    accent: 'text-amber-400',
    badge: 'bg-amber-500/10 border-amber-500/20 text-amber-300',
    tagBorder: 'border-amber-500/30 text-amber-300',
    description:
      'Finds exposed secrets, risky dependencies, auth issues, CORS misconfigs, and deployment blockers — severity ranked so you fix the right things first.',
    features: ['Secret scanning', 'Dependency CVEs', 'Auth risk analysis'],
  },
  {
    icon: '🧪',
    name: 'TestPilot',
    tagline: 'QA Intelligence',
    from: 'from-emerald-600/20',
    to: 'to-emerald-900/10',
    border: 'border-emerald-500/20 hover:border-emerald-400/50',
    glow: 'hover:shadow-emerald-500/10',
    accent: 'text-emerald-400',
    badge: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300',
    tagBorder: 'border-emerald-500/30 text-emerald-300',
    description:
      'Reviews test coverage, detects untested critical paths, generates actionable test plans, and suggests CI/CD quality gates to prevent regressions.',
    features: ['Coverage analysis', 'Test gap detection', 'CI/CD gates'],
  },
];

function AgentCard({ agent, index }: { agent: typeof AGENTS[0]; index: number }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      whileHover={{ y: -4, scale: 1.01 }}
      className={`
        rounded-2xl
        bg-gradient-to-br ${agent.from} ${agent.to}
        border ${agent.border}
        backdrop-blur-md
        ${agent.glow} hover:shadow-xl
        p-6 flex flex-col gap-4
        cursor-default transition-shadow duration-300
      `}
    >
      {/* Top row: icon + name + tagline badge */}
      <div className="flex items-start gap-3">
        <span className="text-3xl leading-none mt-0.5">{agent.icon}</span>
        <div className="flex flex-col gap-1">
          <h3 className="text-lg font-black text-white leading-tight">{agent.name}</h3>
          <span
            className={`inline-block self-start text-xs font-semibold px-2 py-0.5 rounded-full border ${agent.badge}`}
          >
            {agent.tagline}
          </span>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-slate-400 leading-relaxed flex-1">{agent.description}</p>

      {/* Feature pill tags */}
      <div className="flex flex-wrap gap-1.5">
        {agent.features.map((f) => (
          <span
            key={f}
            className={`px-2 py-0.5 rounded-full border text-xs font-medium ${agent.tagBorder}`}
          >
            {f}
          </span>
        ))}
      </div>
    </motion.div>
  );
}

export function AgentCards() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <section id="agents">
      <div className="max-w-[1180px] mx-auto px-6 py-24">
        {/* Section header */}
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-14"
        >
          <p className="text-blue-400 text-sm font-semibold uppercase tracking-widest mb-3">
            4 Specialized Agents
          </p>
          <h2 className="text-3xl sm:text-4xl font-black text-white mb-4">
            Your AI engineering{' '}
            <span className="neon-text">command center</span>
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto">
            Each agent runs a focused analysis pass. Together they give you complete release
            intelligence — architecture, security, tests, and delivery — in one structured report.
          </p>
        </motion.div>

        {/* Cards grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {AGENTS.map((a, i) => (
            <AgentCard key={a.name} agent={a} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
