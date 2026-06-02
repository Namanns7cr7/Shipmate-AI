import type { ShipMateReport } from '../types';

export function OverviewTab({ report }: { report: ShipMateReport }) {
  const { repo, key_blockers, next_actions, agents, score_breakdown } = report;

  return (
    <div className="space-y-5">
      {/* Repo summary */}
      <div className="rounded-xl bg-slate-900/50 border border-slate-700/30 p-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">📦</span>
          <div>
            <a
              href={repo.html_url}
              target="_blank"
              rel="noreferrer"
              className="text-base font-bold text-blue-300 hover:underline"
            >
              {repo.full_name}
            </a>
            <div className="flex gap-3 text-xs text-slate-400 mt-0.5">
              <span>🌿 {repo.branch}</span>
              {repo.language && <span>💻 {repo.language}</span>}
              <span>⭐ {repo.stars}</span>
              <span>📁 {repo.file_count} files</span>
            </div>
            {repo.description && <p className="text-xs text-slate-500 mt-1">{repo.description}</p>}
          </div>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Repo',     val: score_breakdown.repo_score,     icon: '🔍' },
          { label: 'Delivery', val: score_breakdown.delivery_score, icon: '📋' },
          { label: 'Security', val: score_breakdown.security_score, icon: '🔒' },
          { label: 'Tests',    val: score_breakdown.test_score,     icon: '🧪' },
        ].map(({ label, val, icon }) => (
          <div key={label} className="rounded-xl bg-slate-900/50 border border-slate-700/30 p-3 text-center">
            <div className="text-xl mb-1">{icon}</div>
            <div className={`text-2xl font-black ${val >= 80 ? 'text-emerald-400' : val >= 60 ? 'text-yellow-400' : val >= 40 ? 'text-orange-400' : 'text-red-400'}`}>
              {val}
            </div>
            <div className="text-xs text-slate-500">{label}</div>
          </div>
        ))}
      </div>

      {/* Quick agent summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Chip icon="🧱" label={`${agents.repo_lens.tech_stack.length} technologies detected`} />
        <Chip icon="🚧" label={`${agents.plan_forge.blockers.length} delivery blockers`} />
        <Chip icon="🔐" label={`${agents.guardrail.findings.length} security findings`} />
        <Chip icon="🧪" label={`${agents.testpilot.existing_tests.count} test files, ~${agents.testpilot.existing_tests.coverage_estimate}% coverage`} />
      </div>

      {/* Key blockers */}
      {key_blockers.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2 flex items-center gap-2">
            🚧 Key Blockers
          </h3>
          <ul className="space-y-1.5">
            {key_blockers.map((b, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300 bg-red-950/20 border border-red-500/15 rounded-lg px-3 py-2">
                <span className="text-red-400 mt-0.5 flex-shrink-0">⛔</span>
                {b}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Next actions */}
      {next_actions.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">⚡ Next Actions</h3>
          <ol className="space-y-1.5">
            {next_actions.map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300 bg-blue-950/20 border border-blue-500/15 rounded-lg px-3 py-2">
                <span className="text-blue-400 font-bold flex-shrink-0">{i + 1}.</span>
                {a}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function Chip({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900/40 border border-slate-700/30 text-sm text-slate-300">
      <span>{icon}</span>
      <span>{label}</span>
    </div>
  );
}
