import { useEffect, useState } from 'react';
import { scoreColor } from '../../lib/agents';

function CountUp({ to, dur = 1300 }: { to: number; dur?: number }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    let raf: number;
    let start = 0;
    const step = (t: number) => {
      if (!start) start = t;
      const p = Math.min((t - start) / dur, 1);
      setN(Math.round((1 - Math.pow(1 - p, 3)) * to));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [to, dur]);
  return <>{n}</>;
}

interface ScoreRingProps {
  value?: number;
  size?: number;
  stroke?: number;
  label?: string;
  sub?: string;
  animate?: boolean;
  delay?: number;
}

export function ScoreRing({ value = 0, size = 120, stroke = 9, label, sub, animate = true, delay = 200 }: ScoreRingProps) {
  const [displayed, setDisplayed] = useState(0);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const color = scoreColor(value);
  // When not animating, derive v directly; when animating, use the timed state
  const v = animate ? displayed : value;

  useEffect(() => {
    if (!animate) return;
    const t = setTimeout(() => setDisplayed(value), delay);
    return () => clearTimeout(t);
  }, [value, animate, delay]);

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size}
        style={{ transform: 'rotate(-90deg)', filter: `drop-shadow(0 0 10px ${color}55)` }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke="rgba(255,255,255,0.07)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (v / 100) * c}
          style={{ transition: 'stroke-dashoffset 1.3s cubic-bezier(.2,.7,.2,1)' }} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: size * 0.3, fontWeight: 800, color: '#fff', lineHeight: 1 }}>
          {animate ? <CountUp to={value} /> : value}
        </span>
        {label && <div style={{ fontSize: size * 0.1, fontWeight: 700, color, marginTop: 3 }}>{label}</div>}
        {sub   && <div style={{ fontSize: 10, color: 'var(--ink-3)', marginTop: 1 }}>{sub}</div>}
      </div>
    </div>
  );
}
