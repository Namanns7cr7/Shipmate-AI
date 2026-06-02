import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, AlertTriangle, ExternalLink, ArrowUpRight } from 'lucide-react';
import type { GitHubUser, GitHubRepo, ShipMateReport } from '../types';
import type { Page } from '../components/app/AppSidebar';

const REC: Record<string, { label: string; cls: string }> = {
  ready_to_ship: { label: 'Ready to Ship',     cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25' },
  mostly_ready:  { label: 'Mostly Ready',      cls: 'bg-blue-500/15    text-blue-300    border-blue-500/25' },
  needs_review:  { label: 'Needs Review',      cls: 'bg-yellow-500/15  text-yellow-300  border-yellow-500/25' },
  risky_release: { label: 'Needs Improvement', cls: 'bg-orange-500/15  text-orange-300  border-orange-500/25' },
  not_ready:     { label: 'Needs Work',        cls: 'bg-red-500/15     text-red-300     border-red-500/25' },
};

interface StatCardProps {
  value: string | number;
  label: string;
  change: string;
  up: boolean;
  accent: string;
  icon: string;
}

function StatCard({ value, label, change, up, accent, icon }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl p-5 flex flex-col gap-3 border border-white/5"
      style={{ background: 'rgba(13,20,40,0.8)' }}
    >
      <div className="flex items-center justify-between">
        <span className={`w-9 h-9 rounded-xl flex items-center justify-center text-lg ${accent}`}>{icon}</span>
        <span className={`text-xs font-semibold flex items-center gap-1 ${up ? 'text-emerald-400' : 'text-red-400'}`}>
          {up ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
          {change}
        </span>
      </div>
      <div>
        <p className="text-2xl font-black text-white">{value}</p>
        <p className="text-xs text-slate-500 mt-0.5">{label}</p>
      </div>
    </motion.div>
  );
}

function ScorePill({ score }: { score: number }) {
  const cls = score >= 80 ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
    : score >= 60 ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
    : score >= 40 ? 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'
    : 'bg-red-500/20 text-red-300 border-red-500/30';
  return <span className={`inline-flex items-center justify-center h-6 w-10 rounded-full text-xs font-black border ${cls}`}>{score}</span>;
}

interface Props {
  user: GitHubUser | null;
  repos: GitHubRepo[];
  report: ShipMateReport | null;
  onNavigate: (p: Page) => void;
}

export function DashboardPage({ user, repos, report, onNavigate }: Props) {
  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 17 ? 'Good afternoon' : 'Good evening';
  const name = user?.name?.split(' ')[0] || user?.login || 'Developer';

  const tableRows = repos.slice(0, 6).map((r, i) => ({
    name: r.full_name,
    score: report && i === 0 ? report.readiness_score : null,
    rec: report && i === 0 ? report.ship_recommendation : null,
    ago: ['5 min ago', '1 day ago', '3 days ago', '5 days ago', '1 week ago', '1 week ago'][i] ?? '—',
  }));

  return (
    <div className="px-8 py-7 max-w-[1080px] space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-black text-white tracking-tight">
            {greeting}, {name}! 👋
          </h1>
          <p className="text-sm text-slate-500 mt-1">Here's what's happening with your projects today.</p>
        </div>
        <button
          onClick={() => onNavigate('reports')}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-white px-4 py-2 rounded-xl border border-white/8 hover:border-white/15 transition-all"
        >
          <ArrowUpRight size={14} /> View Reports
        </button>
      </motion.div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard value={repos.length || 24} label="Total Repositories"    change="↑ 12% from last week" up icon="📁" accent="bg-blue-500/15"   />
        <StatCard value={58}                  label="Analyses Performed"    change="↑ 38% from last week" up icon="⚡" accent="bg-purple-500/15" />
        <StatCard value={report?.readiness_score ?? 82} label="Avg Readiness Score" change="↑ 6% from last week" up icon="📊" accent="bg-emerald-500/15" />
        <StatCard value={7}                   label="Critical Risks Found"  change="↓ 3% from last week"  up={false} icon="🛡" accent="bg-red-500/15"     />
      </div>

      {/* Table + Insights */}
      <div className="grid lg:grid-cols-[1fr_300px] gap-5">
        {/* Recent analyses */}
        <div className="rounded-2xl border border-white/6 overflow-hidden" style={{ background: 'rgba(11,18,35,0.9)' }}>
          <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
            <h2 className="text-sm font-bold text-white">Recent Analyses</h2>
            <button onClick={() => onNavigate('repos')} className="text-xs text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1">
              View All <ExternalLink size={10} />
            </button>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                {['Repository', 'Score', 'Status', 'Analyzed'].map(h => (
                  <th key={h} className="text-left text-[10px] font-semibold uppercase tracking-wider text-slate-600 px-5 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/4">
              {tableRows.length > 0 ? tableRows.map((row, i) => {
                const badge = row.rec ? REC[row.rec] : null;
                return (
                  <tr key={i} className="group hover:bg-white/3 transition-colors cursor-pointer" onClick={() => row.rec && onNavigate('reports')}>
                    <td className="px-5 py-3.5">
                      <span className="text-[13px] font-medium text-slate-300 group-hover:text-white transition-colors truncate block max-w-[180px]">{row.name}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      {row.score !== null ? <ScorePill score={row.score} /> : <span className="text-xs text-slate-600">—</span>}
                    </td>
                    <td className="px-5 py-3.5">
                      {badge
                        ? <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${badge.cls}`}>{badge.label}</span>
                        : <span className="text-[11px] text-slate-600 px-2.5 py-1 rounded-full border border-white/5 bg-white/3">Not analyzed</span>
                      }
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-500 whitespace-nowrap">{row.ago}</td>
                  </tr>
                );
              }) : (
                <tr><td colSpan={4} className="px-5 py-10 text-center text-sm text-slate-600">
                  No repos yet. <button onClick={() => onNavigate('repos')} className="text-blue-400 hover:underline">Connect one →</button>
                </td></tr>
              )}
            </tbody>
          </table>
          {tableRows.length > 0 && (
            <div className="px-5 py-3 border-t border-white/5">
              <button onClick={() => onNavigate('repos')} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">View all analyses →</button>
            </div>
          )}
        </div>

        {/* AI Insights */}
        <div className="space-y-4">
          <div className="rounded-2xl border border-white/6 p-5" style={{ background: 'rgba(11,18,35,0.9)' }}>
            <h2 className="text-sm font-bold text-white mb-4">AI Insights</h2>
            {report ? (
              <div className="space-y-3">
                <div className="rounded-xl p-3.5" style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}>
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle size={11} className="text-red-400" />
                    <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider">Highest Risk Repository</span>
                  </div>
                  <p className="text-xs font-bold text-white">{report.repo.full_name}</p>
                  {report.key_blockers[0] && (
                    <>
                      <p className="text-[10px] text-orange-300 mt-2 font-semibold">Critical Issue</p>
                      <p className="text-[10px] text-slate-400 mt-0.5 leading-relaxed">{report.key_blockers[0]}</p>
                    </>
                  )}
                  {report.next_actions[0] && (
                    <>
                      <p className="text-[10px] text-emerald-300 mt-2 font-semibold">Recommendation</p>
                      <p className="text-[10px] text-slate-400 mt-0.5 leading-relaxed">{report.next_actions[0]}</p>
                    </>
                  )}
                  <button onClick={() => onNavigate('reports')} className="mt-3 w-full py-1.5 rounded-lg text-xs font-bold text-white transition-colors" style={{ background: 'linear-gradient(135deg,#1d4ed8,#0891b2)' }}>
                    View Analysis
                  </button>
                </div>
              </div>
            ) : (
              <div className="rounded-xl p-4 text-center border border-white/5 bg-white/2">
                <p className="text-xs text-slate-500 mb-3">Run your first analysis to see AI insights.</p>
                <button onClick={() => onNavigate('repos')} className="text-xs text-blue-400 hover:underline">Go to Repositories →</button>
              </div>
            )}
          </div>

          {/* Trend chart */}
          <div className="rounded-2xl border border-white/6 p-5" style={{ background: 'rgba(11,18,35,0.9)' }}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Trends (Last 7 Days)</h3>
            </div>
            <div className="flex items-end gap-1 h-14">
              {[40, 55, 48, 70, 65, 78, 82].map((v, i) => (
                <div key={i} className="flex-1 rounded-t-sm transition-all" style={{ height: `${v}%`, background: i === 6 ? 'linear-gradient(180deg,#3b82f6,#1d4ed8)' : 'rgba(59,130,246,0.2)' }} />
              ))}
            </div>
            <div className="flex justify-between text-[9px] text-slate-600 mt-1">
              {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((d, i) => <span key={i}>{d}</span>)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
