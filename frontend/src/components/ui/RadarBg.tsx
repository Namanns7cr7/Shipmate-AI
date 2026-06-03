import type { CSSProperties } from 'react';

interface RadarBgProps {
  sweep?: boolean;
  rings?: boolean;
  blobs?: boolean;
  style?: CSSProperties;
}

export function RadarBg({ sweep = false, rings = true, blobs = true, style }: RadarBgProps) {
  return (
    <div className="grid-bg" aria-hidden="true"
      style={{ position: 'absolute', inset: 0, overflow: 'hidden', ...style }}>
      {blobs && (
        <>
          <div className="aurora" style={{ width: 520, height: 520, top: -160, left: -120,  background: 'radial-gradient(circle, rgba(37,99,235,0.5), transparent 70%)' }} />
          <div className="aurora" style={{ width: 460, height: 460, top: -80,  right: -140, background: 'radial-gradient(circle, rgba(139,92,246,0.4), transparent 70%)' }} />
          <div className="aurora" style={{ width: 420, height: 420, bottom: -180, left: '38%', background: 'radial-gradient(circle, rgba(14,116,144,0.4), transparent 70%)' }} />
        </>
      )}
      {rings && (
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', opacity: 0.5 }}>
          {[260, 460, 680, 920].map(s => (
            <div key={s} className="compass-ring"
              style={{ position: 'absolute', width: s, height: s, top: -s / 2, left: -s / 2 }} />
          ))}
          {sweep && (
            <div style={{ position: 'absolute', width: 680, height: 680, top: -340, left: -340 }}>
              <div className="radar-sweep" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
