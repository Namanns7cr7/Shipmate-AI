import type { PlanForgeOutput } from '../types';
import { TaskCard } from '../components/TaskCard';

export function PlanTab({ data }: { data: PlanForgeOutput }) {
  return (
    <div className="space-y-6">
      {/* Summary row */}
      <div className="grid grid-cols-3 gap-3">
        <StatBox label="Delivery Score" value={`${data.delivery_score}/100`} color={data.delivery_score >= 70 ? 'text-emerald-400' : 'text-orange-400'} />
        <StatBox label="Est. Effort" value={data.estimated_effort} color="text-blue-300" />
        <StatBox label="Blockers" value={`${data.blockers.length}`} color={data.blockers.length === 0 ? 'text-emerald-400' : 'text-red-400'} />
      </div>

      {/* Next best action */}
      {data.next_best_action && (
        <div className="rounded-xl bg-blue-950/30 border border-blue-500/20 px-4 py-3">
          <p className="text-xs font-semibold text-blue-400 mb-1">⚡ NEXT BEST ACTION</p>
          <p className="text-sm text-slate-200">{data.next_best_action}</p>
        </div>
      )}

      {/* Blockers */}
      {data.blockers.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-3">🚧 Blockers</h3>
          <div className="space-y-3">
            {data.blockers.map(b => (
              <div key={b.id} className="rounded-xl p-4 bg-slate-900/50 border border-red-500/20">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="text-sm font-semibold text-slate-100">{b.title}</span>
                  <SevBadge sev={b.severity} />
                  <span className="text-xs text-slate-600 font-mono">{b.id}</span>
                </div>
                <p className="text-sm text-slate-400 mb-2">{b.description}</p>
                <div className="rounded-lg bg-slate-900/60 px-3 py-2 border border-slate-700/30">
                  <span className="text-xs font-semibold text-emerald-400 mr-2">Resolution:</span>
                  <span className="text-xs text-slate-300">{b.resolution}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Milestones */}
      {data.milestones.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-3">🗺️ Milestones</h3>
          <div className="space-y-2">
            {data.milestones.map((m, i) => (
              <TaskCard key={i} milestone={m} />
            ))}
          </div>
        </div>
      )}

      {/* Dependencies */}
      {data.dependencies.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-3">🔗 Dependencies</h3>
          <ul className="space-y-1">
            {data.dependencies.map((d, i) => (
              <li key={i} className="text-sm text-slate-400 flex items-start gap-2">
                <span className="text-slate-600 mt-0.5">•</span>{d}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-xl bg-slate-900/50 border border-slate-700/30 p-3 text-center">
      <div className={`text-lg font-black ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-0.5">{label}</div>
    </div>
  );
}

function SevBadge({ sev }: { sev: string }) {
  const cls =
    sev === 'critical' ? 'bg-red-500/20 text-red-300' :
    sev === 'high'     ? 'bg-orange-500/20 text-orange-300' :
                         'bg-yellow-500/20 text-yellow-300';
  return <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${cls}`}>{sev}</span>;
}
