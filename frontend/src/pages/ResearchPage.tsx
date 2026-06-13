import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  Telescope, Search, Sparkles, Wrench, Network, GitBranch, Ghost,
  Loader2, AlertTriangle, FileCode2, ChevronRight,
} from 'lucide-react';
import { api } from '../lib/api';
import type { GitHubRepo, ResearchEvent } from '../types';

interface Props {
  selectedRepo: GitHubRepo | null;
  selectedBranch: string;
  accessToken: string | null;
}

type Mode = 'research' | 'improve' | 'innovate';

const MODES: { id: Mode; label: string; Icon: React.ElementType; blurb: string }[] = [
  { id: 'research', label: 'Research', Icon: Search,   blurb: 'Map dataflow, find loops/holes/dead code — grounded on the reference graph.' },
  { id: 'improve',  label: 'Improve',  Icon: Wrench,   blurb: 'Research + conservative, grounded improvement proposals.' },
  { id: 'innovate', label: 'Innovate', Icon: Sparkles, blurb: 'Research + blue-sky, anchored innovation ideas.' },
];

const KIND_TONE: Record<string, string> = {
  dataflow: 'cyan', dead_code: 'slate', coupling: 'amber', risk: 'red', observation: 'blue',
};
const SEV_TONE: Record<string, string> = { high: 'red', medium: 'amber', low: 'slate' };

interface Finding {
  title: string; kind: string; severity: string; detail: string;
  evidence: string[]; suggested_action: string; graph_signal: string;
}
interface Opp {
  id: string; title: string; category: string; impact: string;
  value_score: number; priority: string; target_files: string[]; rationale: string;
}

export function ResearchPage({ selectedRepo, selectedBranch, accessToken }: Props) {
  const [mode, setMode] = useState<Mode>('research');
  const [question, setQuestion] = useState('');
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [graph, setGraph] = useState<{ modules: number; cycles: number; god_modules: number; orphans: number } | null>(null);
  const [answer, setAnswer] = useState('');
  const [findings, setFindings] = useState<Finding[]>([]);
  const [opps, setOpps] = useState<Opp[]>([]);
  const [phase, setPhase] = useState('');
  const abortRef = useRef<AbortController | null>(null);

  const owner = selectedRepo?.owner?.login || (selectedRepo?.full_name || '').split('/')[0] || '';
  const repo = selectedRepo?.name || (selectedRepo?.full_name || '').split('/')[1] || '';

  function reset() {
    setError(null); setGraph(null); setAnswer(''); setFindings([]); setOpps([]); setPhase('');
  }

  async function run() {
    if (!selectedRepo || !accessToken) { setError('Select a repository first.'); return; }
    reset();
    setRunning(true);
    setPhase('Starting…');
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      await api.startResearch(
        { owner, repo, branch: selectedBranch, access_token: accessToken, mode, question: question.trim() },
        (e: ResearchEvent) => handleEvent(e),
        ctrl.signal,
      );
    } catch (err) {
      if (!ctrl.signal.aborted) setError(err instanceof Error ? err.message : 'Research failed.');
    } finally {
      setRunning(false);
      setPhase('');
      abortRef.current = null;
    }
  }

  function stop() {
    abortRef.current?.abort();
    setRunning(false);
    setPhase('');
  }

  function handleEvent(e: ResearchEvent) {
    switch (e.event) {
      case 'research.start': setPhase(`Researching (${e.mode})…`); break;
      case 'index.done': setPhase(`Indexed ${e.files ?? 0} files — building reference graph…`); break;
      case 'graph.done':
        setGraph({ modules: e.modules ?? 0, cycles: e.cycles ?? 0, god_modules: e.god_modules ?? 0, orphans: e.orphans ?? 0 });
        setPhase('Analyzing the graph…');
        break;
      case 'finding':
        setFindings(prev => [...prev, {
          title: e.title || '', kind: e.kind || 'observation', severity: e.severity || 'medium',
          detail: e.detail || '', evidence: e.evidence || [], suggested_action: e.suggested_action || '',
          graph_signal: e.graph_signal || '',
        }]);
        break;
      case 'research.done': if (e.answer) setAnswer(e.answer); break;
      case 'propose.start': setPhase('Proposing improvements…'); break;
      case 'opportunity':
        setOpps(prev => [...prev, {
          id: e.id || '', title: e.title || '', category: e.category || '', impact: e.impact || '',
          value_score: e.value_score ?? 0, priority: e.priority || 'medium',
          target_files: e.target_files || [], rationale: e.rationale || '',
        }]);
        break;
      case 'done': setPhase(''); break;
      case 'error': setError(e.message || 'Research error.'); break;
      default: break;
    }
  }

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
        <div className="chip tone-cyan" style={{ width: 38, height: 38, display: 'grid', placeItems: 'center' }}>
          <Telescope size={20} />
        </div>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>Research</h1>
          <div className="muted" style={{ fontSize: 13 }}>
            Find loops, holes, dead code &amp; messy dataflow — grounded on the import/symbol graph.
          </div>
        </div>
      </div>

      {/* Mode selector */}
      <div style={{ display: 'flex', gap: 10, margin: '20px 0 14px', flexWrap: 'wrap' }}>
        {MODES.map(({ id, label, Icon, blurb }) => (
          <button
            key={id}
            onClick={() => setMode(id)}
            className={`card ${mode === id ? 'card-hover' : ''}`}
            style={{
              flex: '1 1 220px', textAlign: 'left', padding: 14, cursor: 'pointer',
              border: mode === id ? '1px solid var(--cyan)' : '1px solid var(--line)',
              background: mode === id ? 'rgba(34,211,238,0.06)' : 'var(--panel)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, marginBottom: 4 }}>
              <Icon size={16} /> {label}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>{blurb}</div>
          </button>
        ))}
      </div>

      {/* Question + run */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 18 }}>
        <input
          className="input"
          style={{ flex: 1 }}
          placeholder='Optional question — e.g. "where does the auth token flow?" (blank = open audit)'
          value={question}
          onChange={ev => setQuestion(ev.target.value)}
          onKeyDown={ev => { if (ev.key === 'Enter' && !running) run(); }}
          disabled={running}
        />
        {running ? (
          <button className="btn btn-secondary" onClick={stop}>
            <Loader2 size={15} className="spin" /> Stop
          </button>
        ) : (
          <button className="btn btn-primary" onClick={run} disabled={!selectedRepo}>
            <Telescope size={15} /> Run
          </button>
        )}
      </div>

      {phase && (
        <div className="muted mono" style={{ fontSize: 12, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Loader2 size={13} className="spin" /> {phase}
        </div>
      )}
      {error && (
        <div className="card tone-red" style={{ padding: 12, marginBottom: 14, display: 'flex', gap: 8, alignItems: 'center' }}>
          <AlertTriangle size={16} /> <span style={{ fontSize: 13 }}>{error}</span>
        </div>
      )}

      {/* Graph summary */}
      {graph && (
        <div style={{ display: 'flex', gap: 10, marginBottom: 18, flexWrap: 'wrap' }}>
          <GraphStat Icon={Network}  label="Modules"     value={graph.modules} tone="blue" />
          <GraphStat Icon={GitBranch} label="Cycles"     value={graph.cycles} tone={graph.cycles ? 'red' : 'slate'} />
          <GraphStat Icon={FileCode2} label="God modules" value={graph.god_modules} tone={graph.god_modules ? 'amber' : 'slate'} />
          <GraphStat Icon={Ghost}     label="Orphans"     value={graph.orphans} tone={graph.orphans ? 'amber' : 'slate'} />
        </div>
      )}

      {/* Answer */}
      {answer && (
        <div className="card" style={{ padding: 16, marginBottom: 18 }}>
          <div className="eyebrow" style={{ marginBottom: 6 }}>Answer</div>
          <div style={{ fontSize: 14, lineHeight: 1.55, whiteSpace: 'pre-wrap' }}>{answer}</div>
        </div>
      )}

      {/* Findings */}
      {findings.length > 0 && (
        <div style={{ marginBottom: 22 }}>
          <div className="eyebrow" style={{ marginBottom: 10 }}>Findings ({findings.length})</div>
          {findings.map((f, i) => (
            <motion.div
              key={i} initial={{ y: 10 }} animate={{ y: 0 }}
              className="card" style={{ padding: 14, marginBottom: 10 }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                <span className={`pill tone-${SEV_TONE[f.severity] || 'slate'}`}>{f.severity}</span>
                <span className={`chip tone-${KIND_TONE[f.kind] || 'blue'}`}>{f.kind}</span>
                <span style={{ fontWeight: 700, fontSize: 14 }}>{f.title}</span>
                {f.graph_signal && (
                  <span className="chip tone-cyan mono" style={{ fontSize: 11 }}>{f.graph_signal}</span>
                )}
              </div>
              <div style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.5 }}>{f.detail}</div>
              {f.suggested_action && (
                <div style={{ fontSize: 12.5, marginTop: 8, display: 'flex', gap: 6, alignItems: 'flex-start' }}>
                  <ChevronRight size={14} style={{ marginTop: 2, color: 'var(--cyan)' }} />
                  <span>{f.suggested_action}</span>
                </div>
              )}
              {f.evidence.length > 0 && (
                <div className="mono muted" style={{ fontSize: 11, marginTop: 6 }}>
                  {f.evidence.join('  ·  ')}
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}

      {/* Opportunities (improve / innovate) */}
      {opps.length > 0 && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 10 }}>
            {mode === 'innovate' ? 'Innovation ideas' : 'Improvement opportunities'} ({opps.length})
          </div>
          {opps.map((o, i) => (
            <motion.div
              key={o.id || i} initial={{ y: 10 }} animate={{ y: 0 }}
              className="card" style={{ padding: 14, marginBottom: 10 }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                <span className="pill tone-blue mono">{o.value_score}</span>
                <span className="chip tone-purple">{o.category}</span>
                <span style={{ fontWeight: 700, fontSize: 14 }}>{o.title}</span>
              </div>
              <div style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.5 }}>{o.impact || o.rationale}</div>
              {o.target_files.length > 0 && (
                <div className="mono muted" style={{ fontSize: 11, marginTop: 6 }}>{o.target_files.join('  ·  ')}</div>
              )}
            </motion.div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!running && !graph && !error && (
        <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--ink-3)' }}>
          <Telescope size={34} style={{ opacity: 0.5, marginBottom: 10 }} />
          <div style={{ fontSize: 14 }}>Pick a mode and run a research pass on <b>{selectedRepo?.full_name || 'your repo'}</b>.</div>
        </div>
      )}
    </div>
  );
}

function GraphStat({ Icon, label, value, tone }: { Icon: React.ElementType; label: string; value: number; tone: string }) {
  return (
    <div className="card" style={{ flex: '1 1 140px', padding: 12, display: 'flex', alignItems: 'center', gap: 10 }}>
      <span className={`chip tone-${tone}`} style={{ width: 30, height: 30, display: 'grid', placeItems: 'center' }}>
        <Icon size={15} />
      </span>
      <div>
        <div style={{ fontSize: 20, fontWeight: 800, lineHeight: 1 }}>{value}</div>
        <div className="muted" style={{ fontSize: 11 }}>{label}</div>
      </div>
    </div>
  );
}
