import { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';

export interface LogLine {
  time: string;
  agent: string;
  text: string;
  tone?: string;
}

const TONE_HEX: Record<string, string> = {
  slate: '#94a3b8', emerald: '#34d399', purple: '#a78bfa',
  amber: '#fbbf24', cyan: '#22d3ee', red: '#f87171',
};

interface LiveActivityLogProps {
  lines: LogLine[];
  title?: string;
  height?: number;
}

export function LiveActivityLog({ lines, title = 'Agent Activity Log', height = 230 }: LiveActivityLogProps) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [lines]);

  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid var(--line)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="dot dot-pulse" style={{ background: '#34d399' }} />
          <span style={{ fontSize: 12.5, fontWeight: 700, color: '#fff' }}>{title}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, opacity: 0.4 }}>
          <Terminal size={13} />
          <span className="mono" style={{ fontSize: 11 }}>stream</span>
        </div>
      </div>
      <div ref={ref} className="mono"
        style={{ height, overflowY: 'auto', padding: '12px 16px', fontSize: 12, lineHeight: 1.9, background: 'rgba(0,0,0,0.22)' }}>
        {lines.map((l, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}
            className="anim-in">
            <span style={{ color: 'var(--ink-4)', flexShrink: 0 }}>{l.time}</span>
            <span style={{ color: TONE_HEX[l.tone ?? 'slate'] ?? '#94a3b8', flexShrink: 0, fontWeight: 600 }}>
              {l.agent === 'system' ? '›' : `[${l.agent}]`}
            </span>
            <span style={{ color: l.tone === 'red' ? '#fca5a5' : 'var(--ink-2)' }}>{l.text}</span>
          </div>
        ))}
        {lines.length === 0 && <div style={{ color: 'var(--ink-4)' }}>awaiting agents…</div>}
        <span style={{ display: 'inline-block', width: 8, height: 15, background: '#34d399', verticalAlign: 'middle', animation: 'blink 1s steps(1) infinite' }} />
      </div>
    </div>
  );
}
