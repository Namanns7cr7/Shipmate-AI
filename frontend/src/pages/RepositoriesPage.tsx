import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Filter, Star, Lock, Globe, GitBranch, Clock, Zap, BarChart3 } from 'lucide-react';
import type { GitHubRepo, ShipMateReport } from '../types';

const LANG_COLORS: Record<string, string> = {
  TypeScript: '#3178c6', JavaScript: '#f1e05a', Python: '#3572A5',
  Go: '#00ADD8', Rust: '#dea584', Java: '#b07219', 'C#': '#178600',
  Ruby: '#701516', CSS: '#563d7c', HTML: '#e34c26', Shell: '#89e051',
};

function ScoreRing({ score, size = 56 }: { score: number; size?: number }) {
  const r = (size - 10) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#3b82f6' : score >= 40 ? '#f59e0b' : '#ef4444';
  const label = score >= 80 ? 'Ready to Ship' : score >= 60 ? 'Mostly Ready' : score >= 40 ? 'Needs Review' : 'Needs Work';
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="5" />
          <motion.circle
            cx={size / 2} cy={size / 2} r={r} fill="none"
            stroke={color} strokeWidth="5" strokeLinecap="round"
            strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ - dash }}
            transition={{ duration: 1, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-black text-white">{score}</span>
        </div>
      </div>
      <span className="text-[9px] font-semibold text-center leading-tight" style={{ color }}>{label}</span>
    </div>
  );
}

interface RepoCardProps {
  repo: GitHubRepo;
  report: ShipMateReport | null;
  isSelected: boolean;
  analyzing: boolean;
  onAnalyze: (repo: GitHubRepo) => void;
  onViewReport: () => void;
  index: number;
}

function RepoCard({ repo, report, isSelected, analyzing, onAnalyze, onViewReport, index }: RepoCardProps) {
  const hasReport = report && report.repo.name === repo.name;
  const langColor = repo.language ? (LANG_COLORS[repo.language] ?? '#64748b') : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.06 }}
      className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-5 hover:border-slate-700/70 transition-all group"
    >
      <div className="flex items-start gap-4">
        {/* Repo avatar */}
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-700 to-slate-800 border border-slate-700/60 flex items-center justify-center flex-shrink-0 text-lg">
          {repo.private ? '🔒' : '📂'}
        </div>

        {/* Main info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="text-sm font-bold text-white group-hover:text-blue-300 transition-colors truncate">
                {repo.full_name}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5 truncate">
                {repo.description || 'No description provided'}
              </p>
            </div>
            {/* Score ring (right side) */}
            {hasReport && <ScoreRing score={report!.readiness_score} size={52} />}
          </div>

          {/* Tags row */}
          <div className="flex flex-wrap items-center gap-2 mt-3">
            {repo.language && (
              <span className="flex items-center gap-1 text-[10px] font-medium text-slate-300 bg-slate-800/60 border border-slate-700/40 px-2 py-0.5 rounded-full">
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: langColor! }} />
                {repo.language}
              </span>
            )}
            {repo.private && (
              <span className="flex items-center gap-1 text-[10px] text-slate-500 bg-slate-800/40 border border-slate-700/30 px-2 py-0.5 rounded-full">
                <Lock size={9} /> Private
              </span>
            )}
            {!repo.private && (
              <span className="flex items-center gap-1 text-[10px] text-slate-500 bg-slate-800/40 border border-slate-700/30 px-2 py-0.5 rounded-full">
                <Globe size={9} /> Public
              </span>
            )}
            {repo.stargazers_count > 0 && (
              <span className="flex items-center gap-1 text-[10px] text-slate-500">
                <Star size={9} /> {repo.stargazers_count}
              </span>
            )}
          </div>

          {/* Last analyzed + actions */}
          <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-800/40">
            <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
              {hasReport ? (
                <>
                  <Clock size={10} className="flex-shrink-0" />
                  Last Analyzed{' '}
                  <span className="text-slate-400 font-semibold">
                    {new Date(report!.generated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                </>
              ) : (
                <>
                  <GitBranch size={10} className="flex-shrink-0" />
                  <span className="text-slate-500">{repo.default_branch}</span>
                </>
              )}
            </div>

            <div className="flex items-center gap-2">
              {hasReport && (
                <button
                  onClick={onViewReport}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-600/50 text-slate-300 hover:text-white hover:border-slate-500 transition-all"
                >
                  <BarChart3 size={11} /> View Report
                </button>
              )}
              <motion.button
                onClick={() => onAnalyze(repo)}
                disabled={analyzing && isSelected}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {analyzing && isSelected ? (
                  <>
                    <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Analyzing…
                  </>
                ) : (
                  <>
                    <Zap size={11} />
                    {hasReport ? 'Analyze Again' : 'Analyze'}
                  </>
                )}
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
  onAnalyze: (repo: GitHubRepo) => void;
  onViewReport: () => void;
}

export function RepositoriesPage({ repos, loadingRepos, selectedRepo, analyzing, report, onAnalyze, onViewReport }: Props) {
  const [query, setQuery] = useState('');
  const [langFilter, setLangFilter] = useState('All');

  const langs = ['All', ...Array.from(new Set(repos.map(r => r.language).filter(Boolean) as string[]))];
  const filtered = repos.filter(r =>
    (langFilter === 'All' || r.language === langFilter) &&
    (r.name.toLowerCase().includes(query.toLowerCase()) || r.full_name.toLowerCase().includes(query.toLowerCase()))
  );

  return (
    <div className="p-6 space-y-5 max-w-[1100px]">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Repositories</h1>
          <p className="text-sm text-slate-400 mt-0.5">Manage and analyze your GitHub repositories</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold transition-all">
          + Connect Repository
        </button>
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { val: repos.length || 24, label: 'Total Repositories', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
          { val: report ? 1 : 0, label: 'Analyzed', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
          { val: report?.readiness_score ?? 82, label: 'Average Score', color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20' },
          { val: 7, label: 'Critical Risks', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' },
        ].map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className={`rounded-xl border p-4 ${s.bg}`}
          >
            <p className={`text-xl font-black ${s.color}`}>{s.val}</p>
            <p className="text-xs text-slate-400 mt-0.5">{s.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Search + filter */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search repositories…"
            className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-slate-900/70 border border-slate-800/60 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-colors"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter size={13} className="text-slate-500" />
          <select
            value={langFilter}
            onChange={e => setLangFilter(e.target.value)}
            className="px-3 py-2.5 rounded-xl bg-slate-900/70 border border-slate-800/60 text-sm text-slate-300 focus:outline-none focus:border-blue-500/50 transition-colors"
          >
            {langs.map(l => <option key={l} value={l}>{l === 'All' ? 'All Languages' : l}</option>)}
          </select>
        </div>
        <select className="px-3 py-2.5 rounded-xl bg-slate-900/70 border border-slate-800/60 text-sm text-slate-300 focus:outline-none">
          <option>Sort: Recently Analyzed</option>
          <option>Sort: Name A-Z</option>
          <option>Sort: Score</option>
        </select>
      </div>

      {/* Repo list */}
      {loadingRepos ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-5 h-32 animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-12 text-center">
          <p className="text-slate-500 text-sm">No repositories found.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((repo, i) => (
            <RepoCard
              key={repo.id}
              repo={repo}
              report={report}
              isSelected={selectedRepo?.id === repo.id}
              analyzing={analyzing}
              onAnalyze={onAnalyze}
              onViewReport={onViewReport}
              index={i}
            />
          ))}
        </div>
      )}
    </div>
  );
}
