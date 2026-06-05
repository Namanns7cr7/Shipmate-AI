import { useEffect, useRef, useState } from 'react';
import { GitBranch, ChevronDown, Lock, Check } from 'lucide-react';
import { api } from '../../lib/api';
import type { GitHubBranch } from '../../types';

interface Props {
  /** Repo full_name in `owner/name` form. Picker is hidden when null. */
  repoFullName: string | null;
  defaultBranch?: string;
  selected: string;
  onChange: (branch: string) => void;
  accessToken: string | null;
  /** Disable interaction during long-running operations like analyze. */
  disabled?: boolean;
}

/**
 * Compact branch picker for the topbar. Click → opens a dropdown listing
 * every branch on the repo (paginated by the GitHub API up to 50). The
 * selected branch is what `/api/analyze` runs against.
 *
 * Branches are fetched lazily on first open and re-fetched on repo change.
 */
export function BranchPicker({
  repoFullName, defaultBranch, selected, onChange, accessToken, disabled,
}: Props) {
  const [open, setOpen] = useState(false);
  const [branches, setBranches] = useState<GitHubBranch[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Reset cached branches when the repo changes — otherwise stale list shows.
  useEffect(() => { setBranches(null); setError(null); setOpen(false); }, [repoFullName]);

  // Click-outside to close.
  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  async function load() {
    if (!repoFullName || !accessToken) return;
    const [owner, repo] = repoFullName.split('/');
    if (!owner || !repo) return;
    setLoading(true);
    setError(null);
    try {
      const list = await api.getBranches(owner, repo, accessToken);
      setBranches(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load branches');
    } finally {
      setLoading(false);
    }
  }

  function toggle() {
    if (disabled || !repoFullName) return;
    setOpen(v => {
      const next = !v;
      if (next && branches === null) load();
      return next;
    });
  }

  if (!repoFullName) return null;

  const triggerStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 8px',
    fontSize: 12,
    fontFamily: 'JetBrains Mono, ui-monospace, monospace',
    fontWeight: 600,
    color: 'var(--ink-2)',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  };

  return (
    <div ref={containerRef} style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        type="button"
        onClick={toggle}
        title={disabled ? 'Branch is locked while an analysis is running' : 'Switch branch'}
        style={triggerStyle}
      >
        <GitBranch size={12} />
        <span style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {selected}
        </span>
        <ChevronDown size={12} style={{ opacity: 0.7 }} />
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            marginTop: 6,
            minWidth: 280,
            maxWidth: 360,
            maxHeight: 320,
            overflowY: 'auto',
            background: 'var(--panel)',
            backdropFilter: 'blur(14px)',
            border: '1px solid var(--line-2)',
            borderRadius: 10,
            boxShadow: '0 12px 32px rgba(0,0,0,0.4)',
            zIndex: 100,
            padding: 4,
          }}
        >
          <div
            style={{
              padding: '6px 10px',
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
              color: 'var(--ink-3)',
            }}
          >
            Branches
          </div>

          {loading && (
            <div style={{ padding: '8px 10px', fontSize: 12, color: 'var(--ink-3)' }}>
              Loading…
            </div>
          )}

          {error && (
            <div style={{ padding: '8px 10px', fontSize: 12, color: '#f87171' }}>
              {error}
            </div>
          )}

          {branches?.map((b) => {
            const isSelected = b.name === selected;
            const isDefault = b.name === defaultBranch;
            return (
              <button
                key={b.name}
                type="button"
                onClick={() => { onChange(b.name); setOpen(false); }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 6,
                  border: 'none',
                  background: isSelected ? 'rgba(96,165,250,0.12)' : 'transparent',
                  color: isSelected ? '#fff' : 'var(--ink-2)',
                  fontFamily: 'JetBrains Mono, ui-monospace, monospace',
                  fontSize: 12,
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'background 0.12s',
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.04)';
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                }}
              >
                <span style={{ width: 14, display: 'inline-flex', justifyContent: 'center' }}>
                  {isSelected ? <Check size={12} /> : <GitBranch size={12} style={{ opacity: 0.5 }} />}
                </span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {b.name}
                </span>
                {isDefault && (
                  <span style={{
                    fontSize: 9, fontWeight: 700, padding: '1px 5px',
                    borderRadius: 4, background: 'rgba(16,185,129,0.18)',
                    color: '#34d399', letterSpacing: '0.05em',
                  }}>
                    DEFAULT
                  </span>
                )}
                {b.protected && (
                  <Lock size={10} style={{ color: 'var(--ink-4)' }} />
                )}
              </button>
            );
          })}

          {branches && branches.length === 0 && (
            <div style={{ padding: '8px 10px', fontSize: 12, color: 'var(--ink-3)' }}>
              No branches found.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
