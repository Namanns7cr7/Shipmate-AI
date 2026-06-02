import { motion } from 'framer-motion';
import type { ScoreBreakdown, ShipRecommendation } from '../types';

const REC_CONFIG: Record<ShipRecommendation, { label: string; color: string; bg: string; border: string }> = {
  ready_to_ship:  { label: '✅ Ready to Ship',  color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  mostly_ready:   { label: '🟢 Mostly Ready',   color: 'text-green-400',   bg: 'bg-green-500/10',   border: 'border-green-500/30' },
  needs_review:   { label: '🟡 Needs Review',   color: 'text-yellow-400',  bg: 'bg-yellow-500/10',  border: 'border-yellow-500/30' },
  risky_release:  { label: '🟠 Risky Release',  color: 'text-orange-400',  bg: 'bg-orange-500/10',  border: 'border-orange-500/30' },
  not_ready:      { label: '🔴 Not Ready',       color: 'text-red-400',     bg: 'bg-red-500/10',     border: 'border-red-500/30' },
};

const DIM_LABELS: [keyof ScoreBreakdown, string, number][] = [
  ['repo_score',     'Repo Structure', 20],
  ['delivery_score', 'Delivery Plan',  25],
  ['security_score', 'Security',       30],
  ['test_score',     'Test Coverage',  25],
];

function scoreColor(n: number) {
  if (n >= 80) return 'text-emerald-400';
  if (n >= 60) return 'text-yellow-400';
  if (n >= 40) return 'text-orange-400';
  return 'text-red-400';
}
function barColor(n: number) {
  if (n >= 80) return 'bg-emerald-500';
  if (n >= 60) return 'bg-yellow-500';
  if (n >= 40) return 'bg-orange-500';
  return 'bg-red-500';
}
function strokeColor(n: number) {
  if (n >= 80) return '#10b981';
  if (n >= 60) return '#eab308';
  if (n >= 40) return '#f97316';
  return '#ef4444';
}

export function ReadinessScore({
  score,
  recommendation,
  breakdown,
}: {
  score: number;
  recommendation: ShipRecommendation;
  breakdown: ScoreBreakdown;
}) {
  const rec = REC_CONFIG[recommendation] ?? REC_CONFIG.not_ready;
  const r = 54, circ = 2 * Math.PI * r;
  const dashOffset = circ - (score / 100) * circ;

  return (
    <div className="rounded-2xl border bg-slate-800/60 border-slate-700/40 p-6">
      <div className="flex flex-col sm:flex-row items-center gap-8">
        {/* Ring */}
        <div className="relative flex-shrink-0">
          <svg width={136} height={136}>
            <circle cx={68} cy={68} r={r} fill="none" stroke="#1e293b" strokeWidth={10} />
            <motion.circle
              cx={68} cy={68} r={r}
              fill="none"
              stroke={strokeColor(score)}
              strokeWidth={10}
              strokeLinecap="round"
              strokeDasharray={circ}
              initial={{ strokeDashoffset: circ }}
              animate={{ strokeDashoffset: dashOffset }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
              style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <motion.span
              className={`text-4xl font-black ${scoreColor(score)}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
            >
              {score}
            </motion.span>
            <span className="text-xs text-slate-500 font-medium">/ 100</span>
          </div>
        </div>

        {/* Recommendation + breakdown */}
        <div className="flex-1 w-full">
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-semibold mb-4 ${rec.bg} ${rec.border} ${rec.color}`}>
            {rec.label}
          </div>
          <div className="space-y-2">
            {DIM_LABELS.map(([key, label, weight]) => {
              const val = breakdown[key];
              return (
                <div key={key}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">{label} <span className="text-slate-600">({weight}%)</span></span>
                    <span className={`font-bold ${scoreColor(val)}`}>{val}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-slate-700/60">
                    <motion.div
                      className={`h-full rounded-full ${barColor(val)}`}
                      initial={{ width: 0 }}
                      animate={{ width: `${val}%` }}
                      transition={{ duration: 0.8, delay: 0.2 }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
