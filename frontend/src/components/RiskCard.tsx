import type { SecurityFinding, Severity } from '../types';

const SEV_CONFIG: Record<Severity, { bg: string; border: string; badge: string; dot: string }> = {
  critical: { bg: 'bg-red-950/40', border: 'border-red-500/30', badge: 'bg-red-500/20 text-red-300', dot: 'bg-red-500' },
  high:     { bg: 'bg-orange-950/40', border: 'border-orange-500/30', badge: 'bg-orange-500/20 text-orange-300', dot: 'bg-orange-500' },
  medium:   { bg: 'bg-yellow-950/30', border: 'border-yellow-500/20', badge: 'bg-yellow-500/20 text-yellow-300', dot: 'bg-yellow-400' },
  low:      { bg: 'bg-slate-800/40', border: 'border-slate-600/30', badge: 'bg-slate-600/40 text-slate-300', dot: 'bg-slate-400' },
  info:     { bg: 'bg-blue-950/30', border: 'border-blue-500/20', badge: 'bg-blue-500/20 text-blue-300', dot: 'bg-blue-400' },
};

export function RiskCard({ finding }: { finding: SecurityFinding }) {
  const cfg = SEV_CONFIG[finding.severity] ?? SEV_CONFIG.info;
  return (
    <div className={`rounded-xl p-4 border ${cfg.bg} ${cfg.border}`}>
      <div className="flex items-start gap-3">
        <span className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot}`} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="text-sm font-semibold text-slate-100">{finding.title}</span>
            <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${cfg.badge}`}>
              {finding.severity}
            </span>
            <span className="text-xs text-slate-500 uppercase tracking-wide">{finding.category}</span>
            {finding.id && <span className="text-xs text-slate-600 font-mono">{finding.id}</span>}
          </div>
          <p className="text-sm text-slate-400 mb-2">{finding.description}</p>
          <div className="rounded-lg bg-slate-900/60 px-3 py-2 border border-slate-700/30">
            <span className="text-xs font-semibold text-emerald-400 mr-2">Fix:</span>
            <span className="text-xs text-slate-300">{finding.recommendation}</span>
          </div>
          {finding.file && (
            <p className="mt-1 text-xs text-slate-600 font-mono">📁 {finding.file}</p>
          )}
          {finding.cve && (
            <p className="mt-1 text-xs text-slate-600">🔗 {finding.cve}</p>
          )}
        </div>
      </div>
    </div>
  );
}
