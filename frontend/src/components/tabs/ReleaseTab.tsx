import { motion } from 'framer-motion';
import type { DeliveryManagerOutput } from '../../types';
import { CalendarDays, MessageSquare, GitPullRequest, Workflow, Zap, ChevronRight } from 'lucide-react';

export function ReleaseTab({ data }: { data: DeliveryManagerOutput }) {
  const score = data.release_readiness_score;
  const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <div>
      {/* Release score header */}
      <div style={{
        padding: '20px', marginBottom: 24,
        background: 'rgba(17, 24, 39, 0.6)',
        border: '1px solid rgba(99, 179, 237, 0.1)',
        borderRadius: 14,
        display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap',
      }}>
        <div style={{ textAlign: 'center', flexShrink: 0 }}>
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.1 }}
            style={{ fontSize: 48, fontWeight: 900, color: scoreColor, lineHeight: 1, textShadow: `0 0 30px ${scoreColor}60` }}
          >
            {score}
          </motion.div>
          <div style={{ fontSize: 11, color: '#4a6180', marginTop: 4 }}>Release Score / 100</div>
        </div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#f0f6ff', marginBottom: 4 }}>
            📅 Estimated Release: <span style={{ color: '#60a5fa' }}>{data.estimated_release_date}</span>
          </div>
          <div style={{ fontSize: 13, color: '#4a6180', lineHeight: 1.5 }}>
            Contingent on security sign-off and DevOps provisioning.
          </div>
        </div>
      </div>

      {/* Sprint plan */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <CalendarDays size={15} color="#60a5fa" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Sprint Plan</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {data.sprint_plan.map((sprint, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
              style={{
                padding: '16px',
                background: 'rgba(59, 130, 246, 0.05)',
                border: '1px solid rgba(59, 130, 246, 0.12)',
                borderRadius: 12,
              }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, color: '#93c5fd', marginBottom: 4 }}>
                {sprint.day}
              </div>
              <div style={{ fontSize: 11, color: '#4a6180', marginBottom: 10 }}>
                👤 {sprint.owner}
              </div>
              {sprint.tasks.map((task, j) => (
                <div key={j} style={{
                  display: 'flex', gap: 8,
                  padding: '5px 0',
                  borderBottom: j < sprint.tasks.length - 1 ? '1px solid rgba(99, 179, 237, 0.05)' : 'none',
                  fontSize: 12, color: '#8ba3c1',
                }}>
                  <ChevronRight size={12} color="#3b82f6" style={{ marginTop: 2, flexShrink: 0 }} />
                  {task}
                </div>
              ))}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Standup summary */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <MessageSquare size={15} color="#34d399" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Standup Summary</span>
        </div>
        <div style={{
          padding: '16px',
          background: 'rgba(52, 211, 153, 0.04)',
          border: '1px solid rgba(52, 211, 153, 0.12)',
          borderRadius: 12,
          fontSize: 12, color: '#8ba3c1', lineHeight: 1.8,
          whiteSpace: 'pre-wrap',
        }}>
          {data.standup_summary}
        </div>
      </div>

      {/* PR review summary */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <GitPullRequest size={15} color="#a78bfa" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>PR Review Summary</span>
        </div>
        <div style={{
          padding: '16px',
          background: 'rgba(139, 92, 246, 0.05)',
          border: '1px solid rgba(139, 92, 246, 0.15)',
          borderRadius: 12,
          fontSize: 12, color: '#8ba3c1', lineHeight: 1.8,
          whiteSpace: 'pre-wrap',
        }}>
          {data.pr_review_summary}
        </div>
      </div>

      {/* CI/CD recommendations */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Workflow size={15} color="#06b6d4" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>CI/CD Recommendations</span>
        </div>
        {data.cicd_recommendations.map((rec, i) => (
          <div key={i} style={{
            padding: '10px 14px', marginBottom: 6,
            background: 'rgba(6, 182, 212, 0.04)',
            border: '1px solid rgba(6, 182, 212, 0.12)',
            borderRadius: 8, fontSize: 12, color: '#67e8f9', lineHeight: 1.5,
          }}>
            ⚙️ {rec}
          </div>
        ))}
      </div>

      {/* Next actions */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Zap size={15} color="#fbbf24" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Next Team Actions</span>
        </div>
        {data.next_actions.map((action, i) => (
          <div key={i} style={{
            padding: '10px 14px', marginBottom: 6,
            background: 'rgba(245, 158, 11, 0.05)',
            border: '1px solid rgba(245, 158, 11, 0.12)',
            borderRadius: 8, fontSize: 12, color: '#fde68a', lineHeight: 1.5,
          }}>
            {action}
          </div>
        ))}
      </div>
    </div>
  );
}
