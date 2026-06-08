import { Lock } from 'lucide-react';
import { LogoMark, Wordmark } from '../ui/LogoMark';
import { GitHubConnectButton } from '../ui/GitHubConnectButton';
import { RadarBg } from '../ui/RadarBg';
import { Reveal } from '../ui/Reveal';

interface CTASectionProps { onLogin: () => void; loading?: boolean; }

export function CTASection({ onLogin, loading }: CTASectionProps) {
  return (
    <section style={{ position: 'relative', padding: '0 28px 90px' }}>
      <div style={{ maxWidth: 1000, margin: '0 auto' }}>
        <Reveal>
          <div className="card glow-border" style={{ position: 'relative', overflow: 'hidden', padding: '60px 40px', textAlign: 'center' }}>
            <RadarBg sweep rings blobs={false} style={{ opacity: 0.6 }} />
            <div style={{ position: 'relative' }}>
              <div style={{ margin: '0 auto 22px', display: 'flex', justifyContent: 'center' }}>
                <LogoMark size={52} />
              </div>
              <h2 style={{ fontSize: 40, fontWeight: 840, letterSpacing: '-0.035em', margin: '0 0 14px', lineHeight: 1.08 }}>
                Connect GitHub.<br />Score it, then fix it.
              </h2>
              <p className="muted" style={{ fontSize: 16.5, maxWidth: 480, margin: '0 auto 30px', lineHeight: 1.6 }}>
                Point ShipMate at a repository and watch the crew work — every fix lands as a
                reviewable pull request you approve. Revocable, and free to try.
              </p>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
                <GitHubConnectButton onClick={onLogin} label="Connect GitHub" variant="light" size="lg" loading={loading} />
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--ink-3)' }}>
                  <Lock size={14} /> Token stays server-side · you approve every PR
                </span>
              </div>
            </div>
          </div>
        </Reveal>
      </div>

      <footer style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap',
        maxWidth: 1160, margin: '60px auto 0', padding: '28px 28px 0',
        borderTop: '1px solid var(--line)', gap: 16,
      }}>
        <Wordmark size={15} markSize={28} glow={false} />
        <span className="muted" style={{ fontSize: 12.5 }}>© 2026 ShipMate AI · Navigate every repo to production.</span>
        <div style={{ display: 'flex', gap: 24 }}>
          {['Docs', 'Security', 'GitHub'].map(l => (
            <a key={l} href="#" className="muted" style={{ fontSize: 12.5 }}>{l}</a>
          ))}
        </div>
      </footer>
    </section>
  );
}
