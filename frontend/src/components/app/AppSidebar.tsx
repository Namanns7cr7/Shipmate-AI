import { motion } from 'framer-motion';
import {
  LayoutDashboard, FolderGit2, Activity, FileBarChart2,
  LineChart, Settings, ChevronDown, LogOut,
} from 'lucide-react';
import type { GitHubUser } from '../../types';

export type Page = 'dashboard' | 'repos' | 'analysis' | 'reports';

const NAV_ITEMS: { id: Page | null; label: string; Icon: React.ElementType; disabled?: boolean }[] = [
  { id: 'dashboard', label: 'Dashboard',    Icon: LayoutDashboard },
  { id: 'repos',     label: 'Repositories', Icon: FolderGit2 },
  { id: 'analysis',  label: 'Analyses',     Icon: Activity },
  { id: 'reports',   label: 'Reports',      Icon: FileBarChart2 },
  { id: null,        label: 'Insights',     Icon: LineChart,  disabled: true },
  { id: null,        label: 'Settings',     Icon: Settings,   disabled: true },
];

interface Props {
  activePage: Page;
  onNavigate: (p: Page) => void;
  user: GitHubUser | null;
  onLogout: () => void;
}

export function AppSidebar({ activePage, onNavigate, user, onLogout }: Props) {
  return (
    <aside className="flex flex-col w-56 flex-shrink-0 border-r border-white/5"
      style={{ background: 'linear-gradient(180deg, #070d1a 0%, #060b16 100%)', minHeight: '100vh' }}>

      {/* Brand */}
      <div className="px-5 pt-6 pb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center text-xl flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #1d4ed8, #0891b2)' }}>
            🚢
          </div>
          <div>
            <p className="text-[15px] font-black text-white leading-tight tracking-tight">ShipMate <span className="text-blue-400">AI</span></p>
            <p className="text-[10px] text-slate-500 leading-tight mt-0.5">Readiness Platform</p>
          </div>
        </div>
      </div>

      <div className="h-px bg-white/5 mx-3" />

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-0.5">
        {NAV_ITEMS.map((item, i) => {
          if (item.id === null || item.disabled) {
            return (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-slate-600 cursor-not-allowed select-none">
                <item.Icon size={15} />
                <span className="text-[13px]">{item.label}</span>
              </div>
            );
          }
          const isActive = activePage === item.id;
          return (
            <motion.button
              key={item.id}
              onClick={() => onNavigate(item.id!)}
              whileTap={{ scale: 0.97 }}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-150 ${
                isActive
                  ? 'text-white'
                  : 'text-slate-500 hover:text-slate-200 hover:bg-white/4'
              }`}
              style={isActive ? {
                background: 'linear-gradient(135deg, rgba(37,99,235,0.25), rgba(8,145,178,0.15))',
                border: '1px solid rgba(59,130,246,0.3)',
              } : {}}
            >
              <item.Icon size={15} className={isActive ? 'text-blue-400' : ''} />
              {item.label}
              {isActive && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400" />}
            </motion.button>
          );
        })}
      </nav>

      <div className="h-px bg-white/5 mx-3" />

      {/* Bottom */}
      <div className="px-2 py-4 space-y-2">
        {/* Status */}
        <div className="mx-2 flex items-center gap-2.5 px-3 py-2 rounded-xl"
          style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.12)' }}>
          <div className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" style={{ boxShadow: '0 0 6px #10b981' }} />
          <div>
            <p className="text-[10px] font-bold text-emerald-400 leading-none">All Systems</p>
            <p className="text-[10px] text-slate-600 leading-none mt-0.5">Operational</p>
          </div>
        </div>

        {/* User */}
        {user && (
          <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl hover:bg-white/4 transition-colors cursor-pointer group">
            <img src={user.avatar_url} alt="" className="w-7 h-7 rounded-full ring-1 ring-white/10 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-[12px] font-semibold text-slate-200 truncate leading-tight">{user.name || user.login}</p>
              <p className="text-[10px] text-slate-500 truncate leading-tight">Developer</p>
            </div>
            <button onClick={onLogout} className="p-1 rounded-lg text-slate-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100" title="Sign out">
              <LogOut size={12} />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

// Suppress unused import warning
const _ChevronDown = ChevronDown;
void _ChevronDown;
