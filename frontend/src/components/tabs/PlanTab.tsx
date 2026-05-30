import { motion } from 'framer-motion';
import type { PlannerOutput, Task } from '../../types';
import { AlertTriangle, Layers, Server, Database, TestTube, Rocket } from 'lucide-react';

function priorityColor(p: string) {
  if (p === 'high') return '#f87171';
  if (p === 'medium') return '#fbbf24';
  return '#34d399';
}

function effortBadge(e: string) {
  const colors: Record<string, string> = { S: '#34d399', M: '#60a5fa', L: '#a78bfa', XL: '#f87171' };
  return colors[e] || '#60a5fa';
}

function TaskCard({ task, index }: { task: Task; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      style={{
        padding: '14px 16px',
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(99, 179, 237, 0.08)',
        borderRadius: 10,
        marginBottom: 8,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <span style={{
            padding: '2px 8px', borderRadius: 6,
            fontSize: 10, fontWeight: 700, letterSpacing: '0.04em',
            background: `${priorityColor(task.priority)}20`,
            color: priorityColor(task.priority),
            border: `1px solid ${priorityColor(task.priority)}30`,
          }}>
            {task.priority.toUpperCase()}
          </span>
          <span style={{
            padding: '2px 8px', borderRadius: 6,
            fontSize: 10, fontWeight: 700,
            background: `${effortBadge(task.effort)}20`,
            color: effortBadge(task.effort),
            border: `1px solid ${effortBadge(task.effort)}30`,
          }}>
            {task.effort}
          </span>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 13, color: '#e2e8f0', marginBottom: 4 }}>
            <span style={{ color: '#4a6180', marginRight: 8, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>[{task.id}]</span>
            {task.title}
          </div>
          <div style={{ fontSize: 12, color: '#4a6180', lineHeight: 1.5 }}>{task.description}</div>
        </div>
      </div>
    </motion.div>
  );
}

function Section({ icon: Icon, title, color, tasks }: { icon: any; title: string; color: string; tasks: Task[] }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: `${color}15`,
          border: `1px solid ${color}30`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={14} color={color} />
        </div>
        <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>{title}</span>
        <span style={{
          padding: '2px 8px', borderRadius: 10,
          fontSize: 11, fontWeight: 600,
          background: `${color}15`, color,
        }}>
          {tasks.length} tasks
        </span>
      </div>
      {tasks.map((task, i) => <TaskCard key={task.id} task={task} index={i} />)}
    </div>
  );
}

export function PlanTab({ data }: { data: PlannerOutput }) {
  return (
    <div>
      {/* Stats row */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        {[
          { label: 'Story Points', value: data.total_story_points, color: '#60a5fa' },
          { label: 'Recommended Sprints', value: data.recommended_sprint_count, color: '#a78bfa' },
          { label: 'Total Tasks', value: data.frontend_tasks.length + data.backend_tasks.length + data.database_changes.length + data.test_requirements.length, color: '#34d399' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            flex: 1, minWidth: 120,
            padding: '16px', borderRadius: 12,
            background: `${color}08`,
            border: `1px solid ${color}20`,
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 28, fontWeight: 900, color }}>{value}</div>
            <div style={{ fontSize: 11, color: '#4a6180', marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>

      <Section icon={Layers} title="Frontend Tasks" color="#60a5fa" tasks={data.frontend_tasks} />
      <Section icon={Server} title="Backend Tasks" color="#a78bfa" tasks={data.backend_tasks} />
      <Section icon={Database} title="Database Changes" color="#34d399" tasks={data.database_changes} />
      <Section icon={TestTube} title="Test Requirements" color="#fbbf24" tasks={data.test_requirements} />

      {/* Deployment risks */}
      <div style={{ marginTop: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <AlertTriangle size={16} color="#f87171" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Deployment Risks</span>
        </div>
        {data.deployment_risks.map((risk, i) => (
          <div key={i} style={{
            padding: '10px 14px',
            background: 'rgba(239, 68, 68, 0.05)',
            border: '1px solid rgba(239, 68, 68, 0.15)',
            borderRadius: 8, marginBottom: 6,
            fontSize: 12, color: '#fca5a5', lineHeight: 1.5,
          }}>
            {risk}
          </div>
        ))}
      </div>
    </div>
  );
}
