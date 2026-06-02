import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const NAV_LINKS = [
  { label: 'Agents',    href: '#agents' },
  { label: 'Workflow',  href: '#workflow' },
  { label: 'Dashboard', href: '#dashboard' },
  { label: 'Security',  href: '#security' },
];

interface NavbarProps { onLogin: () => void; loading?: boolean; }

export function Navbar({ onLogin, loading }: NavbarProps) {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const scrollTo = (href: string) => {
    setMenuOpen(false);
    document.querySelector(href)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <motion.nav
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className={`fixed top-0 left-0 right-0 z-50 h-16 transition-all duration-300 ${
        scrolled
          ? 'bg-slate-950/90 backdrop-blur-lg border-b border-slate-800/60 shadow-lg shadow-black/20'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-[1180px] mx-auto px-6 h-full grid grid-cols-3 items-center">
        {/* Left col: Logo */}
        <div className="flex items-center gap-2.5">
          <span className="text-2xl">🚢</span>
          <span className="font-black text-white tracking-tight">ShipMate</span>
          <span className="font-black text-blue-400 tracking-tight">AI</span>
          <span className="ml-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400">
            Beta
          </span>
        </div>

        {/* Center col: Nav links (desktop) */}
        <div className="hidden md:flex items-center justify-center gap-1">
          {NAV_LINKS.map(l => (
            <button
              key={l.href}
              onClick={() => scrollTo(l.href)}
              className="px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors rounded-lg hover:bg-slate-800/50"
            >
              {l.label}
            </button>
          ))}
        </div>

        {/* Right col: Connect GitHub (desktop) + Hamburger (mobile) */}
        <div className="flex items-center justify-end">
          <button
            onClick={onLogin}
            disabled={loading}
            className="hidden md:flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-slate-900 font-bold text-sm hover:bg-slate-100 transition-all shadow-lg shadow-black/20 disabled:opacity-60"
          >
            <GitHubIcon className="w-4 h-4" />
            {loading ? 'Connecting…' : 'Connect GitHub'}
          </button>

          <button
            className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors"
            onClick={() => setMenuOpen(v => !v)}
            aria-label="Toggle menu"
          >
            <div className="w-5 space-y-1">
              <div className="h-0.5 bg-current" />
              <div className="h-0.5 bg-current" />
              <div className="h-0.5 bg-current" />
            </div>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="md:hidden bg-slate-950/95 backdrop-blur-lg border-t border-slate-800/60 px-4 py-4 space-y-1"
        >
          {NAV_LINKS.map(l => (
            <button
              key={l.href}
              onClick={() => scrollTo(l.href)}
              className="block w-full text-left px-4 py-2.5 text-sm text-slate-300 hover:text-white hover:bg-slate-800/50 rounded-lg transition-colors"
            >
              {l.label}
            </button>
          ))}
          <button
            onClick={() => { setMenuOpen(false); onLogin(); }}
            disabled={loading}
            className="w-full mt-2 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-white text-slate-900 font-bold text-sm disabled:opacity-60"
          >
            <GitHubIcon className="w-4 h-4" />
            {loading ? 'Connecting…' : 'Connect GitHub'}
          </button>
        </motion.div>
      )}
    </motion.nav>
  );
}

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  );
}
