import type { ShipMateReport } from '../types';

const REC_CONFIG: Record<string, { headline: string; sub: string; color: string; bg: string; border: string; icon: string }> = {
  ready_to_ship:  { headline: 'Ship It!',         sub: 'All key checks passed. The team is ready to release.',                       color: 'text-emerald-300', bg: 'bg-emerald-950/40', border: 'border-emerald-500/30', icon: '🚀' },
  mostly_ready:   { headline: 'Almost There',     sub: 'A few items to tidy up before release — nothing blocking.',                  color: 'text-green-300',   bg: 'bg-green-950/40',   border: 'border-green-500/30',   icon: '🟢' },
  needs_review:   { headline: 'Needs Review',     sub: 'Several issues need addressing before this is safe to release.',             color: 'text-yellow-300',  bg: 'bg-yellow-950/40',  border: 'border-yellow-500/30',  icon: '🟡' },
  risky_release:  { headline: 'Risky Release',    sub: 'Significant gaps in security, tests, or delivery confidence.',               color: 'text-orange-300',  bg: 'bg-orange-950/40',  border: 'border-orange-500/30',  icon: '🟠' },
  not_ready:      { headline: 'Do NOT Ship',      sub: 'Critical blockers detected. Shipping now will cause production incidents.',  color: 'text-red-300',     bg: 'bg-red-950/40',     border: 'border-red-500/30',     icon: '🔴' },
};

export function ReleaseTab({ report }: { report: ShipMateReport }) {
  const rec = REC_CONFIG[report.ship_recommendation] ?? REC_CONFIG.not_ready;
  const { score_breakdown: sb } = report;

  return (
    <div className="space-y-6">
      {/* Ship / No-ship verdict */}
      <div className={`rounded-2xl p-6 border ${rec.bg} ${rec.border} text-center`}>
        <div className="text-5xl mb-3">{rec.icon}</div>
        <h2 className={`text-2xl font-black mb-1 ${rec.color}`}>{rec.headline}</h2>
        <p className="text-sm text-slate-400">{rec.sub}</p>
        <div className={`mt-4 text-5xl font-black ${rec.color}`}>{report.readiness_score}<span className="text-2xl">/100</span></div>
        <div className="text-xs text-slate-500 mt-1">Readiness Score</div>
      </div>

      {/* Score breakdown */}
      <div className="rounded-xl bg-slate-900/50 border border-slate-700/30 p-4">
        <h3 className="text-sm font-bold text-slate-300 mb-3">📊 Score Breakdown</h3>
        {[
          { label: 'Repo Structure', val: sb.repo_score,     weight: 20 },
          { label: 'Delivery Plan',  val: sb.delivery_score, weight: 25 },
          { label: 'Security',       val: sb.security_score, weight: 30 },
          { label: 'Test Coverage',  val: sb.test_score,     weight: 25 },
        ].map(({ label, val, weight }) => (
          <div key={label} className="mb-2">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">{label} ({weight}%)</span>
              <span className={`font-bold ${val >= 80 ? 'text-emerald-400' : val >= 60 ? 'text-yellow-400' : val >= 40 ? 'text-orange-400' : 'text-red-400'}`}>{val}</span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-700/60">
              <div
                className={`h-full rounded-full transition-all ${val >= 80 ? 'bg-emerald-500' : val >= 60 ? 'bg-yellow-500' : val >= 40 ? 'bg-orange-500' : 'bg-red-500'}`}
                style={{ width: `${val}%` }}
              />
            </div>
          </div>
        ))}
        <p className="text-xs text-slate-600 mt-3">
          Formula: repo×20% + delivery×25% + security×30% + tests×25%
        </p>
      </div>

      {/* Key blockers */}
      {report.key_blockers.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">🚧 Blockers Before Release</h3>
          <ul className="space-y-1.5">
            {report.key_blockers.map((b, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300 bg-red-950/20 border border-red-500/15 rounded-lg px-3 py-2">
                <span className="text-red-400 flex-shrink-0">⛔</span>{b}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Next actions */}
      {report.next_actions.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">⚡ Action Plan</h3>
          <ol className="space-y-1.5">
            {report.next_actions.map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300 bg-blue-950/20 border border-blue-500/15 rounded-lg px-3 py-2">
                <span className="text-blue-400 font-bold flex-shrink-0">{i + 1}.</span>{a}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Metadata */}
      <div className="text-xs text-slate-600 border-t border-slate-700/30 pt-3">
        Analyzed: {report.repo.full_name} @ {report.repo.branch} · Generated {new Date(report.generated_at).toLocaleString()}
      </div>
    </div>
  );
}
