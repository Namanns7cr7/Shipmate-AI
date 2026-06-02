import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, AlertTriangle, BarChart3, ExternalLink } from 'lucide-react';
import type { GitHubUser, GitHubRepo, ShipMateReport } from '../types';
import type { Page } from '../components/app/AppSidebar';

const REC_BADGE: Record<string, { label: string; cls: string }> = {
  ready_to_ship: { label: 'Ready to Ship',   cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  mostly_ready:  { label: 'Mostly Ready',    cls: 'bg-blue-500/15    text-blue-300    border-blue-500/30' },
  needs_review:  { label: 'Needs Review',    cls: 'bg-yellow-500/15  text-yellow-300  border-yellow-500/30' },
  risky_release: { label: 'Needs Improvement', cls: 'bg-orange-500/15 text-orange-300 border-orange-500/30' },
  not_ready:     { label: 'Needs Work',      cls: 'bg-red-500/15     text-red-300     border-red-500/30' },
};

function StatCard({ value, label, trend, trendUp, icon: Icon, color }: {
  value: string | number; label: string; trend?: string; trendUp?: boolean;
  icon: React.ElementType; color: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-5 flex items-start justify-between"
    >
      <div>
        <p className="text-2xl font-black text-white">{value}</p>
        <p className="text-xs text-slate-400 mt-1">{label}</p>
        {trend && (
          <p className={`text-[10px] mt-2 flex items-center gap-1 font-semibold ${trendUp ? 'text-emerald-400' : 'text-red-400'}`}>
            {trendUp ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
            {trend}
          </p>
        )}
      </div>
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={18} className="text-white opacity-90" />
      </div>
    </motion.div>
  );
}

function ScoreChip({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    : score >= 60 ? 'bg-blue-500/15 text-blue-300 border-blue-500/30'
    : score >= 40 ? 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30'
    : 'bg-red-500/15 text-red-300 border-red-500/30';
  return (
    <span className={`inline-flex items-center justify-center w-10 h-7 rounded-full text-xs font-black border ${color}`}>
      {score}
    </span>
  );
}

interface Props {
  user: GitHubUser | null;
  repos: GitHubRepo[];
  report: ShipMateReport | null;
  onNavigate: (p: Page) => void;
}

export function DashboardPage({ user, repos, report, onNavigate }: Props) {
  const recentMockRows = repos.slice(0, 5).map((r, i) => ({
    name: r.full_name,
    score: report && i === 0 ? report.readiness_score : null,
    rec: report && i === 0 ? report.ship_recommendation : null,
    ago: i === 0 ? '5 min ago' : i === 1 ? '1 day ago' : i === 2 ? '3 days ago' : `${i + 3} days ago`,
  }));

  return (
    <div className="p-6 space-y-6 max-w-[1100px]">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-black text-white">
              Welcome back, {user?.name || user?.login || 'Developer'}! 👋
            </h1>
            <p className="text-sm text-slate-400 mt-1">Here's what's happening with your projects today.</p>
          </div>
          <button
            onClick={() => onNavigate('reports')}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/60 border border-slate-700/50 text-slate-300 text-sm hover:text-white hover:bg-slate-800 transition-all"
          >
            <BarChart3 size={14} /> View Reports
          </button>
        </div>
      </motion.div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard value={repos.length || 24} label="Total Repositories" trend="↑ 12% from last week" trendUp icon={FolderGit} color="bg-blue-600/30" />
        <StatCard value={58} label="Analyses Performed" trend="↑ 38% from last week" trendUp icon={FlaskIcon} color="bg-purple-600/30" />
        <StatCard value={report?.readiness_score ?? 82} label="Average Readiness Score" trend="↑ 6% from last week" trendUp icon={TrendingUp} color="bg-emerald-600/30" />
        <StatCard value={7} label="Critical Risks Found" trend="↓ 3% from last week" trendUp={false} icon={AlertTriangle} color="bg-red-600/30" />
      </div>

      {/* Recent analyses + AI Insights */}
      <div className="grid lg:grid-cols-5 gap-5">
        {/* Recent analyses table */}
        <div className="lg:col-span-3 rounded-2xl bg-slate-900/70 border border-slate-800/60 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800/60 flex items-center justify-between">
            <h2 className="text-sm font-bold text-white">Recent Analyses</h2>
            <button
              onClick={() => onNavigate('repos')}
              className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              View All Analyses
            </button>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800/40">
                <th className="text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider px-5 py-2.5">Repository</th>
                <th className="text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider px-3 py-2.5">Score</th>
                <th className="text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider px-3 py-2.5">Status</th>
                <th className="text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider px-3 py-2.5">Analyzed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/30">
              {recentMockRows.length > 0 ? recentMockRows.map((row, i) => {
                const badge = row.rec ? REC_BADGE[row.rec] : null;
                return (
                  <tr key={i} className="hover:bg-slate-800/30 transition-colors group">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-200 group-hover:text-white transition-colors truncate max-w-[160px]">
                          {row.name}
                        </span>
                        <ExternalLink size={10} className="text-slate-600 group-hover:text-slate-400 flex-shrink-0" />
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      {row.score !== null ? <ScoreChip score={row.score} /> : <span className="text-xs text-slate-600">—</span>}
                    </td>
                    <td className="px-3 py-3">
                      {badge ? (
                        <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full border ${badge.cls}`}>{badge.label}</span>
                      ) : (
                        <span className="text-[10px] font-semibold px-2.5 py-1 rounded-full border bg-slate-700/30 text-slate-500 border-slate-600/30">Not analyzed</span>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <span className="text-xs text-slate-500">{row.ago}</span>
                    </td>
                  </tr>
                );
              }) : (
                <tr>
                  <td colSpan={4} className="px-5 py-8 text-center text-sm text-slate-500">
                    No repositories yet. <button onClick={() => onNavigate('repos')} className="text-blue-400 hover:underline">Connect a repo →</button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* AI Insights */}
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-2xl bg-slate-900/70 border border-slate-800/60 p-5">
            <h2 className="text-sm font-bold text-white mb-4">AI Insights</h2>

            {report ? (
              <>
                <div className="rounded-xl bg-red-500/8 border border-red-500/20 p-3.5 mb-3">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle size={12} className="text-red-400" />
                    <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider">Highest Risk</span>
                  </div>
                  <p className="text-xs font-semibold text-white">{report.repo.full_name}</p>
                  {report.key_blockers[0] && (
                    <>
                      <p className="text-[10px] text-red-300 mt-1">Critical Issue</p>
                      <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">{report.key_blockers[0]}</p>
                    </>
                  )}
                  {report.next_actions[0] && (
                    <>
                      <p className="text-[10px] text-emerald-300 mt-2">Recommendation</p>
                      <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">{report.next_actions[0]}</p>
                    </>
                  )}
                  <button onClick={() => onNavigate('reports')} className="mt-3 w-full py-1.5 rounded-lg bg-blue-600 text-xs font-semibold text-white hover:bg-blue-500 transition-colors">
                    View Analysis
                  </button>
                </div>
              </>
            ) : (
              <div className="rounded-xl bg-slate-800/40 border border-slate-700/30 p-4 text-center">
                <p className="text-xs text-slate-500">Run your first analysis to see AI insights here.</p>
                <button
                  onClick={() => onNavigate('repos')}
                  className="mt-3 text-xs text-blue-400 hover:underline"
                >
                  Go to Repositories →
                </button>
              </div>
            )}

            {/* Trend sparkline placeholder */}
            <div className="mt-3">
              <p className="text-[10px] font-semibold text-slate-500 mb-2">Trends (Last 7 Days)</p>
              <TrendLine />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Inline placeholder icons
function FolderGit({ size }: { size: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/></svg>;
}

function FlaskIcon({ size }: { size: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2v6l-2 10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2L18 8V2"/><path d="M6 2h12"/><path d="M5 12h14"/></svg>;
}

function TrendLine() {
  const points = [25, 40, 35, 60, 50, 70, 82];
  const h = 48, w = 200;
  const min = Math.min(...points), max = Math.max(...points);
  const toX = (i: number) => (i / (points.length - 1)) * w;
  const toY = (v: number) => h - ((v - min) / (max - min)) * h;
  const d = points.map((v, i) => `${i === 0 ? 'M' : 'L'} ${toX(i)} ${toY(v)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: 48 }}>
      <path d={d} fill="none" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      {points.map((v, i) => (
        <circle key={i} cx={toX(i)} cy={toY(v)} r="2.5" fill="#3b82f6" />
      ))}
    </svg>
  );
}
