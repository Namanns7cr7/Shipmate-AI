import { motion } from 'framer-motion';
import { useEffect, useRef } from 'react';

interface HeroProps { onLogin: () => void; loading?: boolean; error?: string | null; }

function ScoreArc({ score }: { score: number }) {
  const r = 40;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <svg viewBox="0 0 100 100" className="w-20 h-20 -rotate-90">
      <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(99,179,237,0.1)" strokeWidth="8" />
      <motion.circle
        cx="50" cy="50" r={r} fill="none"
        stroke="url(#heroGrad)" strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={circ}
        initial={{ strokeDashoffset: circ }}
        animate={{ strokeDashoffset: circ - dash }}
        transition={{ duration: 1.4, delay: 0.6, ease: 'easeOut' }}
      />
      <defs>
        <linearGradient id="heroGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function StatRow({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-slate-800/50 border border-slate-700/40">
      <span className="text-xs text-slate-400">{label}</span>
      <span className={`text-sm font-bold ${color}`}>{value}</span>
    </div>
  );
}

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  );
}

export function Hero({ onLogin, loading, error }: HeroProps) {
  const blobRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let frame: number;
    let t = 0;
    const animate = () => {
      t += 0.003;
      if (blobRef.current) {
        blobRef.current.style.transform = `translate(${Math.sin(t) * 20}px, ${Math.cos(t * 0.7) * 15}px)`;
      }
      frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <section className="relative min-h-screen grid-bg pt-20 overflow-hidden flex items-center">
      {/* Animated background blobs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div ref={blobRef} className="absolute top-1/4 -left-32 w-96 h-96 bg-blue-600/8 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-32 w-80 h-80 bg-purple-600/8 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-cyan-600/4 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-[1180px] mx-auto px-6 py-20">
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_420px] gap-14 items-center">

          {/* LEFT COLUMN */}
          <div>
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45 }}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-6"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              AI-native release intelligence
            </motion.div>

            {/* H1 */}
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="text-[2.5rem] sm:text-[3rem] lg:text-[3.5rem] font-black leading-[1.08] tracking-tight mb-6"
            >
              Ship production-ready code{' '}
              <span className="neon-text">with AI agents</span>
            </motion.h1>

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="text-base sm:text-lg text-slate-400 leading-relaxed mb-8 max-w-lg"
            >
              Connect your GitHub repo and get a live release readiness score. 4 specialized agents
              analyze architecture, security posture, test coverage, and delivery plan — in seconds.
            </motion.p>

            {/* CTA Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-col sm:flex-row gap-3 mb-8"
            >
              <button
                onClick={onLogin}
                disabled={loading}
                className="btn-primary inline-flex items-center justify-center gap-2.5 px-6 py-3.5 text-sm font-bold rounded-xl disabled:opacity-60"
              >
                <GitHubIcon className="w-5 h-5 relative z-10" />
                <span className="relative z-10">{loading ? 'Connecting…' : 'Connect GitHub'}</span>
              </button>
              <button
                onClick={() => document.querySelector('#dashboard')?.scrollIntoView({ behavior: 'smooth' })}
                className="btn-secondary inline-flex items-center justify-center gap-2 px-6 py-3.5 text-sm font-semibold rounded-xl"
              >
                View Demo Flow
                <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                  <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </motion.div>

            {/* Error */}
            {error && (
              <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-4 text-sm text-red-400">
                {error}
              </motion.p>
            )}

            {/* Trust badges */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
              className="flex flex-wrap items-center gap-5 text-xs text-slate-500"
            >
              <span className="flex items-center gap-1.5"><span className="text-green-400">✓</span> No zip upload</span>
              <span className="flex items-center gap-1.5"><span className="text-green-400">✓</span> Private repos</span>
              <span className="flex items-center gap-1.5"><span className="text-green-400">✓</span> Read-only access</span>
              <span className="flex items-center gap-1.5"><span className="text-green-400">✓</span> Free during beta</span>
            </motion.div>
          </div>

          {/* RIGHT COLUMN — mock dashboard card */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="relative"
          >
            <div className="gradient-border">
              <div className="glass-card p-5 space-y-3">

                {/* Header row */}
                <div className="flex items-center justify-between">
                  <p className="text-xs text-slate-400 font-mono">shipmate-ai / frontend</p>
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-yellow-500/15 border border-yellow-500/30 text-yellow-300">
                    Mostly Ready
                  </span>
                </div>

                {/* Score ring + stat rows */}
                <div className="flex items-center gap-4 p-3 rounded-xl bg-slate-900/60 border border-slate-700/30">
                  {/* SVG ring */}
                  <div className="relative flex-shrink-0">
                    <ScoreArc score={87} />
                    <div className="absolute inset-0 flex items-center justify-center rotate-90">
                      <div className="text-center">
                        <div className="text-xl font-black text-white leading-none">87</div>
                        <div className="text-[10px] text-slate-500">/100</div>
                      </div>
                    </div>
                  </div>
                  {/* 3 stat rows */}
                  <div className="flex-1 space-y-2 min-w-0">
                    <StatRow label="Release Readiness" value="87 / 100" color="text-blue-400" />
                    <StatRow label="Security Risk"     value="Medium"   color="text-yellow-400" />
                    <StatRow label="Test Coverage"     value="72%"      color="text-emerald-400" />
                  </div>
                </div>

                {/* 2x2 agent mini cards */}
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { icon: '🔍', label: 'RepoLens',  val: 'Mapped',   color: 'text-blue-400' },
                    { icon: '📋', label: 'PlanForge', val: '9 tasks',  color: 'text-purple-400' },
                    { icon: '🔒', label: 'GuardRail', val: '3 risks',  color: 'text-yellow-400' },
                    { icon: '🧪', label: 'TestPilot', val: '12 tests', color: 'text-emerald-400' },
                  ].map(a => (
                    <div key={a.label} className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/30">
                      <span className="text-base leading-none">{a.icon}</span>
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-slate-300">{a.label}</p>
                        <p className={`text-xs ${a.color}`}>{a.val}</p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Footer */}
                <p className="text-xs text-slate-500 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse flex-shrink-0" />
                  Open Issues <span className="text-white font-semibold">14</span>
                  <span className="mx-1">·</span>
                  Suggested Tasks <span className="text-white font-semibold">9</span>
                </p>

              </div>
            </div>
            {/* Glow halo */}
            <div className="absolute -inset-4 bg-blue-600/5 rounded-2xl blur-2xl -z-10" />
          </motion.div>

        </div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.4 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 text-slate-600 text-xs"
      >
        Scroll to explore
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="w-0.5 h-6 bg-gradient-to-b from-slate-600 to-transparent rounded-full mt-1"
        />
      </motion.div>
    </section>
  );
}
