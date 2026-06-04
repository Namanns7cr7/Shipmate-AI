import { useEffect, useState } from 'react';
import { PIPE } from '../../lib/agents';

interface WorkflowPipelineProps {
  active?: number;
  autoplay?: boolean;
  compact?: boolean;
}

export function WorkflowPipeline({ active = -1, autoplay = false, compact = false }: WorkflowPipelineProps) {
  const [autoStep, setAutoStep] = useState(0);
  // When not autoplaying, derive step from prop directly (no state needed)
  const step = autoplay ? autoStep : active;

  useEffect(() => {
    if (!autoplay) return;
    const id = setInterval(() => setAutoStep(s => (s + 1) % (PIPE.length + 2)), 1100);
    return () => clearInterval(id);
  }, [autoplay]);

  return (
    <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: compact ? 6 : 10, justifyContent: 'center' }}>
      {PIPE.map((node, i) => {
        const on  = autoplay ? i <= step : i <= active;
        const now = autoplay ? i === step : i === active;
        return (
          <div key={node.key} style={{ display: 'flex', alignItems: 'center', gap: compact ? 6 : 10 }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 7, minWidth: compact ? 58 : 78, transition: 'opacity .4s', opacity: on ? 1 : 0.4 }}>
              <div style={{
                width: compact ? 38 : 46, height: compact ? 38 : 46, borderRadius: 13,
                display: 'grid', placeItems: 'center',
                background: on ? `${node.hex}1f` : 'rgba(255,255,255,0.03)',
                border: `1px solid ${on ? node.hex + '88' : 'rgba(255,255,255,0.08)'}`,
                color: on ? node.hex : 'var(--ink-4)',
                boxShadow: now ? `0 0 0 4px ${node.hex}22, 0 0 22px ${node.hex}55` : 'none',
                transition: 'all .4s ease',
                transform: now ? 'scale(1.08)' : 'scale(1)',
              }}>
                <node.Icon size={compact ? 17 : 21} />
              </div>
              <span style={{ fontSize: compact ? 9.5 : 11, fontWeight: 650, color: on ? 'var(--ink-2)' : 'var(--ink-4)', textAlign: 'center', whiteSpace: 'nowrap' }}>
                {node.name}
              </span>
            </div>

            {i < PIPE.length - 1 && (
              <div style={{
                width: compact ? 16 : 28, height: 2, borderRadius: 2, marginTop: compact ? -16 : -20,
                background: on ? `linear-gradient(90deg, ${node.hex}, ${PIPE[i + 1].hex})` : 'rgba(255,255,255,0.08)',
                transition: 'all .4s ease',
                boxShadow: on ? `0 0 8px ${node.hex}66` : 'none',
              }} />
            )}
          </div>
        );
      })}
    </div>
  );
}
