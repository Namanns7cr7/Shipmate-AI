import { useEffect, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { GitHubIcon } from '../ui/GitHubIcon';
import { AGENTS } from '../../lib/agents';
import { ScoreRing } from '../ui/ScoreRing';
import { VerdictPill } from '../ui/VerdictPill';
import { Spinner } from '../ui/GitHubConnectButton';

const COMPLETE_STATS: Record<string, string> = {
  repolens: '8 deps flagged', planforge: '4 milestones',
  guardrail: '1 critical',   testpilot: '+18% cov',
};

export function LiveAgentPreview() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setPhase(p => (p + 1) % 9), 950);
    return () => clearInterval(id);
  }, []);

  const statusFor = (i: number) =>
    phase < i + 1 ? 'pending' : phase === i + 1 ? 'running' : 'complete';
  const done = phase >= 5;

  return (
    <div className="card glow-border" style={{ padding: 0, overflow: 'hidden', boxShadow: 'var(--shadow-glow)' }}>
      {/* Window chrome */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid var(--line)', background: 'rgba(0,0,0,0.2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <GitHubIcon size={16} style={{ color: 'var(--ink-2)' }} />
          <span className="mono" style={{ fontSize: 12.5, color: '#fff', fontWeight: 600 }}>northwind-labs/atlas-checkout</span>
          <span className="chip tone-emerald" style={{ fontSize: 10 }}>
            <span className="dot dot-pulse" style={{ background: '#34d399' }} /> connected
          </span>
        </div>
        <span className="mono" style={{ fontSize: 11, color: 'var(--ink-4)' }}>main · a9f3c21</span>
      </div>

      <div style={{ padding: 18, display: 'grid', gridTemplateColumns: '1fr 150px', gap: 18 }}>
        {/* Agents list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div className="eyebrow" style={{ marginBottom: 2 }}>Agents · live</div>
          {AGENTS.map((a, i) => {
            const st = statusFor(i);
            return (
              <div key={a.key} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '9px 11px', borderRadius: 11, transition: 'all .35s ease',
                background: st === 'running' ? `${a.hex}14` : 'rgba(255,255,255,0.02)',
                border: `1px solid ${st === 'pending' ? 'var(--line)' : a.hex + '44'}`,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: 8, display: 'grid', placeItems: 'center', flexShrink: 0,
                    background: `${a.hex}1c`, color: a.hex,
                    boxShadow: st === 'running' ? `0 0 12px ${a.hex}66` : 'none',
                  }}>
                    <a.Icon size={15} />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 650, color: '#fff' }}>{a.name}</div>
                    <div style={{ fontSize: 10.5, color: 'var(--ink-3)' }}>
                      {st === 'complete' ? COMPLETE_STATS[a.key] : st === 'running' ? 'working…' : 'queued'}
                    </div>
                  </div>
                </div>
                {st === 'running'  ? <Spinner size={13} color={a.hex} dark={false} />
                 : st === 'complete' ? <CheckCircle2 size={16} style={{ color: a.hex }} />
                 : <span className="dot" style={{ background: 'var(--ink-4)' }} />}
              </div>
            );
          })}
        </div>

        {/* Readiness ring */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
          <div className="eyebrow">Readiness</div>
          <div style={{ opacity: done ? 1 : 0.3, transition: 'opacity .6s' }}>
            <ScoreRing value={done ? 72 : 0} size={120} stroke={9} delay={100} />
          </div>
          {done
            ? <VerdictPill verdict="Needs Fixes" />
            : <span className="chip tone-slate"><Spinner size={11} dark={false} /> computing…</span>
          }
        </div>
      </div>

      {/* Findings strip */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', padding: '0 18px 18px' }}>
        {([['1 critical', 'red'], ['3 high', 'orange'], ['6 medium', 'amber'], ['61% → 79% coverage', 'cyan']] as [string, string][]).map(([t, tone]) => (
          <span key={t} className={`chip tone-${tone}`} style={{ opacity: done ? 1 : 0.4, transition: 'opacity .5s' }}>{t}</span>
        ))}
      </div>
    </div>
  );
}
