import { motion } from 'framer-motion';
import type { AgentProgress } from '../types';

const STATUS_STYLES: Record<string, { ring: string; dot: string; label: string; labelColor: string }> = {
  idle:     { ring: 'ring-slate-700', dot: 'bg-slate-600', label: 'Waiting', labelColor: 'text-slate-500' },
  running:  { ring: 'ring-blue-500/60', dot: 'bg-blue-400', label: 'Running', labelColor: 'text-blue-400' },
  complete: { ring: 'ring-emerald-500/60', dot: 'bg-emerald-400', label: 'Done', labelColor: 'text-emerald-400' },
  error:    { ring: 'ring-red-500/60', dot: 'bg-red-400', label: 'Error', labelColor: 'text-red-400' },
};

export function AgentSwarm({ agents }: { agents: AgentProgress[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {agents.map((agent, i) => {
        const s = STATUS_STYLES[agent.status];
        return (
          <motion.div
            key={agent.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className={`rounded-xl p-4 bg-slate-800/60 border border-slate-700/40 ring-1 ${s.ring} transition-all`}
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{agent.icon}</span>
              {agent.status === 'running' ? (
                <motion.span
                  className={`w-2 h-2 rounded-full ${s.dot}`}
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
              ) : (
                <span className={`w-2 h-2 rounded-full ${s.dot}`} />
              )}
            </div>
            <p className="text-sm font-semibold text-slate-100 leading-tight">{agent.label}</p>
            <p className="text-xs text-slate-500 mt-1 leading-snug">{agent.description}</p>
            <p className={`text-xs font-medium mt-2 ${s.labelColor}`}>{s.label}</p>
          </motion.div>
        );
      })}
    </div>
  );
}
