import { useEffect, useRef, useState } from 'react';
import { Loader2, CheckCircle2, XCircle, Activity, AlertTriangle } from 'lucide-react';
import { api } from '../../lib/api';
import type { WatcherState, WatcherLogLine } from '../../types';

/**
 * CIWatchPanel — live view of the CIWatcher driving a Coder-opened PR to green.
 *
 * Mounted by ActuateButton once a PR url exists. Polls
 *   GET /api/watcher/{owner}/{repo}/{pr}            every POLL_MS
 *   GET /api/watcher/{owner}/{repo}/{pr}/log?since  (append-only tail)
 * and renders attempts/N, a status badge, and the terminal-style log tail.
 * Stops polling once the watcher reaches a terminal state (passed/gave_up/crashed)
 * or after the PR 404s (watcher never registered / already cleaned up).
 */

const POLL_MS = 12_000;

type Tone = { fg: string; bg: string; border: string };

const STATUS_TONE: Record<WatcherState['status'], Tone> = {
  watching: { fg: '#cfe1ff', bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.35)' },
  fixing:   { fg: '#fbbf24', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.35)' },
  passed:   { fg: '#34d399', bg: 'rgba(16,185,129,0.14)', border: 'rgba(16,185,129,0.4)' },
  gave_up:  { fg: '#fca5a5', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.4)' },
  crashed:  { fg: '#fca5a5', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.4)' },
};

const LEVEL_FG: Record<WatcherLogLine['level'], string> = {
  info: 'var(--ink-2)', warn: '#fbbf24', error: '#fca5a5',
};

function StatusIcon({ status }: { status: WatcherState['status'] }) {
  if (status === 'passed') return <CheckCircle2 size={13} />;
  if (status === 'gave_up' || status === 'crashed') return <XCircle size={13} />;
  if (status === 'fixing') return <Loader2 size={13} style={{ animation: 'shipmate-spin 0.8s linear infinite' }} />;
  return <Activity size={13} />;
}

const TERMINAL = new Set<WatcherState['status']>(['passed', 'gave_up', 'crashed']);

interface Props {
  owner: string;
  repo: string;
  prNumber: number;
}

export function CIWatchPanel({ owner, repo, prNumber }: Props) {
  const [state, setState] = useState<WatcherState | null>(null);
  const [lines, setLines] = useState<WatcherLogLine[]>([]);
  const [notFound, setNotFound] = useState(false);
  const sinceRef = useRef(0);
  const logBoxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;

    async function tick() {
      try {
        const s = await api.getWatcher(owner, repo, prNumber);
        if (!alive) return;
        if (s === null) {
          // Watcher not registered for this PR (or cleaned up). Show a hint
          // and stop polling — nothing will appear.
          setNotFound(true);
          return;
        }
        setNotFound(false);
        setState(s);

        const tail = await api.getWatcherLog(owner, repo, prNumber, sinceRef.current);
        if (!alive) return;
        if (tail.lines.length) {
          sinceRef.current = tail.next_id;
          setLines(prev => [...prev, ...tail.lines]);
        }

        if (!TERMINAL.has(s.status)) {
          timer = setTimeout(tick, POLL_MS);
        }
      } catch {
        // transient — back off one interval and retry
        if (alive) timer = setTimeout(tick, POLL_MS);
      }
    }

    tick();
    return () => { alive = false; clearTimeout(timer); };
  }, [owner, repo, prNumber]);

  // Autoscroll the log tail.
  useEffect(() => {
    if (logBoxRef.current) logBoxRef.current.scrollTop = logBoxRef.current.scrollHeight;
  }, [lines]);

  if (notFound && !state) {
    return (
      <div style={{
        marginTop: 8, padding: '8px 10px', borderRadius: 8, fontSize: 11.5,
        color: 'var(--ink-3)', background: 'rgba(255,255,255,0.03)',
        border: '1px solid var(--line)', display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <AlertTriangle size={12} /> No CI watcher is tracking this PR (CI may not be configured).
      </div>
    );
  }

  if (!state) {
    return (
      <div style={{ marginTop: 8, fontSize: 11.5, color: 'var(--ink-3)', display: 'flex', alignItems: 'center', gap: 6 }}>
        <Loader2 size={12} style={{ animation: 'shipmate-spin 0.8s linear infinite' }} /> Connecting to CI watcher…
      </div>
    );
  }

  const tone = STATUS_TONE[state.status];
  const label: Record<WatcherState['status'], string> = {
    watching: 'Watching CI', fixing: 'Auto-fixing', passed: 'CI passed',
    gave_up: 'Gave up', crashed: 'Watcher crashed',
  };

  return (
    <div style={{
      marginTop: 8, borderRadius: 10, overflow: 'hidden',
      border: `1px solid ${tone.border}`, background: 'rgba(0,0,0,0.18)', maxWidth: 420,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: 8, padding: '7px 10px', background: tone.bg, borderBottom: `1px solid ${tone.border}`,
      }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, color: tone.fg }}>
          <StatusIcon status={state.status} /> {label[state.status]}
        </span>
        <span className="mono" style={{ fontSize: 11, color: tone.fg, opacity: 0.85 }}>
          attempt {state.attempts}/{state.max_attempts}
        </span>
      </div>

      {state.last_error && (
        <div style={{ padding: '5px 10px', fontSize: 11, color: '#fca5a5', background: 'rgba(239,68,68,0.06)' }}>
          {state.last_error}
        </div>
      )}

      <div ref={logBoxRef} className="mono" style={{
        maxHeight: 150, overflowY: 'auto', padding: '8px 10px',
        fontSize: 11, lineHeight: 1.7,
      }}>
        {lines.length === 0 ? (
          <span style={{ color: 'var(--ink-4)' }}>waiting for CI events…</span>
        ) : lines.map(l => (
          <div key={l.id} style={{ display: 'flex', gap: 6, alignItems: 'baseline' }}>
            <span style={{ color: 'var(--ink-4)', flexShrink: 0 }}>
              {new Date(l.ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
            <span style={{ color: LEVEL_FG[l.level] }}>{l.msg}</span>
          </div>
        ))}
      </div>
      <style>{`@keyframes shipmate-spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
