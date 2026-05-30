import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, Clock, Loader, AlertCircle, Brain, Search, TestTube, Shield, Truck } from 'lucide-react';
import type { AgentState } from '../types';

const AGENT_ICONS = {
  planner: Brain,
  repo_analyst: Search,
  test_generator: TestTube,
  security_guard: Shield,
  delivery_manager: Truck,
};

const AGENT_COLORS = {
  planner: '#60a5fa',
  repo_analyst: '#a78bfa',
  test_generator: '#34d399',
  security_guard: '#f87171',
  delivery_manager: '#fbbf24',
};

interface AgentCardProps {
  agent: AgentState;
  index: number;
}

function StatusIcon({ status }: { status: AgentState['status'] }) {
  if (status === 'idle') return <Clock size={16} color="#4a6180" />;
  if (status === 'running') return (
    <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
      <Loader size={16} color="#06b6d4" />
    </motion.div>
  );
  if (status === 'complete') return <CheckCircle size={16} color="#10b981" />;
  return <AlertCircle size={16} color="#ef4444" />;
}

function AgentCard({ agent, index }: AgentCardProps) {
  const Icon = AGENT_ICONS[agent.name];
  const color = AGENT_COLORS[agent.name];
  const isRunning = agent.status === 'running';
  const isComplete = agent.status === 'complete';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      style={{
        position: 'relative',
        padding: '20px',
        background: isComplete
          ? `rgba(${color === '#34d399' ? '16, 185, 129' : color === '#60a5fa' ? '59, 130, 246' : color === '#a78bfa' ? '139, 92, 246' : color === '#f87171' ? '239, 68, 68' : '245, 158, 11'}, 0.07)`
          : isRunning
          ? 'rgba(6, 182, 212, 0.06)'
          : 'rgba(17, 24, 39, 0.7)',
        border: isRunning
          ? '1px solid rgba(6, 182, 212, 0.35)'
          : isComplete
          ? `1px solid ${color}35`
          : '1px solid rgba(99, 179, 237, 0.08)',
        borderRadius: 14,
        overflow: 'hidden',
        transition: 'all 0.4s',
      }}
    >
      {/* Animated scan line for running state */}
      <AnimatePresence>
        {isRunning && (
          <motion.div
            initial={{ top: '-2px' }}
            animate={{ top: '102%' }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
            style={{
              position: 'absolute',
              left: 0, right: 0,
              height: 2,
              background: 'linear-gradient(90deg, transparent, #06b6d4, transparent)',
              zIndex: 2,
            }}
          />
        )}
      </AnimatePresence>

      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        {/* Icon with glow */}
        <div style={{
          width: 44, height: 44, flexShrink: 0,
          borderRadius: 12,
          background: isComplete ? `${color}20` : 'rgba(99, 179, 237, 0.06)',
          border: `1px solid ${isComplete ? color + '40' : 'rgba(99, 179, 237, 0.1)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: isComplete ? `0 0 16px ${color}30` : isRunning ? '0 0 16px rgba(6, 182, 212, 0.3)' : 'none',
          transition: 'all 0.4s',
        }}>
          <Icon size={20} color={isComplete ? color : isRunning ? '#06b6d4' : '#4a6180'} />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{
              fontWeight: 600, fontSize: 14,
              color: isComplete ? color : isRunning ? '#93c5fd' : '#8ba3c1',
              transition: 'color 0.3s',
            }}>
              {agent.label}
            </span>
            <StatusIcon status={agent.status} />
          </div>

          <p style={{ fontSize: 12, color: '#4a6180', lineHeight: 1.5, marginBottom: 10 }}>
            {agent.description}
          </p>

          {/* Progress bar */}
          <div style={{ height: 3, background: 'rgba(255,255,255,0.05)', borderRadius: 2 }}>
            {isComplete && (
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: '100%' }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
                style={{ height: '100%', background: color, borderRadius: 2, boxShadow: `0 0 8px ${color}` }}
              />
            )}
            {isRunning && (
              <motion.div
                animate={{ x: ['-100%', '200%'] }}
                transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
                style={{ height: '100%', width: '40%', background: 'linear-gradient(90deg, transparent, #06b6d4, transparent)', borderRadius: 2 }}
              />
            )}
          </div>

          {/* Status label */}
          <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            {isRunning && (
              <motion.span
                animate={{ opacity: [1, 0.4, 1] }}
                transition={{ duration: 1.2, repeat: Infinity }}
                style={{ fontSize: 11, color: '#06b6d4', fontWeight: 600 }}
              >
                ● Processing...
              </motion.span>
            )}
            {isComplete && (
              <span style={{ fontSize: 11, color: '#10b981', fontWeight: 600 }}>✓ Complete</span>
            )}
            {agent.status === 'idle' && (
              <span style={{ fontSize: 11, color: '#4a6180' }}>Waiting in queue</span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

interface AgentSwarmProps {
  agents: AgentState[];
}

export function AgentSwarm({ agents }: AgentSwarmProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {agents.map((agent, i) => (
        <AgentCard key={agent.name} agent={agent} index={i} />
      ))}
    </div>
  );
}
