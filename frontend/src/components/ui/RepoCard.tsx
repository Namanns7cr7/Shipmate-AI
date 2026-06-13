import { Lock, BookOpen, Star, GitBranch, Clock, Zap, BarChart3, AlertTriangle } from 'lucide-react';
import { ScoreRing } from './ScoreRing';
import { VerdictPill } from './VerdictPill';
import { Reveal } from './Reveal';
import { LANG_COLORS } from '../../lib/agents';
import type { GitHubRepo, ShipMateReport } from '../../types';

interface RepoCardProps {
  repo: GitHubRepo;
  report?: ShipMateReport | null;
  onAnalyze: (r: GitHubRepo) => void;
  onReport?: () => void;
  analyzing?: boolean;
  isSelected?: boolean;
  delay?: number;
}

export function RepoCard({ repo: r, report, onAnalyze, onReport, analyzing = false, isSelected = false, delay = 0 }: RepoCardProps) {
  const hasReport = !!report && report.repo.name === r.name;
  const langColor = r.language ? (LANG_COLORS[r.language] ?? '#64748b') : null;
  const riskTotal = hasReport
    ? report!.agents.guardrail.findings.filter(f => f.severity === 'critical' || f.severity === 'high').length
    : 0;

  return (
    <Reveal delay={delay}>
      <div className="card card-hover" style={{ padding: 18 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
          {/* Left: icon + info */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, minWidth: 0, flex: 1 }}>
            <div style={{
              width: 42, height: 42, borderRadius: 12, display: 'grid', placeItems: 'center', flexShrink: 0,
              background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line-2)', color: 'var(--ink-2)',
            }}>
              {r.private ? <Lock size={18} /> : <BookOpen size={18} />}
            </div>

            <div style={{ minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span className="mono" style={{ fontWeight: 700, fontSize: 14.5, color: '#fff' }}>{r.full_name}</span>
                <span className={`chip ${r.private ? 'tone-slate' : 'tone-emerald'}`}>
                  {r.private ? 'Private' : 'Public'}
                </span>
                {hasReport && <span className="dot" style={{ background: '#34d399' }} title="Analyzed" />}
              </div>
              <p className="muted" style={{ fontSize: 12.5, margin: '5px 0 0', lineHeight: 1.5 }}>
                {r.description || 'No description'}
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginTop: 10 }}>
                {r.language && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11.5, color: 'var(--ink-3)' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: langColor ?? '#64748b', flexShrink: 0 }} />
                    {r.language}
                  </span>
                )}
                {r.stargazers_count > 0 && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11.5, color: 'var(--ink-3)' }}>
                    <Star size={12} /> {r.stargazers_count}
                  </span>
                )}
                <span className="mono" style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11.5, color: 'var(--ink-3)' }}>
                  <GitBranch size={12} /> {r.default_branch}
                </span>
                {hasReport
                  ? <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11.5, color: 'var(--ink-3)' }}>
                      <Clock size={12} /> {new Date(report!.generated_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  : <span className="chip tone-slate">Not analyzed</span>
                }
              </div>
            </div>
          </div>

          {/* Right: score ring */}
          {hasReport && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0, gap: 8 }}>
              <ScoreRing value={report!.readiness_score} size={62} stroke={6} delay={delay + 200} />
              {riskTotal > 0 && (
                <span className="chip tone-red">
                  <AlertTriangle size={11} /> {riskTotal} risks
                </span>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--line)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {hasReport && <VerdictPill verdict={
              report!.ship_recommendation === 'ready_to_ship' || report!.ship_recommendation === 'mostly_ready' ? 'Ready' :
              report!.ship_recommendation === 'not_ready' || report!.ship_recommendation === 'risky_release' ? 'Blocked' : 'Needs Fixes'
            } small />}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {hasReport && onReport && (
              <button className="btn btn-ghost btn-sm" onClick={onReport}>
                <BarChart3 size={13} /> View Report
              </button>
            )}
            <button
              className="btn btn-primary btn-sm"
              onClick={() => onAnalyze(r)}
              disabled={analyzing && isSelected}
            >
              {analyzing && isSelected
                ? <><span style={{ width: 12, height: 12, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', animation: 'spin .7s linear infinite', display: 'inline-block' }} /> Analyzing…</>
                : <><Zap size={13} /> {hasReport ? 'Re-analyze' : 'Analyze'}</>
              }
            </button>
          </div>
        </div>
      </div>
    </Reveal>
  );
}
