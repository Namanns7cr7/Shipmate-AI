import { LogOut } from 'lucide-react';
import { motion } from 'framer-motion';
import type { GitHubUser } from '../types';

// Inline GitHub icon (not available in lucide-react)
function GithubIcon({ size = 24, className = '' }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}


interface GitHubUserProfileProps {
  user: GitHubUser;
  onLogout: () => void;
  loading?: boolean;
}

export function GitHubUserProfile({
  user,
  onLogout,
  loading = false,
}: GitHubUserProfileProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-4 rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-3"
    >
      {/* Avatar */}
      <img
        src={user.avatar_url}
        alt={user.login}
        className="h-10 w-10 rounded-full border-2 border-blue-400"
      />

      {/* User Info */}
      <div className="flex-1 min-w-0">
        <p className="truncate font-semibold text-white">{user.name || user.login}</p>
        <p className="truncate text-xs text-slate-400">@{user.login}</p>
      </div>

      {/* GitHub Link */}
      <a
        href={user.html_url}
        target="_blank"
        rel="noopener noreferrer"
        className="p-2 text-slate-400 hover:text-white transition"
        title="Open GitHub profile"
      >
        <GithubIcon size={18} />
      </a>

      {/* Logout Button */}
      <button
        onClick={onLogout}
        disabled={loading}
        className="flex items-center gap-2 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-400 hover:bg-red-500/20 transition disabled:opacity-50 disabled:cursor-not-allowed"
        title="Logout from GitHub"
      >
        <LogOut size={16} />
        <span className="hidden sm:inline">Logout</span>
      </button>
    </motion.div>
  );
}
