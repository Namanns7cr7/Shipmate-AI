import { motion } from 'framer-motion';
import {
  LayoutDashboard, FolderGit2, FlaskConical, FileText,
  Lightbulb, Settings, ChevronDown,
} from 'lucide-react';
import type { GitHubUser } from '../../types';

export type Page = 'dashboard' | 'repos' | 'analysis' | 'reports';

const NAV = [
  { id: 'dashboard' as Page, label: 'Dashboard',    Icon: LayoutDashboard },
  { id: 'repos'     as Page, label: 'Repositories', Icon: FolderGit2 },
  { id: 'analysis'  as Page, label: 'Analyses',     Icon: FlaskConical },
  { id: 'reports'   as Page, label: 'Reports',      Icon: FileText },
  { id: null,                label: 'Insights',     Icon: Lightbulb, disabled: true },
  { id: null,                label: 'Settings',     Icon: Settings,  disabled: true },
];

interface Props {
  activePage: Page;
  onNavigate: (p: Page) => void;
  user: GitHubUser | null;
  onLogout: () => void;
}

export function AppSidebar({ activePage, onNavigate, user, onLogout }: Props) {
  return (
    <aside
      className="flex flex-col w-[220px] flex-shrink-0 bg-[#070d1a] border-r border-slate-800/50"
      style={{ minHeight: '100vh' }}
    >
      {/* Logo */}
      <div className="px-5 py-5 border-b border-slate-800/50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center text-base flex-shrink-0">
            🚢
          </div>
          <div>
            <p className="text-sm font-black text-white leading-none">ShipMate AI</p>
            <p className="text-[10px] text-slate-500 mt-0.5 leading-none">Production Readiness</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV.map(item => {
          if (item.disabled || item.id === null) {
            return (
              <div
                key={item.label}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 cursor-not-allowed"
              >
                <item.Icon size={16} />
                <span className="text-sm">{item.label}</span>
              </div>
            );
          }
          const isActive = activePage === item.id;
          return (
            <motion.button
              key={item.id}
              onClick={() => onNavigate(item.id!)}
              whileHover={{ x: 2 }}
              whileTap={{ scale: 0.98 }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                isActive
                  ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <item.Icon size={16} className={isActive ? 'text-blue-400' : ''} />
              {item.label}
            </motion.button>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="px-3 pb-4 space-y-3 border-t border-slate-800/50 pt-3">
        {/* System status */}
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/5 border border-emerald-500/15">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse flex-shrink-0" />
          <div>
            <p className="text-[10px] font-semibold text-emerald-400">All Systems</p>
            <p className="text-[10px] text-slate-500">Operational</p>
          </div>
        </div>

        {/* User profile */}
        {user && (
          <button
            onClick={onLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-800/50 transition-colors group"
          >
            <img
              src={user.avatar_url}
              alt={user.login}
              className="w-7 h-7 rounded-full ring-1 ring-slate-700 flex-shrink-0"
            />
            <div className="flex-1 min-w-0 text-left">
              <p className="text-xs font-semibold text-slate-200 truncate">{user.name || user.login}</p>
              <p className="text-[10px] text-slate-500 truncate">Developer</p>
            </div>
            <ChevronDown size={12} className="text-slate-600 group-hover:text-slate-400 flex-shrink-0" />
          </button>
        )}
      </div>
    </aside>
  );
}
