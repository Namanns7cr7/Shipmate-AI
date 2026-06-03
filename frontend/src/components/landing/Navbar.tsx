import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Wordmark } from '../ui/LogoMark';
import { GitHubConnectButton } from '../ui/GitHubConnectButton';

interface NavbarProps { onLogin: () => void; loading?: boolean; }

const NAV_LINKS = ['Product', 'Agents', 'Why ShipMate', 'Pricing'];

export function Navbar({ onLogin, loading }: NavbarProps) {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 50, height: 68,
        transition: 'all .3s ease',
        background: scrolled ? 'rgba(7,12,24,0.82)' : 'transparent',
        backdropFilter: scrolled ? 'blur(16px)' : 'none',
        borderBottom: scrolled ? '1px solid var(--line)' : '1px solid transparent',
      }}
    >
      <div style={{ maxWidth: 1200, margin: '0 auto', height: '100%', padding: '0 28px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}>
        <Wordmark size={18} markSize={34} />

        {/* Desktop nav — centered */}
        <nav style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 4 }}
          className="hidden md:flex">
          {NAV_LINKS.map(l => (
            <button key={l} style={{ padding: '8px 13px', borderRadius: 9, fontSize: 13.5, fontWeight: 550, color: 'var(--ink-3)', background: 'none', border: 'none', cursor: 'pointer', transition: 'color .15s' }}
              onMouseEnter={e => (e.currentTarget.style.color = '#fff')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--ink-3)')}>
              {l}
            </button>
          ))}
        </nav>

        {/* Right CTA */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button className="btn btn-secondary btn-sm hidden md:inline-flex" onClick={onLogin}>Sign in</button>
          <div className="hidden md:block">
            <GitHubConnectButton onClick={onLogin} label="Connect GitHub" variant="light" size="sm" loading={loading} />
          </div>
          {/* Mobile hamburger */}
          <button className="md:hidden" style={{ padding: 8, borderRadius: 8, background: 'none', border: 'none', color: 'var(--ink-3)', cursor: 'pointer' }}
            onClick={() => setMenuOpen(v => !v)} aria-label="Toggle menu">
            <div style={{ width: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ height: 2, background: 'currentColor', borderRadius: 1 }} />
              <div style={{ height: 2, background: 'currentColor', borderRadius: 1 }} />
              <div style={{ height: 2, background: 'currentColor', borderRadius: 1 }} />
            </div>
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {menuOpen && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          style={{ background: 'rgba(7,12,24,0.95)', backdropFilter: 'blur(16px)', borderTop: '1px solid var(--line)', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {NAV_LINKS.map(l => (
            <button key={l} onClick={() => setMenuOpen(false)}
              style={{ width: '100%', textAlign: 'left', padding: '10px 16px', borderRadius: 8, fontSize: 14, color: 'var(--ink-2)', background: 'none', border: 'none', cursor: 'pointer' }}>
              {l}
            </button>
          ))}
          <div style={{ marginTop: 8 }}>
            <GitHubConnectButton onClick={() => { setMenuOpen(false); onLogin(); }} label="Connect GitHub" size="lg" loading={loading} />
          </div>
        </motion.div>
      )}
    </motion.header>
  );
}
