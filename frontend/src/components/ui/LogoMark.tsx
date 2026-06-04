import { useId } from 'react';

interface LogoMarkProps { size?: number; glow?: boolean; }

export function LogoMark({ size = 34, glow = true }: LogoMarkProps) {
  const uid = useId();
  const id = `lg${uid.replace(/:/g, '')}`;

  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-label="ShipMate"
      style={{ filter: glow ? 'drop-shadow(0 6px 16px rgba(37,99,235,0.45))' : 'none', flexShrink: 0 }}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0"    stopColor="#3b82f6" />
          <stop offset="0.55" stopColor="#2563eb" />
          <stop offset="1"    stopColor="#0e7490" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="44" height="44" rx="13" fill={`url(#${id})`} />
      <rect x="2.5" y="2.5" width="43" height="43" rx="12.5" fill="none" stroke="rgba(255,255,255,0.22)" />
      <circle cx="24" cy="24" r="13" fill="none" stroke="rgba(255,255,255,0.32)" strokeWidth="1.4" />
      {[0, 90, 180, 270].map(a => (
        <line key={a} x1="24" y1="9.5" x2="24" y2="12.5"
          stroke="rgba(255,255,255,0.7)" strokeWidth="1.6" strokeLinecap="round"
          transform={`rotate(${a} 24 24)`} />
      ))}
      <polygon points="24,12 28,24 24,21 20,24" fill="#ffffff" />
      <polygon points="24,36 20,24 24,27 28,24" fill="rgba(255,255,255,0.45)" />
      <circle cx="24" cy="24" r="2.1" fill="#0a1326" stroke="#fff" strokeWidth="1.1" />
    </svg>
  );
}

interface WordmarkProps { size?: number; markSize?: number; glow?: boolean; }

export function Wordmark({ size = 18, markSize = 34, glow = true }: WordmarkProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <LogoMark size={markSize} glow={glow} />
      <span style={{ fontSize: size, fontWeight: 800, letterSpacing: '-0.02em', color: '#fff' }}>
        ShipMate<span style={{ color: 'var(--blue-2)' }}> AI</span>
      </span>
    </div>
  );
}
