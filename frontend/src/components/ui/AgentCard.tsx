import type { AgentDef } from '../../lib/agents';
import { Spinner } from './GitHubConnectButton';
import { Check, Clock } from 'lucide-react';

interface AgentStat { k: string; v: string | number; color?: string; }

interface AgentCardProps {
  agent: AgentDef;
  status?: 'pending' | 'running' | 'complete' | 'error';
  progress?: number;
  stats?: AgentStat[];
  compact?: boolean;
}

export function AgentCard({ agent: a, status = 'pending', progress = 0, stats, compact = false }: AgentCardProps) {
  const isRunning  = status === 'running';
  const isComplete = status === 'complete';

  const statChip = isComplete
    ? { label: 'Complete', tone: 'emerald' }
    : isRunning
    ? { label: 'Running',  tone: a.tone    }
    : status === 'error'
    ? { label: 'Error',    tone: 'red'     }
    : { label: 'Queued',   tone: 'slate'   };

  return (
    <div className="card" style={{
      padding: compact ? 14 : 16,
      borderColor: status !== 'pending' ? `${a.hex}40` : 'var(--line)',
      background: isRunning ? `linear-gradient(180deg, ${a.hex}12, var(--panel))` : 'var(--panel)',
      transition: 'all .4s ease',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 38, height: 38, borderRadius: 11, display: 'grid', placeItems: 'center', flexShrink: 0,
            background: `${a.hex}1c`, border: `1px solid ${a.hex}55`, color: a.hex,
            boxShadow: isRunning ? `0 0 16px ${a.hex}55` : 'none',
          }}>
            <a.Icon size={19} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14.5, color: '#fff' }}>{a.name}</div>
            <div style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>{a.tag}</div>
          </div>
        </div>
        <span className={`chip tone-${statChip.tone}`} style={{ flexShrink: 0 }}>
          {isRunning ? <Spinner size={11} /> : isComplete ? <Check size={12} /> : <Clock size={11} />}
          {statChip.label}
        </span>
      </div>

      {!compact && <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 10, lineHeight: 1.5 }}>{a.sub}</div>}

      {status !== 'pending' && (
        <div className="track" style={{ marginTop: 12 }}>
          <i style={{ width: `${progress}%`, background: `linear-gradient(90deg, ${a.hex}, ${a.hex}aa)` }} />
        </div>
      )}

      {isComplete && stats && (
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          {stats.map((s, i) => (
            <div key={i} style={{ flex: 1, background: 'rgba(0,0,0,0.25)', borderRadius: 9, padding: '8px 10px' }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: s.color ?? '#fff' }}>{s.v}</div>
              <div style={{ fontSize: 9.5, color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>{s.k}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
