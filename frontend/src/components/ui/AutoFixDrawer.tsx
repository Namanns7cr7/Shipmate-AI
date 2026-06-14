import { useEffect, useRef, useState } from 'react';
import {
  X, Loader2, CheckCircle2, XCircle, Sparkles, Search, GitPullRequest, Ban,
} from 'lucide-react';
import { api } from '../../lib/api';
import { CIWatchPanel } from './CIWatchPanel';
import type { AutoFixEvent } from '../../types';

/**
 * AutoFixDrawer — slide-in panel that drives the server-side autonomous loop
 * (POST /api/auto-fix/start, SSE) and renders a live activity feed: one card
 * per picked finding moving picked → coding → pytest → pr → done|failed, plus
 * an embedded CIWatchPanel for any finding that opened a PR.
 *
 * The same gates run server-side as the per-finding Apply-Fix button — this is
 * just the multi-finding, hands-off surface.
 */

const PR_NUM_RE = /\/pull\/(\d+)/;

type FindingStatus = 'coding' | 'shipped' | 'rejected' | 'error';

interface FindingCard {
  signature: string;
  kind: string;
  title: string;
  status: FindingStatus;
  detail?: string;
  prUrl?: string | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  owner: string;
  repo: string;
  branch: string;
  accessToken: string | null;
}

const KIND_TONE: Record<string, string> = {
  guardrail: '#f59e0b', blocker: '#ef4444', milestone: '#8b5cf6',
  test: '#22d3ee', next_action: '#60a5fa',
};

function StatusBadge({ status }: { status: FindingStatus }) {
  const map: Record<FindingStatus, { fg: string; bg: string; icon: React.ReactNode; label: string }> = {
    coding:   { fg: '#cfe1ff', bg: 'rgba(59,130,246,0.14)', icon: <Loader2 size={12} style={{ animation: 'shipmate-spin 0.8s linear infinite' }} />, label: 'Coding' },
    shipped:  { fg: '#34d399', bg: 'rgba(16,185,129,0.14)', icon: <GitPullRequest size={12} />, label: 'PR opened' },
    rejected: { fg: '#fbbf24', bg: 'rgba(245,158,11,0.14)', icon: <Ban size={12} />, label: 'Rejected by gate' },
    error:    { fg: '#fca5a5', bg: 'rgba(239,68,68,0.12)', icon: <XCircle size={12} />, label: 'Error' },
  };
  const t = map[status];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 8px',
      borderRadius: 999, fontSize: 11, fontWeight: 700, color: t.fg, background: t.bg,
    }}>
      {t.icon} {t.label}
    </span>
  );
}

export function AutoFixDrawer({ open, onClose, owner, repo, branch, accessToken }: Props) {
  const [running, setRunning] = useState(false);
  const [phase, setPhase] = useState<string>('');
  const [cards, setCards] = useState<FindingCard[]>([]);
  const [summary, setSummary] = useState<{ good: number; actuated: number; note?: string } | null>(null);
  const [error, setError] = useState<string>('');
  const abortRef = useRef<AbortController | null>(null);

  // Stop the stream if the drawer is closed mid-run.
  useEffect(() => {
    if (!open && abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
      setRunning(false);
    }
  }, [open]);

  function upsertCard(sig: string, patch: Partial<FindingCard> & Pick<FindingCard, 'kind' | 'title'>) {
    setCards(prev => {
      const i = prev.findIndex(c => c.signature === sig);
      if (i === -1) return [...prev, { signature: sig, status: 'coding', ...patch }];
      const next = [...prev];
      next[i] = { ...next[i], ...patch };
      return next;
    });
  }

  function handleEvent(e: AutoFixEvent) {
    switch (e.event) {
      case 'analyze.start': setPhase(`Analyzing (round ${e.round})…`); break;
      case 'analyze.done':  setPhase(`Round ${e.round}: ${e.picked} finding(s) picked · score ${e.score ?? '—'}`); break;
      case 'finding.picked':
        if (e.signature) upsertCard(e.signature, { kind: e.kind || '', title: e.title || '', status: 'coding' });
        break;
      case 'actuate.done': {
        const sig = e.signature || `${e.kind}::${e.title}`;
        const shipped = e.status === 'complete' && !!e.pr_url;
        upsertCard(sig, {
          kind: e.kind || '', title: e.title || '',
          status: shipped ? 'shipped' : (e.status === 'error' ? 'error' : 'rejected'),
          detail: shipped ? undefined : (e.message || e.status),
          prUrl: e.pr_url,
        });
        break;
      }
      case 'loop.done':
        setSummary({ good: e.good ?? 0, actuated: e.actuated ?? 0, note: e.note });
        setPhase('Done');
        setRunning(false);
        break;
      case 'error':
        setError(e.message || 'stream error');
        setRunning(false);
        break;
    }
  }

  async function start() {
    if (!accessToken) { setError('Not signed in to GitHub.'); return; }
    setRunning(true); setError(''); setCards([]); setSummary(null); setPhase('Starting…');
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      await api.startAutoFix(
        { owner, repo, branch, access_token: accessToken, rounds: 2 },
        handleEvent, ac.signal,
      );
    } catch (e) {
      if (!ac.signal.aborted) setError(e instanceof Error ? e.message : 'auto-fix failed');
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }

  if (!open) return null;

  return (
    <>
      {/* Scrim */}
      <div onClick={onClose} style={{
        position: 'fixed', inset: 0, background: 'rgba(3,6,14,0.55)',
        backdropFilter: 'blur(2px)', zIndex: 60,
      }} />
      {/* Drawer */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(480px, 100vw)',
        background: 'var(--bg)', borderLeft: '1px solid var(--line-2)', zIndex: 61,
        display: 'flex', flexDirection: 'column', boxShadow: '-20px 0 60px rgba(0,0,0,0.5)',
        animation: 'shipmate-drawer-in 0.22s ease',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 18px', borderBottom: '1px solid var(--line)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <span style={{
              display: 'grid', placeItems: 'center', width: 30, height: 30, borderRadius: 9,
              background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)',
            }}>
              <Sparkles size={16} color="#fff" />
            </span>
            <div>
              <div style={{ fontSize: 14, fontWeight: 800, color: '#fff' }}>Auto-fix</div>
              <div className="mono" style={{ fontSize: 11, color: 'var(--ink-3)' }}>{owner}/{repo} · {branch}</div>
            </div>
          </div>
          <button onClick={onClose} style={{ padding: 6, borderRadius: 8, background: 'none', border: 'none', color: 'var(--ink-3)', cursor: 'pointer' }}>
            <X size={18} />
          </button>
        </div>

        {/* Phase line */}
        <div style={{ padding: '10px 18px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'center', gap: 8, minHeight: 22 }}>
          {running
            ? <Loader2 size={13} style={{ animation: 'shipmate-spin 0.8s linear infinite', color: 'var(--blue-2)' }} />
            : <Search size={13} style={{ color: 'var(--ink-3)' }} />}
          <span style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>{phase || 'Idle — press Start to run the autonomous loop.'}</span>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {error && (
            <div style={{ padding: '10px 12px', borderRadius: 8, fontSize: 12.5, color: '#fca5a5', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.3)' }}>
              {error}
            </div>
          )}

          {cards.map(c => {
            const prNum = c.prUrl ? Number(c.prUrl.match(PR_NUM_RE)?.[1]) : null;
            return (
              <div key={c.signature} className="card" style={{ padding: 12 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
                  <div style={{ minWidth: 0 }}>
                    <span className="mono" style={{ fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', color: KIND_TONE[c.kind] || 'var(--ink-3)' }}>
                      {c.kind}
                    </span>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', marginTop: 2, lineHeight: 1.35 }}>
                      {c.title}
                    </div>
                  </div>
                  <StatusBadge status={c.status} />
                </div>
                {c.detail && (
                  <div style={{ marginTop: 6, fontSize: 11.5, color: 'var(--ink-3)', lineHeight: 1.4 }}>
                    {c.detail}
                  </div>
                )}
                {c.prUrl && (
                  <a href={c.prUrl} target="_blank" rel="noopener noreferrer"
                    style={{ marginTop: 6, display: 'inline-block', fontSize: 12, fontWeight: 600, color: 'var(--blue-2)' }}>
                    View PR ↗
                  </a>
                )}
                {prNum !== null && !Number.isNaN(prNum) && (
                  <CIWatchPanel owner={owner} repo={repo} prNumber={prNum} />
                )}
              </div>
            );
          })}

          {summary && (
            <div style={{
              padding: '12px 14px', borderRadius: 10, marginTop: 4,
              background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.25)',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              {summary.good > 0 ? <CheckCircle2 size={18} color="#34d399" /> : <Ban size={18} color="var(--ink-3)" />}
              <div style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>
                <strong style={{ color: '#fff' }}>{summary.good}</strong> PR(s) opened ·{' '}
                <strong style={{ color: '#fff' }}>{summary.actuated}</strong> finding(s) actuated
                {summary.note ? ` · ${summary.note}` : ''}
              </div>
            </div>
          )}

          {!running && cards.length === 0 && !error && (
            <div style={{ textAlign: 'center', color: 'var(--ink-3)', fontSize: 12.5, padding: '24px 8px', lineHeight: 1.6 }}>
              ShipMate will analyze the repo, pick the top findings, generate fixes,
              run them through the pytest gate, and open PRs for the ones that pass —
              then watch CI on each. Up to 2 rounds.
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: 14, borderTop: '1px solid var(--line)' }}>
          <button
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center' }}
            disabled={running || !accessToken}
            onClick={start}
          >
            {running ? <><Loader2 size={14} style={{ animation: 'shipmate-spin 0.8s linear infinite' }} /> Running…</> : <><Sparkles size={14} /> Start Auto-fix</>}
          </button>
        </div>
      </div>
      <style>{`
        @keyframes shipmate-spin { to { transform: rotate(360deg); } }
        @keyframes shipmate-drawer-in { from { transform: translateX(24px); opacity: 0.4; } to { transform: translateX(0); opacity: 1; } }
      `}</style>
    </>
  );
}
