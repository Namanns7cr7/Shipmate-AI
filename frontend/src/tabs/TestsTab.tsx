import type { TestPilotOutput } from '../types';

const QA_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  ready:     { label: '✅ QA Ready',     color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
  partial:   { label: '🟡 Partial',      color: 'text-yellow-400',  bg: 'bg-yellow-500/10 border-yellow-500/20' },
  not_ready: { label: '🔴 Not Ready',    color: 'text-red-400',     bg: 'bg-red-500/10 border-red-500/20' },
};

const TYPE_COLOR: Record<string, string> = {
  unit:        'bg-blue-500/20 text-blue-300',
  integration: 'bg-purple-500/20 text-purple-300',
  e2e:         'bg-emerald-500/20 text-emerald-300',
  security:    'bg-red-500/20 text-red-300',
  performance: 'bg-orange-500/20 text-orange-300',
};

const PRI_COLOR: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-300',
  high:     'bg-orange-500/20 text-orange-300',
  medium:   'bg-yellow-500/20 text-yellow-300',
  low:      'bg-slate-600/40 text-slate-400',
};

export function TestsTab({ data }: { data: TestPilotOutput }) {
  const { existing_tests: et } = data;
  const qa = QA_CONFIG[data.qa_readiness] ?? QA_CONFIG.not_ready;

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatBox label="Test Score" value={`${data.test_score}/100`}
          color={data.test_score >= 70 ? 'text-emerald-400' : data.test_score >= 40 ? 'text-yellow-400' : 'text-red-400'} />
        <StatBox label="Test Files" value={String(et.count)} color="text-blue-300" />
        <StatBox label="Coverage Est." value={`${et.coverage_estimate}%`}
          color={et.coverage_estimate >= 60 ? 'text-emerald-400' : et.coverage_estimate >= 30 ? 'text-yellow-400' : 'text-red-400'} />
        <div className={`rounded-xl border p-3 text-center ${qa.bg}`}>
          <div className={`text-sm font-bold ${qa.color}`}>{qa.label}</div>
          <div className="text-xs text-slate-500 mt-0.5">QA Readiness</div>
        </div>
      </div>

      {/* Frameworks */}
      {et.frameworks.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">🛠 Test Frameworks</h3>
          <div className="flex flex-wrap gap-2">
            {et.frameworks.map(f => (
              <span key={f} className="px-2.5 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-xs text-purple-300 font-medium">
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Test files */}
      {et.test_files.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">📂 Test Files ({et.test_files.length})</h3>
          <div className="max-h-36 overflow-y-auto space-y-1 pr-1">
            {et.test_files.map(f => (
              <div key={f} className="text-xs font-mono text-slate-400 bg-slate-900/40 border border-slate-700/30 rounded px-3 py-1">
                {f}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Missing coverage */}
      {data.missing_coverage_areas.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">🕳 Missing Coverage</h3>
          <ul className="space-y-1.5">
            {data.missing_coverage_areas.map((area, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300 bg-orange-950/20 border border-orange-500/15 rounded-lg px-3 py-2">
                <span className="text-orange-400 flex-shrink-0">⚠</span>{area}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Suggested tests */}
      {data.suggested_tests.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-3">💡 Suggested Tests</h3>
          <div className="space-y-3">
            {data.suggested_tests.map((t, i) => (
              <div key={i} className="rounded-xl p-4 bg-slate-900/50 border border-slate-700/40">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="text-sm font-semibold text-slate-100 font-mono">{t.name}</span>
                  <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${TYPE_COLOR[t.type] ?? 'bg-slate-600/40 text-slate-300'}`}>
                    {t.type}
                  </span>
                  <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${PRI_COLOR[t.priority] ?? 'bg-slate-600/40 text-slate-300'}`}>
                    {t.priority}
                  </span>
                </div>
                <p className="text-sm text-slate-400">{t.description}</p>
                {t.target_file && (
                  <p className="mt-1 text-xs text-slate-600 font-mono">📁 {t.target_file}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-xl bg-slate-900/50 border border-slate-700/30 p-3 text-center">
      <div className={`text-xl font-black ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-0.5">{label}</div>
    </div>
  );
}
