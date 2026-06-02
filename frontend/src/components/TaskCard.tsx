import type { Milestone } from '../types';

const PRI: Record<string, { badge: string; dot: string }> = {
  critical: { badge: 'bg-red-500/20 text-red-300',    dot: 'bg-red-500' },
  high:     { badge: 'bg-orange-500/20 text-orange-300', dot: 'bg-orange-500' },
  medium:   { badge: 'bg-yellow-500/20 text-yellow-300', dot: 'bg-yellow-400' },
  low:      { badge: 'bg-slate-600/40 text-slate-300',   dot: 'bg-slate-500' },
};

const CAT_ICON: Record<string, string> = {
  feature: '✨', testing: '🧪', security: '🔒', ci_cd: '⚙️',
  infra: '🏗️', docs: '📄',
};

export function TaskCard({ milestone }: { milestone: Milestone }) {
  const pri = PRI[milestone.priority] ?? PRI.low;
  const icon = CAT_ICON[milestone.category] ?? '📌';
  return (
    <div className="rounded-xl p-4 border bg-slate-800/50 border-slate-700/40 hover:border-blue-500/30 transition-colors">
      <div className="flex items-start gap-3">
        <span className="text-lg leading-none">{icon}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="text-sm font-semibold text-slate-100">{milestone.title}</span>
            <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${pri.badge}`}>
              {milestone.priority}
            </span>
          </div>
          <p className="text-sm text-slate-400 mb-2">{milestone.description}</p>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span>⏱ {milestone.estimated_days} day{milestone.estimated_days !== 1 ? 's' : ''}</span>
            <span className="capitalize">{milestone.category.replace('_', ' ')}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
