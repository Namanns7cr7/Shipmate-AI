import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, SlidersHorizontal, Star, Lock, Globe, Clock, Zap, BarChart3, GitBranch, Plus } from 'lucide-react';
import type { GitHubRepo, ShipMateReport } from '../types';

const LANG_COLORS: Record<string, string> = {
  TypeScript: '#3178c6', JavaScript: '#f1e05a', Python: '#3572A5',
  Go: '#00ADD8', Rust: '#dea584', Java: '#b07219', 'C#': '#178600',
  Ruby: '#701516', CSS: '#563d7c', HTML: '#e34c26', Shell: '#89e051',
};

function ScoreRing({ score }: { score: number }) {
  const size = 56; const r = 22; const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#3b82f6' : score >= 40 ? '#f59e0b' : '#ef4444';
  const recLabel = score >= 80 ? 'Ready to Ship' : score >= 60 ? 'Mostly Ready' : score >= 40 ? 'Needs Review' : 'Needs Work';
  return (
    <div className="flex flex-col items-center gap-1 flex-shrink-0">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
          <motion.circle
            cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="5"
            strokeLinecap="round" strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ - dash }}
            transition={{ duration: 1, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-[13px] font-black text-white">{score}</span>
        </div>
      </div>
      <span className="text-[9px] font-bold text-center leading-tight" style={{ color, maxWidth: 64 }}>{recLabel}</span>
    </div>
  );
}

interface RepoCardProps {
  repo: GitHubRepo;
  report: ShipMateReport | null;
  isSelected: boolean;
  analyzing: boolean;
  onAnalyze: (r: GitHubRepo) => void;
  onViewReport: () => void;
  index: number;
}

function RepoCard({ repo, report, isSelected, analyzing, onAnalyze, onViewReport, index }: RepoCardProps) {
  const hasReport = report?.repo.name === repo.name;
  const lc = repo.language ? (LANG_COLORS[repo.language] ?? '#64748b') : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className="rounded-2xl p-5 border border-white/6 hover:border-white/10 transition-all group"
      style={{ background: 'rgba(11,18,35,0.9)' }}
    >
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className="w-10 h-10 rounded-xl border border-white/8 flex items-center justify-center text-lg flex-shrink-0"
          style={{ background: 'rgba(255,255,255,0.04)' }}>
          {repo.private ? '🔒' : '📁'}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-[14px] font-bold text-slate-200 group-hover:text-white transition-colors truncate">{repo.full_name}</h3>
                {hasReport && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" title="Analyzed" />}
              </div>
              <p className="text-xs text-slate-600 truncate">{repo.description || 'No description'}</p>

              {/* Tags */}
              <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                {repo.language && (
                  <span className="flex items-center gap-1 text-[10px] font-medium text-slate-300 px-2 py-0.5 rounded-full border border-white/8 bg-white/4">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: lc! }} />
                    {repo.language}
                  </span>
                )}
                {repo.private
                  ? <span className="flex items-center gap-1 text-[10px] text-slate-500 px-2 py-0.5 rounded-full border border-white/6"><Lock size={8} /> Private</span>
                  : <span className="flex items-center gap-1 text-[10px] text-slate-500 px-2 py-0.5 rounded-full border border-white/6"><Globe size={8} /> Public</span>
                }
                {repo.stargazers_count > 0 && (
                  <span className="flex items-center gap-1 text-[10px] text-slate-600">
                    <Star size={9} /> {repo.stargazers_count}
                  </span>
                )}
              </div>
            </div>
            {hasReport && <ScoreRing score={report!.readiness_score} />}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/5">
            <div className="flex items-center gap-1 text-[11px] text-slate-600">
              {hasReport ? (
                <><Clock size={10} /> Last analyzed{' '}
                  <span className="text-slate-400 ml-0.5">
                    {new Date(report!.generated_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </span>
                </>
              ) : (
                <><GitBranch size={10} /> {repo.default_branch}</>
              )}
            </div>
            <div className="flex items-center gap-2">
              {hasReport && (
                <button onClick={onViewReport}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold border border-white/10 text-slate-300 hover:text-white hover:border-white/20 transition-all">
                  <BarChart3 size={11} /> View Report
                </button>
              )}
              <motion.button
                onClick={() => onAnalyze(repo)}
                disabled={analyzing && isSelected}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold text-white transition-all disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #1d4ed8, #0891b2)' }}
              >
                {analyzing && isSelected
                  ? <><span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Analyzing…</>
                  : <><Zap size={11} /> {hasReport ? 'Analyze Again' : 'Analyze'}</>
                }
              </motion.button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

interface Props {
  repos: GitHubRepo[];
  loadingRepos: boolean;
  selectedRepo: GitHubRepo | null;
  analyzing: boolean;
  report: ShipMateReport | null;
  onAnalyze: (r: GitHubRepo) => void;
  onViewReport: () => void;
}

export function RepositoriesPage({ repos, loadingRepos, selectedRepo, analyzing, report, onAnalyze, onViewReport }: Props) {
  const [query, setQuery] = useState('');
  const [lang, setLang] = useState('All');

  const langs = ['All', ...Array.from(new Set(repos.map(r => r.language).filter(Boolean) as string[]))];
  const filtered = repos.filter(r =>
    (lang === 'All' || r.language === lang) &&
    (r.name.toLowerCase().includes(query.toLowerCase()) || r.full_name.toLowerCase().includes(query.toLowerCase()))
  );

  return (
    <div className="px-8 py-7 max-w-[1080px] space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div>
          <h1 className="text-[22px] font-black text-white tracking-tight">Repositories</h1>
          <p className="text-sm text-slate-500 mt-0.5">Manage and analyze your GitHub repositories</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold text-white transition-all"
          style={{ background: 'linear-gradient(135deg, #1d4ed8, #0891b2)' }}>
          <Plus size={14} /> Connect Repository
        </button>
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { val: repos.length || 24, label: 'Total Repositories', color: 'text-blue-400',    bg: 'rgba(59,130,246,0.08)',  border: 'rgba(59,130,246,0.2)' },
          { val: report ? 1 : 0,    label: 'Analyzed',           color: 'text-emerald-400', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.2)' },
          { val: report?.readiness_score ?? 82, label: 'Average Score', color: 'text-purple-400',  bg: 'rgba(139,92,246,0.08)',  border: 'rgba(139,92,246,0.2)'  },
          { val: 7,                  label: 'Critical Risks',     color: 'text-red-400',     bg: 'rgba(239,68,68,0.08)',  border: 'rgba(239,68,68,0.2)'  },
        ].map((s, i) => (
          <motion.div key={s.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
            className="rounded-xl p-4" style={{ background: s.bg, border: `1px solid ${s.border}` }}>
            <p className={`text-xl font-black ${s.color}`}>{s.val}</p>
            <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Search + filter */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search size={13} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600 pointer-events-none" />
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search repositories…"
            className="w-full pl-9 pr-4 py-2.5 rounded-xl text-sm text-slate-200 placeholder-slate-600 focus:outline-none transition-colors"
            style={{ background: 'rgba(11,18,35,0.9)', border: '1px solid rgba(255,255,255,0.07)' }}
          />
        </div>
        <div className="flex items-center gap-2">
          <SlidersHorizontal size={13} className="text-slate-600" />
          <select value={lang} onChange={e => setLang(e.target.value)}
            className="px-3 py-2.5 rounded-xl text-sm text-slate-300 focus:outline-none"
            style={{ background: 'rgba(11,18,35,0.9)', border: '1px solid rgba(255,255,255,0.07)' }}>
            {langs.map(l => <option key={l}>{l === 'All' ? 'All Languages' : l}</option>)}
          </select>
          <select className="px-3 py-2.5 rounded-xl text-sm text-slate-300 focus:outline-none"
            style={{ background: 'rgba(11,18,35,0.9)', border: '1px solid rgba(255,255,255,0.07)' }}>
            <option>Sort: Recently Analyzed</option>
            <option>Sort: Name A-Z</option>
            <option>Sort: Score</option>
          </select>
        </div>
      </div>

      {/* Repo list */}
      {loadingRepos ? (
        <div className="space-y-4">{[1,2,3].map(i => <div key={i} className="rounded-2xl h-28 animate-pulse" style={{ background: 'rgba(11,18,35,0.9)', border: '1px solid rgba(255,255,255,0.06)' }} />)}</div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl p-14 text-center" style={{ background: 'rgba(11,18,35,0.9)', border: '1px solid rgba(255,255,255,0.06)' }}>
          <p className="text-slate-500">No repositories found.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((r, i) => (
            <RepoCard key={r.id} repo={r} report={report} isSelected={selectedRepo?.id === r.id}
              analyzing={analyzing} onAnalyze={onAnalyze} onViewReport={onViewReport} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
