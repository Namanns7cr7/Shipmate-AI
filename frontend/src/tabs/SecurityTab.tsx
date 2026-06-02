import type { GuardRailOutput } from '../types';
import { RiskCard } from '../components/RiskCard';

export function SecurityTab({ data }: { data: GuardRailOutput }) {
  const critical = data.findings.filter(f => f.severity === 'critical');
  const high     = data.findings.filter(f => f.severity === 'high');
  const medium   = data.findings.filter(f => f.severity === 'medium');
  const low      = data.findings.filter(f => f.severity === 'low' || f.severity === 'info');

  return (
    <div className="space-y-6">
      {/* Score + summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatBox label="Security Score" value={`${data.security_score}/100`}
          color={data.security_score >= 80 ? 'text-emerald-400' : data.security_score >= 60 ? 'text-yellow-400' : 'text-red-400'} />
        <StatBox label="Critical" value={String(critical.length)} color={critical.length > 0 ? 'text-red-400' : 'text-emerald-400'} />
        <StatBox label="High" value={String(high.length)} color={high.length > 0 ? 'text-orange-400' : 'text-emerald-400'} />
        <StatBox label="Medium / Low" value={String(medium.length + low.length)} color="text-yellow-400" />
      </div>

      {/* Exposed secrets */}
      {data.exposed_secrets.length > 0 && (
        <div className="rounded-xl bg-red-950/30 border border-red-500/30 px-4 py-3">
          <p className="text-xs font-bold text-red-400 mb-2">🔑 EXPOSED SECRETS DETECTED</p>
          <ul className="space-y-1">
            {data.exposed_secrets.map((s, i) => (
              <li key={i} className="text-sm text-red-300 flex items-start gap-2">
                <span className="flex-shrink-0">•</span>{s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* All findings */}
      {data.findings.length === 0 ? (
        <div className="rounded-xl bg-emerald-950/20 border border-emerald-500/20 px-4 py-6 text-center">
          <p className="text-3xl mb-2">✅</p>
          <p className="text-sm font-semibold text-emerald-400">No security findings detected</p>
          <p className="text-xs text-slate-500 mt-1">The codebase passed all automated security checks.</p>
        </div>
      ) : (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-3">🔒 Findings ({data.findings.length})</h3>
          <div className="space-y-3">
            {data.findings.map(f => <RiskCard key={f.id} finding={f} />)}
          </div>
        </div>
      )}

      {/* CORS issues */}
      {data.cors_issues.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">🌐 CORS Issues</h3>
          <ul className="space-y-1">
            {data.cors_issues.map((c, i) => (
              <li key={i} className="text-sm text-slate-400 flex items-start gap-2">
                <span className="text-orange-400">•</span>{c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Auth risks */}
      {data.auth_risks.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">🔐 Auth Risks</h3>
          <ul className="space-y-1">
            {data.auth_risks.map((r, i) => (
              <li key={i} className="text-sm text-slate-400 flex items-start gap-2">
                <span className="text-yellow-400">•</span>{r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Dep vulns */}
      {data.dependency_vulnerabilities.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-slate-300 mb-2">📦 Dependency Vulnerabilities</h3>
          <ul className="space-y-1">
            {data.dependency_vulnerabilities.map((d, i) => (
              <li key={i} className="text-sm text-slate-400 flex items-start gap-2">
                <span className="text-orange-400">•</span>{d}
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
      <div className={`text-xl font-black ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-0.5">{label}</div>
    </div>
  );
}
