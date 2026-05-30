import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface ReadinessScoreProps {
  score: number;
  breakdown: Record<string, number>;
}

function ScoreRing({ score }: { score: number }) {
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const getColor = (s: number) => {
    if (s >= 80) return '#10b981';
    if (s >= 60) return '#f59e0b';
    return '#ef4444';
  };

  const color = getColor(score);

  return (
    <div style={{ position: 'relative', width: 160, height: 160, flexShrink: 0 }}>
      <svg width="160" height="160" style={{ transform: 'rotate(-90deg)' }}>
        {/* Track */}
        <circle
          cx="80" cy="80" r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth="10"
        />
        {/* Progress */}
        <motion.circle
          cx="80" cy="80" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.5, ease: 'easeOut', delay: 0.3 }}
          style={{ filter: `drop-shadow(0 0 8px ${color})` }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        gap: 2,
      }}>
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.8, type: 'spring' }}
          style={{
            fontSize: 36, fontWeight: 900, lineHeight: 1,
            color,
            textShadow: `0 0 20px ${color}`,
          }}
        >
          {score}
        </motion.div>
        <div style={{ fontSize: 12, color: '#4a6180', fontWeight: 500 }}>/ 100</div>
      </div>
    </div>
  );
}

const DIMENSION_LABELS: Record<string, string> = {
  task_clarity: 'Task Clarity',
  test_coverage: 'Test Coverage',
  security_score: 'Security Score',
  deployment_confidence: 'Deploy Confidence',
  repo_confidence: 'Repo Confidence',
  cicd_readiness: 'CI/CD Readiness',
};

const DIMENSION_COLORS: Record<string, string> = {
  task_clarity: '#60a5fa',
  test_coverage: '#34d399',
  security_score: '#f87171',
  deployment_confidence: '#fbbf24',
  repo_confidence: '#a78bfa',
  cicd_readiness: '#06b6d4',
};

export function ReadinessScore({ score, breakdown }: ReadinessScoreProps) {
  const label = score >= 80 ? 'Production Ready' : score >= 60 ? 'Needs Work' : 'Not Ready';
  const trendUp = score >= 70;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      style={{
        padding: '28px',
        background: 'rgba(17, 24, 39, 0.85)',
        border: '1px solid rgba(99, 179, 237, 0.12)',
        borderRadius: 20,
        backdropFilter: 'blur(12px)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 28, flexWrap: 'wrap' }}>
        {/* Score Ring */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <ScoreRing score={score} />
          <div style={{ textAlign: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center' }}>
              {trendUp ? <TrendingUp size={14} color="#10b981" /> : <TrendingDown size={14} color="#ef4444" />}
              <span style={{
                fontSize: 13,
                fontWeight: 700,
                color: score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444',
              }}>
                {label}
              </span>
            </div>
            <div style={{ fontSize: 11, color: '#4a6180', marginTop: 2 }}>Production Readiness</div>
          </div>
        </div>

        {/* Breakdown */}
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ marginBottom: 16, fontWeight: 700, fontSize: 15, color: '#f0f6ff' }}>Score Breakdown</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {Object.entries(breakdown).map(([key, value]) => {
              const color = DIMENSION_COLORS[key] || '#60a5fa';
              const label = DIMENSION_LABELS[key] || key;
              return (
                <div key={key}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 12, color: '#8ba3c1' }}>{label}</span>
                    <span style={{ fontSize: 12, fontWeight: 700, color }}>{value}</span>
                  </div>
                  <div style={{ height: 4, background: 'rgba(255,255,255,0.05)', borderRadius: 2 }}>
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${value}%` }}
                      transition={{ duration: 1, ease: 'easeOut', delay: 0.5 }}
                      style={{
                        height: '100%',
                        background: color,
                        borderRadius: 2,
                        boxShadow: `0 0 6px ${color}50`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
