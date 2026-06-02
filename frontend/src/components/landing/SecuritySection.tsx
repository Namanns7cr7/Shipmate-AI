import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';

interface TrustPoint {
  icon: string;
  title: string;
  desc: string;
  color: string;
  bg: string;
}

const POINTS: TrustPoint[] = [
  {
    icon: '🔑',
    title: 'GitHub OAuth only',
    desc: 'Auth via GitHub. No passwords stored.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
  },
  {
    icon: '📎',
    title: 'No zip upload',
    desc: 'Reads directly from GitHub API.',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
  },
  {
    icon: '🔐',
    title: 'Private repos',
    desc: 'OAuth scope covers private repos per session.',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
  },
  {
    icon: '👁',
    title: 'Read-only analysis',
    desc: 'Never writes to your repo or opens PRs.',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
  },
  {
    icon: '🛡',
    title: 'Prompt-injection aware',
    desc: 'Agent inputs sanitized against README attacks.',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
  },
  {
    icon: '📋',
    title: 'Audit logs',
    desc: 'Every agent action timestamped for compliance.',
    color: 'text-rose-400',
    bg: 'bg-rose-500/10',
  },
];

export function SecuritySection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <section id="security" className="bg-slate-900/40 border-y border-slate-800/40">
      <div className="max-w-[1180px] mx-auto px-6 py-24">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-14"
        >
          <p className="text-emerald-400 text-xs font-semibold uppercase tracking-widest mb-3">
            Security &amp; Trust
          </p>
          <h2 className="text-3xl sm:text-4xl font-black text-white mb-4">
            Built for{' '}
            <span className="neon-green">enterprise trust</span>
          </h2>
          <p className="text-slate-400 max-w-md mx-auto text-sm">
            Your code stays on GitHub. ShipMate AI reads only what it needs, scoped to your session.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {POINTS.map((point, i) => (
            <motion.div
              key={point.title}
              initial={{ opacity: 0, y: 30 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              whileHover={{ y: -3 }}
              className="glass-card p-4 flex items-start gap-3 transition-all duration-200"
            >
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl flex-shrink-0 ${point.bg}`}
              >
                {point.icon}
              </div>
              <div>
                <p className={`font-semibold text-sm mb-0.5 ${point.color}`}>{point.title}</p>
                <p className="text-xs text-slate-400 leading-relaxed">{point.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
