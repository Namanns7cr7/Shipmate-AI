import type { RepoLensOutput } from '../types';

const IMPACT_COLOR: Record<string, string> = {
  critical: 'text-red-400 bg-red-500/10 border-red-500/20',
  high:     'text-orange-400 bg-orange-500/10 border-orange-500/20',
  medium:   'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  low:      'text-slate-400 bg-slate-700/30 border-slate-600/30',
};

export function RepoTab({ data }: { data: RepoLensOutput }) {
  return (
    <div className="space-y-6">
      {/* Summary chips */}
      <div className="grid grid-cols-3 gap-3">
        <InfoBox label="Architecture" value={data.architecture_pattern} icon="🏗️" />
        <InfoBox label="Primary Lang" value={data.primary_language} icon="💻" />
        <InfoBox label="Files" value={String(data.file_count)} icon="📁" />
      </div>

      {/* Status flags */}
      <div className="grid grid-cols-3 gap-2">
        <Flag ok={data.has_ci_cd}    label="CI / CD" />
        <Flag ok={data.has_dockerfile} label="Dockerfile" />
        <Flag ok={data.has_tests}    label="Tests" />
      </div>

      {/* Tech stack */}
      {data.tech_stack.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">🧰 Tech Stack</h3>
          <div className="flex flex-wrap gap-2">
            {data.tech_stack.map(t => (
              <span key={t} className="px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 font-medium">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Key modules */}
      {data.key_modules.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">📦 Key Modules</h3>
          <div className="flex flex-wrap gap-2">
            {data.key_modules.map(m => (
              <span key={m} className="px-2.5 py-1 rounded-lg bg-slate-800/60 border border-slate-700/40 text-xs text-slate-300 font-mono">
                {m}/
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Entry points */}
      {data.entry_points.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">🚪 Entry Points</h3>
          <div className="space-y-1">
            {data.entry_points.map(e => (
              <div key={e} className="flex items-center gap-2 text-xs font-mono text-slate-300 bg-slate-900/50 border border-slate-700/30 rounded-lg px-3 py-1.5">
                <span className="text-slate-500">▶</span> {e}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Architecture risks */}
      {data.architecture_risks.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">⚠️ Architecture Risks</h3>
          <div className="space-y-2">
            {data.architecture_risks.map((r, i) => (
              <div key={i} className={`rounded-xl px-4 py-3 border ${IMPACT_COLOR[r.impact] ?? IMPACT_COLOR.low}`}>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{r.risk}</span>
                  <span className={`text-xs uppercase font-bold px-2 py-0.5 rounded-full border ${IMPACT_COLOR[r.impact] ?? IMPACT_COLOR.low}`}>{r.impact}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Dependencies */}
      {Object.entries(data.dependency_summary).map(([eco, pkgs]) => pkgs.length > 0 && (
        <div key={eco}>
          <h3 className="text-sm font-bold text-slate-300 mb-2 capitalize">📦 {eco} Dependencies ({pkgs.length})</h3>
          <div className="flex flex-wrap gap-1.5">
            {pkgs.slice(0, 30).map(p => (
              <span key={p} className="px-2 py-0.5 rounded bg-slate-800/60 border border-slate-700/30 text-xs text-slate-400 font-mono">
                {p}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function InfoBox({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div className="rounded-xl bg-slate-900/50 border border-slate-700/30 p-3 text-center">
      <div className="text-lg mb-1">{icon}</div>
      <div className="text-sm font-semibold text-slate-200 capitalize">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

function Flag({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className={`rounded-lg px-3 py-2 text-center border text-xs font-semibold ${
      ok ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400'
         : 'bg-red-500/10 border-red-500/20 text-red-400'
    }`}>
      {ok ? '✅' : '❌'} {label}
    </div>
  );
}
