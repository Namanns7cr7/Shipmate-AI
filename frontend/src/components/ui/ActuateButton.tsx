import { useState } from 'react';
import { Wand2, Loader2, ExternalLink, AlertCircle, Check, ChevronDown, ChevronUp, Copy } from 'lucide-react';
import { api } from '../../lib/api';
import type {
  FindingPayload, RepoLensSummary, ActuateResponse,
} from '../../types';

type Status = 'idle' | 'running' | 'done' | 'error' | 'no_change';

interface Props {
  owner: string;
  repo: string;
  branch: string;
  accessToken: string | null;
  finding: FindingPayload;
  context?: RepoLensSummary;
  label?: string;
  size?: 'sm' | 'md';
}

const SIZE_PADDING: Record<NonNullable<Props['size']>, string> = {
  sm: '6px 11px',
  md: '8px 14px',
};
const SIZE_FONT: Record<NonNullable<Props['size']>, number> = {
  sm: 12,
  md: 13,
};

// All button states share these so text never wraps inside narrow card slots.
const PILL_BASE: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  borderRadius: 8,
  fontWeight: 700,
  whiteSpace: 'nowrap',
  flexShrink: 0,
  cursor: 'pointer',
  textDecoration: 'none',
  lineHeight: 1.1,
};

export function ActuateButton({
  owner, repo, branch, accessToken, finding, context, label = 'Apply Fix', size = 'sm',
}: Props) {
  const [status, setStatus] = useState<Status>('idle');
  const [response, setResponse] = useState<ActuateResponse | null>(null);
  const [errMsg, setErrMsg] = useState<string>('');
  const [errorExpanded, setErrorExpanded] = useState(false);

  const padding = SIZE_PADDING[size];
  const font = SIZE_FONT[size];

  async function run() {
    if (!accessToken) {
      setErrMsg('Not signed in to GitHub. Reconnect from the sidebar.');
      setStatus('error');
      setErrorExpanded(false);
      return;
    }
    setStatus('running');
    setErrMsg('');
    setErrorExpanded(false);
    try {
      const res = await api.actuate({
        owner, repo, branch, access_token: accessToken,
        finding, context, open_pr: true,
      });
      setResponse(res);
      setStatus(res.status === 'no_change' ? 'no_change' : 'done');
    } catch (e: unknown) {
      let msg = 'Coder failed';
      if (e && typeof e === 'object' && 'response' in e) {
        const er = e as { response?: { data?: { detail?: string } }; message?: string };
        msg = er.response?.data?.detail || er.message || msg;
      } else if (e instanceof Error) {
        msg = e.message;
      }
      setErrMsg(msg);
      setStatus('error');
    }
  }

  // ── DONE — green pill, links to the PR ─────────────────────────────────
  if (status === 'done' && response?.pr_url) {
    return (
      <a
        href={response.pr_url}
        target="_blank"
        rel="noopener noreferrer"
        style={{
          ...PILL_BASE,
          padding, fontSize: font,
          color: '#0b1220',
          background: 'linear-gradient(135deg,#34d399,#10b981)',
          border: '1px solid #10b981',
          boxShadow: '0 4px 14px rgba(16,185,129,0.25)',
        }}
      >
        <Check size={font} /> View PR <ExternalLink size={font - 2} />
      </a>
    );
  }

  // ── NO CHANGE — neutral pill ──────────────────────────────────────────
  if (status === 'no_change') {
    return (
      <span style={{
        ...PILL_BASE,
        padding, fontSize: font, fontWeight: 600, cursor: 'default',
        color: 'var(--ink-2)', background: 'rgba(255,255,255,0.04)',
        border: '1px solid var(--line)',
      }}>
        <Check size={font} /> No change needed
      </span>
    );
  }

  // ── ERROR — compact retry button + expandable detail panel BELOW ──────
  if (status === 'error') {
    const friendly = friendlyError(errMsg);
    return (
      <span style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6, maxWidth: '100%' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <button
            onClick={run}
            title="Retry"
            style={{
              ...PILL_BASE,
              padding, fontSize: font,
              color: '#fca5a5', background: 'rgba(239,68,68,0.12)',
              border: '1px solid rgba(239,68,68,0.45)',
            }}
          >
            <AlertCircle size={font} /> Retry
          </button>
          <button
            onClick={() => setErrorExpanded(v => !v)}
            title={errorExpanded ? 'Hide error details' : 'Show error details'}
            aria-label="Toggle error details"
            style={{
              ...PILL_BASE,
              padding: '6px 8px', fontSize: font,
              color: '#fca5a5', background: 'rgba(239,68,68,0.06)',
              border: '1px solid rgba(239,68,68,0.25)',
            }}
          >
            {errorExpanded ? <ChevronUp size={font} /> : <ChevronDown size={font} />}
          </button>
        </span>
        {errorExpanded && (
          <div style={{
            display: 'flex', flexDirection: 'column', gap: 6,
            padding: '10px 12px', borderRadius: 8,
            background: 'rgba(239,68,68,0.07)',
            border: '1px solid rgba(239,68,68,0.25)',
            maxWidth: 360, width: '100%',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#fca5a5', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                {friendly.title}
              </span>
              <button
                onClick={() => navigator.clipboard?.writeText(errMsg)}
                title="Copy full error"
                aria-label="Copy error to clipboard"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  padding: '2px 6px', borderRadius: 6, fontSize: 10, fontWeight: 600,
                  color: '#fca5a5', background: 'transparent',
                  border: '1px solid rgba(239,68,68,0.3)', cursor: 'pointer',
                }}
              >
                <Copy size={10} /> copy
              </button>
            </div>
            {friendly.hint && (
              <span style={{ fontSize: 12, color: 'var(--ink-2)', lineHeight: 1.45 }}>
                {friendly.hint}
              </span>
            )}
            <pre style={{
              margin: 0, padding: '6px 8px', borderRadius: 6,
              fontSize: 10.5, lineHeight: 1.4, color: '#fca5a5',
              background: 'rgba(0,0,0,0.25)',
              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              maxHeight: 140, overflow: 'auto',
              fontFamily: 'JetBrains Mono, ui-monospace, monospace',
            }}>{errMsg}</pre>
          </div>
        )}
      </span>
    );
  }

  // ── RUNNING — short label so it fits in 240px milestone cards ─────────
  if (status === 'running') {
    return (
      <span style={{
        ...PILL_BASE,
        padding, fontSize: font, cursor: 'progress',
        color: '#cfe1ff', background: 'rgba(59,130,246,0.12)',
        border: '1px solid rgba(59,130,246,0.35)',
      }}>
        <Loader2 size={font} style={{ animation: 'shipmate-spin 0.8s linear infinite' }} />
        Working…
      </span>
    );
  }

  // ── IDLE — primary button ─────────────────────────────────────────────
  return (
    <>
      <button
        onClick={run}
        disabled={!accessToken}
        style={{
          ...PILL_BASE,
          padding, fontSize: font,
          color: '#fff',
          background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)',
          border: '1px solid rgba(255,255,255,0.1)',
          cursor: accessToken ? 'pointer' : 'not-allowed',
          opacity: accessToken ? 1 : 0.5,
          boxShadow: '0 4px 14px rgba(59,130,246,0.25)',
        }}
      >
        <Wand2 size={font} /> {label}
      </button>
      <style>{`@keyframes shipmate-spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}

/** Map common backend errors to a short title + hint. Falls back to generic. */
function friendlyError(msg: string): { title: string; hint: string | null } {
  const m = msg.toLowerCase();
  if (m.includes('workflow` scope') || m.includes("'workflow' scope")
      || (m.includes('.github/workflows/') && m.includes('404'))) {
    return {
      title: 'GitHub workflow scope missing',
      hint: 'GitHub blocks writes under .github/workflows/ unless your OAuth token has the `workflow` scope. Sign out + reconnect GitHub from the sidebar to re-grant scopes, then retry.',
    };
  }
  if (m.includes('expiredtoken') || m.includes('security token included in the request is expired')) {
    return {
      title: 'AWS credentials expired',
      hint: 'Refresh ADA credentials and restart the backend, then retry.',
    };
  }
  if (m.includes('401') || m.includes('unauthorized')) {
    return {
      title: 'GitHub auth rejected',
      hint: 'Reconnect GitHub from the sidebar — your token may have been revoked.',
    };
  }
  if (m.includes('403') || m.includes('forbidden')) {
    return {
      title: 'GitHub permissions denied',
      hint: 'The OAuth app may need broader scopes, or the repo is protected.',
    };
  }
  if (m.includes('502') || m.includes('github')) {
    return {
      title: 'GitHub API error',
      hint: 'GitHub rejected the request. Inspect the full error below for the exact reason.',
    };
  }
  if (m.includes('timeout') || m.includes('etimedout')) {
    return {
      title: 'Coder timed out',
      hint: 'The Bedrock call exceeded 120s. Retry, or scope the change to fewer files.',
    };
  }
  if (m.includes('actuation failed') || m.includes('coder')) {
    return {
      title: 'Coder agent failed',
      hint: 'The LLM call did not return a valid patch. Retry — Bedrock occasionally drops responses.',
    };
  }
  return { title: 'Failed', hint: null };
}
