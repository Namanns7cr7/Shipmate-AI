import { useEffect, useMemo, useRef, useState } from 'react';
import { BookOpen, ChevronDown, Check, Lock, Search } from 'lucide-react';
import type { GitHubRepo } from '../../types';

interface Props {
  repos: GitHubRepo[];
  selected: GitHubRepo | null;
  onSelect: (repo: GitHubRepo) => void;
  /** Disable interaction during long-running operations like analyze. */
  disabled?: boolean;
}

/**
 * Compact repository picker for the topbar — mirrors BranchPicker's style.
 * Click → dropdown listing the user's repos with a search filter (the list can
 * be long). Selecting a repo also resets the branch to that repo's default
 * (handled by the parent's onSelect, which already does handleSelectRepo).
 *
 * No fetch here: the repos list is already loaded in App.tsx, so this is a pure
 * presentational picker.
 */
export function RepoPicker({ repos, selected, onSelect, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Click-outside to close.
  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  // Focus the search box when the dropdown opens.
  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return repos;
    return repos.filter(
      r => r.name.toLowerCase().includes(q) || r.full_name.toLowerCase().includes(q),
    );
  }, [repos, query]);

  function toggle() {
    if (disabled) return;
    setOpen(v => {
      const next = !v;
      if (next) setQuery('');
      return next;
    });
  }

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
        title={disabled ? 'Repository is locked while an analysis is running' : 'Switch repository'}
        style={triggerStyle}
      >
        <BookOpen size={12} />
        <span style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {selected ? selected.name : 'Select repo'}
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
            minWidth: 300,
            maxWidth: 400,
            background: 'var(--panel)',
            backdropFilter: 'blur(14px)',
            border: '1px solid var(--line-2)',
            borderRadius: 10,
            boxShadow: '0 12px 32px rgba(0,0,0,0.4)',
            zIndex: 100,
            padding: 4,
          }}
        >
          <div style={{ padding: '6px 8px' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '5px 8px', borderRadius: 8,
              background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line)',
            }}>
              <Search size={12} style={{ color: 'var(--ink-3)', flexShrink: 0 }} />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search repositories…"
                style={{
                  flex: 1, background: 'transparent', border: 'none', outline: 'none',
                  color: 'var(--ink)', fontSize: 12,
                  fontFamily: 'JetBrains Mono, ui-monospace, monospace',
                }}
              />
            </div>
          </div>

          <div style={{ maxHeight: 320, overflowY: 'auto' }}>
            {filtered.map((r) => {
              const isSelected = selected?.id === r.id;
              return (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => { onSelect(r); setOpen(false); }}
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
                    {isSelected ? <Check size={12} /> : <BookOpen size={12} style={{ opacity: 0.5 }} />}
                  </span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.name}
                  </span>
                  {r.private && <Lock size={10} style={{ color: 'var(--ink-4)' }} />}
                  {r.language && (
                    <span style={{
                      fontSize: 9, fontWeight: 700, padding: '1px 5px',
                      borderRadius: 4, background: 'rgba(96,165,250,0.14)',
                      color: '#93c5fd', letterSpacing: '0.04em',
                    }}>
                      {r.language}
                    </span>
                  )}
                </button>
              );
            })}

            {filtered.length === 0 && (
              <div style={{ padding: '8px 10px', fontSize: 12, color: 'var(--ink-3)' }}>
                {repos.length === 0 ? 'No repositories found.' : 'No matches.'}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
