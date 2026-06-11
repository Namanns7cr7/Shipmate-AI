import { Lock } from 'lucide-react';
import { GitHubIcon } from './GitHubIcon';
import { RadarBg } from './RadarBg';
import { GitHubConnectButton } from './GitHubConnectButton';

interface EmptyStateProps { onConnect: () => void; }

export function EmptyState({ onConnect }: EmptyStateProps) {
  return (
    <div className="card glow-border" style={{ padding: '56px 32px', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
      <RadarBg sweep rings blobs={false} style={{ opacity: 0.5 }} />
      <div style={{ position: 'relative' }}>
        <div style={{
          width: 76, height: 76, borderRadius: 22, margin: '0 auto 22px',
          display: 'grid', placeItems: 'center',
          background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line-2)',
          boxShadow: '0 0 40px rgba(37,99,235,0.25)',
        }}>
          <GitHubIcon size={36} style={{ color: '#fff' }} />
        </div>
        <h3 style={{ fontSize: 22, fontWeight: 800, margin: '0 0 8px', letterSpacing: '-0.02em' }}>
          Connect a repository to begin
        </h3>
        <p className="muted" style={{ maxWidth: 420, margin: '0 auto 24px', fontSize: 14, lineHeight: 1.6 }}>
          ShipMate reads your GitHub repos, runs four agents to score readiness and
          surface risks, then opens pull requests that fix what it finds.
        </p>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
          <GitHubConnectButton onClick={onConnect} label="Connect GitHub" size="lg" />
          <span className="pill"><Lock size={12} /> Token stays server-side · revoke anytime</span>
        </div>
      </div>
    </div>
  );
}
