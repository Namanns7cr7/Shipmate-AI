import { Loader } from 'lucide-react';
import { motion } from 'framer-motion';

// Inline GitHub icon (not available in lucide-react)
function GithubIcon({ size = 24, className = '' }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

interface GithubConnectButtonProps {
  onClick: () => void;
  loading?: boolean;
  error?: string | null;
}

export function GitHubConnectButton({
  onClick,
  loading = false,
  error = null,
}: GithubConnectButtonProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-4"
    >
      {/* Main Card */}
      <div className="rounded-lg border border-slate-800 bg-gradient-to-b from-slate-800/50 to-slate-900/50 p-8 text-center shadow-lg">
        <div className="mb-6 flex justify-center">
          <div className="rounded-full bg-blue-500/10 p-4">
            <GithubIcon size={48} className="text-blue-400" />
          </div>
        </div>

        <h2 className="mb-2 text-2xl font-bold text-white">
          Connect Your GitHub Account
        </h2>
        <p className="mb-6 text-slate-400">
          Analyze your real repositories with ShipMate AI. Get production readiness
          insights for your projects.
        </p>

        {error && (
          <div className="mb-4 rounded-lg bg-red-500/10 p-4 text-left">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        <button
          onClick={onClick}
          disabled={loading}
          className="group relative inline-flex items-center gap-3 rounded-lg bg-gradient-to-r from-blue-500 to-cyan-500 px-6 py-3 font-semibold text-white transition-all hover:shadow-lg hover:shadow-blue-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <Loader size={20} className="animate-spin" />
              <span>Connecting...</span>
            </>
          ) : (
            <>
              <GithubIcon size={20} />
              <span>Login with GitHub</span>
            </>
          )}
        </button>

        {/* Features List */}
        <div className="mt-8 space-y-3 border-t border-slate-700 pt-8">
          <div className="flex items-center gap-3">
            <div className="h-2 w-2 rounded-full bg-green-400" />
            <p className="text-sm text-slate-300">
              Access all your repositories
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-2 w-2 rounded-full bg-green-400" />
            <p className="text-sm text-slate-300">
              Real-time production readiness analysis
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-2 w-2 rounded-full bg-green-400" />
            <p className="text-sm text-slate-300">
              AI-powered recommendations
            </p>
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="rounded-lg bg-blue-500/5 p-4 border border-blue-500/20">
        <p className="text-xs text-blue-300">
          <span className="font-semibold">Why authenticate?</span> We use your
          GitHub credentials to analyze your actual repositories and provide
          personalized insights. Your data is secure and never shared.
        </p>
      </div>
    </motion.div>
  );
}
