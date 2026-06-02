import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';

interface CTASectionProps { onLogin: () => void; loading?: boolean; }

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  );
}

export function CTASection({ onLogin, loading }: CTASectionProps) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <section id="cta" className="py-24">
      <div className="max-w-[1180px] mx-auto px-6">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 32 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.55, ease: 'easeOut' }}
          className="rounded-3xl border border-slate-700/40 bg-gradient-to-br from-slate-900 to-slate-900/60 p-16 text-center relative overflow-hidden"
        >
          {/* Radial glow blobs inside the card */}
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute top-1/2 left-1/4 -translate-y-1/2 -translate-x-1/2 w-80 h-80 bg-blue-600/15 rounded-full blur-3xl" />
            <div className="absolute top-1/2 right-1/4 -translate-y-1/2 translate-x-1/2 w-80 h-80 bg-purple-600/15 rounded-full blur-3xl" />
          </div>

          {/* Content */}
          <div className="relative z-10 flex flex-col items-center">
            <div className="text-5xl mb-4">🚢</div>

            <h2 className="text-3xl sm:text-4xl font-black text-white mb-4 leading-tight">
              Ready to analyze your repo?
            </h2>

            <p className="text-slate-400 mb-8 max-w-lg mx-auto leading-relaxed">
              Connect GitHub and let ShipMate AI prepare your next release.
            </p>

            <motion.button
              onClick={onLogin}
              disabled={loading}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.97 }}
              className="btn-primary inline-flex items-center gap-3 px-8 py-4 text-base font-bold rounded-2xl disabled:opacity-60"
            >
              <GitHubIcon className="w-5 h-5 relative z-10" />
              <span className="relative z-10">{loading ? 'Connecting…' : 'Connect GitHub'}</span>
            </motion.button>

            <p className="mt-4 text-xs text-slate-500">
              Free during beta&nbsp; •&nbsp; No credit card&nbsp; •&nbsp; Private repos supported
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
