import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  Hammer, Sparkles, Zap, ShieldCheck, ShieldAlert, FileCode2,
  ChevronRight, ChevronDown, GitPullRequest, AlertTriangle, Check, Loader2, XCircle,
} from 'lucide-react';
import { api } from '../lib/api';
import type {
  GitHubRepo, Opportunity, BuildPlanResponse, BuildExecuteResponse,
} from '../types';

interface Props {
  selectedRepo: GitHubRepo | null;
  selectedBranch: string;
  accessToken: string | null;
}

// Persist discovered plans across tab switches / reloads (complaint: switching
// tabs nuked everything and forced a full re-run). Keyed by repo+branch so a
// different selection naturally shows its own cached plan (or none). sessionScope
// (not localStorage) so it clears when the tab closes — plans are ephemeral.
const SS_PREFIX = 'shipmate.build.plan.';
function ssKey(repoFullName: string, branch: string) {
  return `${SS_PREFIX}${repoFullName}@${branch}`;
}
function loadCachedPlan(repoFullName: string, branch: string): BuildPlanResponse | null {
  try {
    const raw = sessionStorage.getItem(ssKey(repoFullName, branch));
    return raw ? (JSON.parse(raw) as BuildPlanResponse) : null;
  } catch { return null; }
}
function saveCachedPlan(repoFullName: string, branch: string, plan: BuildPlanResponse | null) {
  try {
    const k = ssKey(repoFullName, branch);
    if (plan) sessionStorage.setItem(k, JSON.stringify(plan));
    else sessionStorage.removeItem(k);
  } catch { /* sessionStorage full / unavailable — non-fatal */ }
}

const CAT_TONE: Record<string, string> = {
  feature: 'purple', improvement: 'cyan', tweak: 'blue', bug: 'red',
};
const PRIO_TONE: Record<string, string> = {
  critical: 'red', high: 'amber', medium: 'blue', low: 'slate',
};

function scoreHex(v: number): string {
  if (v >= 72) return '#ef4444';   // critical band uses warm = "do this"
  if (v >= 55) return '#f59e0b';
  if (v >= 38) return '#3b82f6';
  return '#6f7d97';
}

export function BuildPage({ selectedRepo, selectedBranch, accessToken }: Props) {
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState<BuildPlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  // Per-opportunity execute/preview state.
  const [busyId, setBusyId] = useState<string | null>(null);
  const [execResult, setExecResult] = useState<Record<string, BuildExecuteResponse>>({});
  // Opportunity ids the user dismissed this session (hidden immediately).
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const repoKey = selectedRepo?.full_name ?? '';

  // Rehydrate the cached plan whenever the repo/branch selection changes (incl.
  // first mount after a tab switch). This is what makes the plan survive
  // navigation without re-running discovery.
  useEffect(() => {
    if (!repoKey) { setPlan(null); return; }
    setPlan(loadCachedPlan(repoKey, selectedBranch));
    setExecResult({});
    setDismissed(new Set());
    setExpanded(null);
    setError(null);
  }, [repoKey, selectedBranch]);

  // Persist whenever the plan changes (discovery result or cleared).
  const lastSaved = useRef<string>('');
  useEffect(() => {
    if (!repoKey) return;
    const sig = plan ? plan.generated_at : '';
    if (sig === lastSaved.current) return;
    lastSaved.current = sig;
    saveCachedPlan(repoKey, selectedBranch, plan);
  }, [plan, repoKey, selectedBranch]);

  async function discover() {
    if (!selectedRepo || !accessToken) return;
    const [owner, repo] = selectedRepo.full_name.split('/');
    setLoading(true); setError(null); setPlan(null); setExecResult({}); setDismissed(new Set());
    try {
      const res = await api.buildPlan({
        owner, repo, branch: selectedBranch, access_token: accessToken,
        max_opportunities: 8,
      });
      setPlan(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to discover opportunities');
    } finally {
      setLoading(false);
    }
  }

  async function dismiss(opp: Opportunity) {
    if (!selectedRepo || !accessToken) return;
    const [owner, repo] = selectedRepo.full_name.split('/');
    // Hide immediately (optimistic) — the journal write makes it stick across runs.
    setDismissed(prev => new Set(prev).add(opp.id));
    try {
      await api.buildDismiss({
        owner, repo, access_token: accessToken,
        title: opp.title, file: opp.target_files[0] ?? null,
      });
    } catch {
      // Roll back the optimistic hide on failure.
      setDismissed(prev => { const n = new Set(prev); n.delete(opp.id); return n; });
    }
  }

  async function runOpportunity(opp: Opportunity, execute: boolean) {
    if (!selectedRepo || !accessToken) return;
    const [owner, repo] = selectedRepo.full_name.split('/');
    setBusyId(opp.id);
    try {
      const res = await api.buildExecute({
        owner, repo, branch: selectedBranch, access_token: accessToken,
        opportunity: opp, execute,
      });
      setExecResult(prev => ({ ...prev, [opp.id]: res }));
      setExpanded(opp.id);
    } catch (e: unknown) {
      setExecResult(prev => ({
        ...prev,
        [opp.id]: {
          owner, repo, branch: selectedBranch, opportunity_id: opp.id,
          executed: execute, files_changed: [], status: 'execute_failed', ai_enhanced: true,
          generated_at: '', summary: e instanceof Error ? e.message : 'request failed',
        } as BuildExecuteResponse,
      }));
      setExpanded(opp.id);
    } finally {
      setBusyId(null);
    }
  }

  if (!selectedRepo) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '80vh', textAlign: 'center', padding: 24 }}>
        <Hammer size={42} style={{ color: 'var(--ink-3)', marginBottom: 16 }} />
        <h2 style={{ fontSize: 20, fontWeight: 800, color: '#fff', margin: '0 0 8px' }}>No repository selected</h2>
        <p style={{ fontSize: 14, color: 'var(--ink-3)' }}>Pick a repo to discover what to build next.</p>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: [0.2,0.7,0.2,1] }}
      style={{ padding: '28px 32px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h1 style={{ fontSize: 25, fontWeight: 840, margin: 0, letterSpacing: '-0.025em', color: '#fff' }}>Build</h1>
            <span className="chip tone-purple"><Sparkles size={12} /> Opportunity Planner</span>
          </div>
          <p className="muted" style={{ fontSize: 14, margin: '5px 0 0' }}>
            What should we build next in <span className="mono" style={{ color: 'var(--ink-2)' }}>{selectedRepo.name}</span> @ {selectedBranch}?
          </p>
        </div>
        <button className="btn btn-primary" onClick={discover} disabled={loading}>
          {loading ? <><Loader2 size={15} className="spin" /> Discovering…</> : <><Zap size={15} /> Discover Opportunities</>}
        </button>
      </div>

      {error && (
        <div className="card" style={{ padding: 14, marginBottom: 16, borderColor: 'rgba(239,68,68,0.3)', display: 'flex', gap: 10, alignItems: 'center' }}>
          <AlertTriangle size={16} style={{ color: '#ef4444' }} />
          <span style={{ fontSize: 13, color: 'var(--ink-2)' }}>{error}</span>
        </div>
      )}

      {/* Empty / loading states */}
      {!plan && !loading && (
        <div className="card grid-bg" style={{ padding: 48, textAlign: 'center' }}>
          <Hammer size={36} style={{ color: 'var(--purple)', marginBottom: 14 }} />
          <h3 style={{ fontSize: 17, fontWeight: 800, color: '#fff', margin: '0 0 6px' }}>Find self-improvement work</h3>
          <p className="muted" style={{ fontSize: 13.5, maxWidth: 520, margin: '0 auto 4px' }}>
            ShipMate reads the repo's code and proposes grounded, ranked opportunities —
            features, improvements, tweaks, and bugs — each cited against real files.
            Pick one to generate a step-by-step plan; optionally let the Coder open a PR.
          </p>
        </div>
      )}

      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[1,2,3,4].map(i => <div key={i} className="skel" style={{ height: 96, borderRadius: 16 }} />)}
        </div>
      )}

      {/* Results */}
      {plan && !loading && (
        <>
          {/* Summary strip */}
          <div className="card" style={{ display: 'flex', gap: 24, flexWrap: 'wrap', padding: '14px 18px', marginBottom: 16 }}>
            <Stat label="Discovered" value={plan.total_found} />
            <Stat label="Grounded" value={`${plan.grounded_count}/${plan.total_found}`} tone="emerald" />
            <Stat label="Verified" value={plan.verified_count} tone="cyan" />
            <Stat label="Shown" value={plan.opportunities.length} tone="purple" />
            {!plan.ai_enhanced && (
              <span className="chip tone-amber" style={{ marginLeft: 'auto', alignSelf: 'center' }}>
                <ShieldAlert size={12} /> Heuristic-only (LLM unavailable)
              </span>
            )}
          </div>

          {plan.opportunities.length === 0 ? (
            <div className="card" style={{ padding: 40, textAlign: 'center' }}>
              <ShieldCheck size={28} style={{ color: 'var(--emerald)', marginBottom: 10 }} />
              <p style={{ fontSize: 14, color: 'var(--ink-2)', margin: 0 }}>
                No grounded, not-already-built opportunities surfaced this run.
              </p>
              {!plan.ai_enhanced && (
                <p className="muted" style={{ fontSize: 12.5, marginTop: 6 }}>
                  The LLM provider was unavailable — refresh credentials and retry.
                </p>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {plan.opportunities.filter(o => !dismissed.has(o.id)).map(opp => (
                <OpportunityCard
                  key={opp.id}
                  opp={opp}
                  open={expanded === opp.id}
                  onToggle={() => setExpanded(e => e === opp.id ? null : opp.id)}
                  busy={busyId === opp.id}
                  result={execResult[opp.id]}
                  onPlan={() => runOpportunity(opp, false)}
                  onBuild={() => runOpportunity(opp, true)}
                  onDismiss={() => dismiss(opp)}
                />
              ))}
              {plan.opportunities.length > 0 && plan.opportunities.every(o => dismissed.has(o.id)) && (
                <div className="card" style={{ padding: 24, textAlign: 'center' }}>
                  <span className="muted" style={{ fontSize: 13 }}>
                    All opportunities dismissed. Run Discover again for fresh ones —
                    dismissed items won't come back.
                  </span>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </motion.div>
  );
}

function Stat({ label, value, tone = 'slate' }: { label: string; value: number | string; tone?: string }) {
  const hex: Record<string, string> = { slate: '#aeb9cf', emerald: '#10b981', cyan: '#22d3ee', purple: '#8b5cf6' };
  return (
    <div>
      <div style={{ fontSize: 20, fontWeight: 820, color: hex[tone] ?? '#fff', lineHeight: 1 }}>{value}</div>
      <div className="eyebrow" style={{ marginTop: 4 }}>{label}</div>
    </div>
  );
}

function OpportunityCard({
  opp, open, onToggle, busy, result, onPlan, onBuild, onDismiss,
}: {
  opp: Opportunity;
  open: boolean;
  onToggle: () => void;
  busy: boolean;
  result?: BuildExecuteResponse;
  onPlan: () => void;
  onBuild: () => void;
  onDismiss: () => void;
}) {
  const sHex = scoreHex(opp.value_score);
  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', borderColor: open ? 'var(--line-2)' : 'var(--line)' }}>
      {/* Row */}
      <button onClick={onToggle} style={{
        width: '100%', display: 'flex', alignItems: 'center', gap: 14, padding: '14px 16px',
        background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', color: 'inherit',
      }}>
        {/* Score */}
        <div style={{ width: 46, height: 46, borderRadius: 12, flexShrink: 0, display: 'grid', placeItems: 'center', background: `${sHex}18`, border: `1px solid ${sHex}55` }}>
          <span style={{ fontSize: 16, fontWeight: 820, color: sHex }}>{opp.value_score}</span>
        </div>
        {/* Title + chips */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 14.5, fontWeight: 700, color: '#fff' }}>{opp.title}</span>
            <span className={`chip tone-${CAT_TONE[opp.category] ?? 'slate'}`}>{opp.category}</span>
            <span className={`pill tone-${PRIO_TONE[opp.priority] ?? 'slate'}`}>{opp.priority}</span>
            {opp.journal_state && <span className="chip tone-amber">{opp.journal_state}</span>}
          </div>
          <div className="muted" style={{ fontSize: 12.5, marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {opp.impact}
          </div>
        </div>
        {/* Effort + chevron */}
        <span className="chip tone-slate" style={{ flexShrink: 0 }}>{opp.effort} · {opp.estimated_days}d</span>
        {open ? <ChevronDown size={18} style={{ color: 'var(--ink-3)', flexShrink: 0 }} /> : <ChevronRight size={18} style={{ color: 'var(--ink-3)', flexShrink: 0 }} />}
      </button>

      {/* Expanded body */}
      {open && (
        <div style={{ padding: '0 16px 16px', borderTop: '1px solid var(--line)' }}>
          <p style={{ fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.6, margin: '14px 0 12px' }}>{opp.description}</p>

          {opp.target_files.length > 0 && (
            <Section label="Target files" icon={FileCode2}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {opp.target_files.map(f => <span key={f} className="chip tone-blue mono" style={{ fontSize: 11 }}>{f}</span>)}
              </div>
            </Section>
          )}

          {opp.suggested_approach.length > 0 && (
            <Section label="Suggested approach">
              <ol style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.7 }}>
                {opp.suggested_approach.map((s, i) => <li key={i}>{s}</li>)}
              </ol>
            </Section>
          )}

          {opp.evidence.length > 0 && (
            <Section label="Evidence (grounded in code)" icon={ShieldCheck}>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: 'var(--ink-3)', lineHeight: 1.7 }}>
                {opp.evidence.map((e, i) => <li key={i} className="mono">{e}</li>)}
              </ul>
            </Section>
          )}

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, marginTop: 16, alignItems: 'center' }}>
            <button className="btn btn-secondary btn-sm" onClick={onPlan} disabled={busy}>
              {busy ? <Loader2 size={13} className="spin" /> : <Sparkles size={13} />} Preview Plan
            </button>
            <button className="btn btn-primary btn-sm" onClick={onBuild} disabled={busy}
              title="Plan, critique, and — if the critic approves — open a PR per step">
              {busy ? <Loader2 size={13} className="spin" /> : <GitPullRequest size={13} />} Build It
            </button>
            <button className="btn btn-ghost btn-sm" onClick={onDismiss} disabled={busy}
              style={{ marginLeft: 'auto', color: 'var(--ink-3)' }}
              title="Hide this and never propose it again (recorded in the journal)">
              <XCircle size={13} /> Dismiss
            </button>
          </div>

          {/* Plan / execute result */}
          {result && <ExecResult result={result} />}
        </div>
      )}
    </div>
  );
}

function Section({ label, icon: Icon, children }: { label: string; icon?: React.ElementType; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="eyebrow" style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 7 }}>
        {Icon && <Icon size={12} />} {label}
      </div>
      {children}
    </div>
  );
}

function ExecResult({ result }: { result: BuildExecuteResponse }) {
  const crit = result.critique;
  const approved = crit?.approved;
  const statusTone =
    result.status === 'executed' ? 'emerald'
    : result.status === 'plan_rejected' ? 'amber'
    : result.status === 'execute_failed' ? 'red'
    : 'blue';

  return (
    <div className="card" style={{ marginTop: 14, padding: 14, background: 'rgba(0,0,0,0.22)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span className={`chip tone-${statusTone}`}>{result.status}</span>
        {crit && (
          <span className={`chip tone-${approved ? 'emerald' : 'red'}`}>
            {approved ? <Check size={12} /> : <ShieldAlert size={12} />} critic: {approved ? 'approved' : 'rejected'}
          </span>
        )}
        {result.pr_url && (
          <a href={result.pr_url} target="_blank" rel="noreferrer" className="chip tone-blue" style={{ marginLeft: 'auto', textDecoration: 'none' }}>
            <GitPullRequest size={12} /> View PR →
          </a>
        )}
      </div>

      <p style={{ fontSize: 13, color: 'var(--ink-2)', margin: '0 0 10px', lineHeight: 1.55 }}>{result.summary}</p>

      {crit && !approved && crit.issues.length > 0 && (
        <ul style={{ margin: '0 0 10px', paddingLeft: 18, fontSize: 12, color: '#fca5a5', lineHeight: 1.6 }}>
          {crit.issues.map((iss, i) => <li key={i}>{iss}</li>)}
        </ul>
      )}

      {result.plan && result.plan.steps.length > 0 && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 8 }}>Plan · {result.plan.steps.length} steps</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {result.plan.steps.map(s => (
              <div key={s.index} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <span style={{ width: 22, height: 22, borderRadius: 7, flexShrink: 0, display: 'grid', placeItems: 'center', background: 'var(--blue)18', border: '1px solid var(--line-2)', fontSize: 11, fontWeight: 800, color: 'var(--blue-2)' }}>{s.index}</span>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 650, color: '#fff' }}>
                    {s.title}
                    {s.depends_on.length > 0 && <span className="muted" style={{ fontWeight: 400, fontSize: 11 }}> · after {s.depends_on.join(', ')}</span>}
                  </div>
                  <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>{s.description}</div>
                  {s.target_files.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 5 }}>
                      {s.target_files.map(f => <span key={f} className="mono" style={{ fontSize: 10.5, color: 'var(--ink-3)' }}>{f}</span>)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {result.files_changed.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="eyebrow" style={{ marginBottom: 6 }}>Files changed</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
            {result.files_changed.map(f => <span key={f} className="chip tone-emerald mono" style={{ fontSize: 10.5 }}>{f}</span>)}
          </div>
        </div>
      )}
    </div>
  );
}
