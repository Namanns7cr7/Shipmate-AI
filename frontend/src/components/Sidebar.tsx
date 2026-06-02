import { useState } from 'react';
import { Search, GitBranch, GitPullRequest, Zap, Star, Lock, Globe } from 'lucide-react';
import { motion } from 'framer-motion';
import type { GitHubRepo, GitHubBranch, GitHubPR } from '../types';

interface SidebarProps {
  repos: GitHubRepo[];
  selectedRepo: GitHubRepo | null;
  onSelectRepo: (repo: GitHubRepo) => void;
  branches: GitHubBranch[];
  selectedBranch: string;
  onSelectBranch: (branch: string) => void;
  pulls: GitHubPR[];
  selectedPull: GitHubPR | null;
  onSelectPull: (pr: GitHubPR | null) => void;
  featureContext: string;
  onFeatureContextChange: (v: string) => void;
  onAnalyze: () => void;
  analyzing: boolean;
  loadingRepos: boolean;
  lastAnalyzedAt?: string | null;
}

const LANG_COLORS: Record<string, string> = {
  TypeScript: '#3178c6', JavaScript: '#f1e05a', Python: '#3572A5',
  Go: '#00ADD8', Rust: '#dea584', Java: '#b07219', 'C#': '#178600',
  Ruby: '#701516', PHP: '#4F5D95', Swift: '#ffac45', Kotlin: '#A97BFF',
  CSS: '#563d7c', HTML: '#e34c26', Shell: '#89e051', Vue: '#41b883',
};

function LangDot({ language }: { language: string | null }) {
  if (!language) return null;
  const color = LANG_COLORS[language] ?? '#64748b';
  return <span className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />;
}

export function Sidebar({
  repos, selectedRepo, onSelectRepo,
  branches, selectedBranch, onSelectBranch,
  pulls, selectedPull, onSelectPull,
  featureContext, onFeatureContextChange,
  onAnalyze, analyzing, loadingRepos, lastAnalyzedAt,
}: SidebarProps) {
  const [query, setQuery] = useState('');
  const filtered = repos.filter(r =>
    r.name.toLowerCase().includes(query.toLowerCase()) ||
    r.full_name.toLowerCase().includes(query.toLowerCase())
  );
  const canAnalyze = !!selectedRepo && !analyzing;

  return (
    <div className="flex flex-col gap-5 h-full">
      {/* ── Repository section ── */}
      <div>
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2.5">Repository</p>

        {/* Search */}
        <div className="relative mb-2">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search repositories…"
            className="w-full pl-8 pr-3 py-2 rounded-lg bg-slate-900/70 border border-slate-700/50
                       text-xs text-slate-200 placeholder-slate-600
                       focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-colors"
          />
        </div>

        {/* Repo list */}
        <div className="max-h-56 overflow-y-auto space-y-0.5 pr-0.5 scrollbar-thin">
          {loadingRepos ? (
            <div className="space-y-1.5 px-1 py-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-9 rounded-lg bg-slate-800/60 animate-pulse" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <p className="text-xs text-slate-500 px-2 py-3 text-center">No repositories found.</p>
          ) : filtered.map(repo => (
            <button
              key={repo.id}
              onClick={() => onSelectRepo(repo)}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-xs transition-all group ${
                selectedRepo?.id === repo.id
                  ? 'bg-blue-600/20 border border-blue-500/30 text-blue-100'
                  : 'text-slate-300 hover:bg-slate-800/60 border border-transparent'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                {repo.private
                  ? <Lock size={11} className="text-slate-500 flex-shrink-0" />
                  : <Globe size={11} className="text-slate-600 flex-shrink-0" />
                }
                <span className="font-semibold truncate">{repo.name}</span>
              </div>
              <div className="flex items-center gap-2 mt-1 ml-[19px]">
                {repo.language && (
                  <>
                    <LangDot language={repo.language} />
                    <span className="text-[10px] text-slate-500">{repo.language}</span>
                  </>
                )}
                {repo.stargazers_count > 0 && (
                  <span className="flex items-center gap-0.5 text-[10px] text-slate-600 ml-auto">
                    <Star size={9} />
                    {repo.stargazers_count}
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Branch selector ── */}
      {selectedRepo && (
        <div>
          <label className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
            <GitBranch size={11} /> Branch
          </label>
          {branches.length > 0 ? (
            <select
              value={selectedBranch}
              onChange={e => onSelectBranch(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-900/70 border border-slate-700/50
                         text-xs text-slate-200 focus:outline-none focus:border-blue-500/50 transition-colors"
            >
              {branches.map(b => (
                <option key={b.name} value={b.name}>{b.name}</option>
              ))}
            </select>
          ) : (
            <div className="h-8 rounded-lg bg-slate-800/40 animate-pulse" />
          )}
        </div>
      )}

      {/* ── PR selector ── */}
      {selectedRepo && pulls.length > 0 && (
        <div>
          <label className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
            <GitPullRequest size={11} /> Pull Request
            <span className="font-normal text-slate-600 normal-case tracking-normal">(optional)</span>
          </label>
          <select
            value={selectedPull?.number ?? ''}
            onChange={e => {
              const n = Number(e.target.value);
              onSelectPull(pulls.find(p => p.number === n) ?? null);
            }}
            className="w-full px-3 py-2 rounded-lg bg-slate-900/70 border border-slate-700/50
                       text-xs text-slate-200 focus:outline-none focus:border-blue-500/50 transition-colors"
          >
            <option value="">Analyze branch directly</option>
            {pulls.map(p => (
              <option key={p.number} value={p.number}>#{p.number} {p.title.slice(0, 40)}</option>
            ))}
          </select>
        </div>
      )}

      {/* ── Feature context ── */}
      {selectedRepo && (
        <div className="flex-1">
          <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
            Feature Context
            <span className="ml-1.5 font-normal normal-case tracking-normal text-slate-600">(optional)</span>
          </label>
          <textarea
            value={featureContext}
            onChange={e => onFeatureContextChange(e.target.value)}
            placeholder={"Describe what you're shipping…\ne.g. Add GitHub OAuth login with repo access"}
            rows={4}
            className="w-full px-3 py-2 rounded-lg bg-slate-900/70 border border-slate-700/50
                       text-xs text-slate-200 placeholder-slate-600 resize-none leading-relaxed
                       focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-colors"
          />
        </div>
      )}

      {/* ── Analyze button ── */}
      {selectedRepo ? (
        <div className="mt-auto space-y-2">
          <motion.button
            onClick={onAnalyze}
            disabled={!canAnalyze}
            whileHover={canAnalyze ? { scale: 1.02 } : {}}
            whileTap={canAnalyze ? { scale: 0.98 } : {}}
            className={`flex items-center justify-center gap-2 w-full py-3 rounded-xl font-bold text-sm transition-all ${
              canAnalyze
                ? 'btn-primary text-white shadow-lg shadow-blue-900/30'
                : 'bg-slate-800/60 text-slate-500 cursor-not-allowed border border-slate-700/40'
            }`}
          >
            {analyzing ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Analyzing…
              </>
            ) : (
              <>
                <Zap size={15} className="relative z-10" />
                <span className="relative z-10">Analyze Readiness</span>
              </>
            )}
          </motion.button>

          {lastAnalyzedAt && !analyzing && (
            <p className="text-center text-[10px] text-slate-600">
              Last analysis: {lastAnalyzedAt}
            </p>
          )}
        </div>
      ) : (
        <div className="mt-auto rounded-xl bg-slate-800/30 border border-slate-700/30 p-4 text-center">
          <p className="text-xs text-slate-500">Select a repository above to begin your analysis.</p>
        </div>
      )}
    </div>
  );
}
