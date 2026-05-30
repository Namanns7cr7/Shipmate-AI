import { motion } from 'framer-motion';
import { Zap, Activity, Shield, GitBranch, Cpu } from 'lucide-react';

const navItems = [
  { icon: Activity, label: 'Dashboard', active: true },
  { icon: GitBranch, label: 'Repo Analysis', active: false },
  { icon: Shield, label: 'Security', active: false },
  { icon: Cpu, label: 'Agents', active: false },
];

export function Sidebar() {
  return (
    <motion.aside
      initial={{ x: -280 }}
      animate={{ x: 0 }}
      transition={{ type: 'spring', stiffness: 100, damping: 20 }}
      style={{
        width: 260,
        minWidth: 260,
        height: '100vh',
        background: 'rgba(8, 12, 20, 0.95)',
        borderRight: '1px solid rgba(99, 179, 237, 0.08)',
        display: 'flex',
        flexDirection: 'column',
        position: 'fixed',
        left: 0,
        top: 0,
        zIndex: 100,
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Logo */}
      <div style={{ padding: '28px 24px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 40, height: 40,
            background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
            borderRadius: 12,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px rgba(59, 130, 246, 0.4)',
          }}>
            <Zap size={22} color="white" />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 17, letterSpacing: '-0.3px', color: '#f0f6ff' }}>
              ShipMate<span style={{ color: '#60a5fa' }}> AI</span>
            </div>
            <div style={{ fontSize: 10, color: '#4a6180', fontWeight: 500, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              Engineering Command
            </div>
          </div>
        </div>

        {/* Status pill */}
        <div style={{
          marginTop: 16,
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 12px',
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.2)',
          borderRadius: 20,
          width: 'fit-content',
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981', display: 'block', boxShadow: '0 0 8px #10b981' }} />
          <span style={{ fontSize: 11, color: '#34d399', fontWeight: 600, letterSpacing: '0.04em' }}>5 Agents Online</span>
        </div>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'rgba(99, 179, 237, 0.06)', margin: '0 24px' }} />

      {/* Nav label */}
      <div style={{ padding: '16px 24px 8px', fontSize: 10, color: '#4a6180', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
        Navigation
      </div>

      {/* Nav items */}
      <nav style={{ padding: '0 12px', flex: 1 }}>
        {navItems.map(({ icon: Icon, label, active }) => (
          <div
            key={label}
            style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 12px',
              borderRadius: 10,
              marginBottom: 4,
              cursor: 'pointer',
              background: active ? 'rgba(59, 130, 246, 0.12)' : 'transparent',
              border: active ? '1px solid rgba(59, 130, 246, 0.2)' : '1px solid transparent',
              color: active ? '#93c5fd' : '#4a6180',
              fontSize: 14,
              fontWeight: active ? 600 : 400,
              transition: 'all 0.15s',
            }}
          >
            <Icon size={16} />
            {label}
          </div>
        ))}
      </nav>

      {/* Agent roster */}
      <div style={{ margin: '0 12px 12px' }}>
        <div style={{ padding: '12px', fontSize: 10, color: '#4a6180', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Agent Swarm
        </div>
        {[
          { name: 'Planner', color: '#60a5fa' },
          { name: 'Repo Analyst', color: '#a78bfa' },
          { name: 'Test Generator', color: '#34d399' },
          { name: 'Security Guard', color: '#f87171' },
          { name: 'Delivery Mgr', color: '#fbbf24' },
        ].map(({ name, color }) => (
          <div key={name} style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '7px 12px',
            borderRadius: 8,
            marginBottom: 2,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, boxShadow: `0 0 6px ${color}` }} />
            <span style={{ fontSize: 12, color: '#8ba3c1' }}>{name}</span>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{
        padding: '16px 24px',
        borderTop: '1px solid rgba(99, 179, 237, 0.06)',
        fontSize: 11,
        color: '#4a6180',
        textAlign: 'center'
      }}>
        ShipMate AI · Hackathon MVP
      </div>
    </motion.aside>
  );
}
