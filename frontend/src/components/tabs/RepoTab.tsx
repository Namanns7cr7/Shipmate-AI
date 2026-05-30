import { motion } from 'framer-motion';
import type { RepoAnalystOutput } from '../../types';
import { FileCode, AlertTriangle, Package, Lightbulb, Activity } from 'lucide-react';

function riskColor(risk: string) {
  if (risk === 'high') return '#f87171';
  if (risk === 'medium') return '#fbbf24';
  return '#34d399';
}

function changeTypeColor(ct: string) {
  if (ct === 'create') return '#34d399';
  if (ct === 'delete') return '#f87171';
  return '#60a5fa';
}

export function RepoTab({ data }: { data: RepoAnalystOutput }) {
  return (
    <div>
      {/* Architecture notes */}
      <div style={{
        padding: '16px',
        background: 'rgba(59, 130, 246, 0.06)',
        border: '1px solid rgba(59, 130, 246, 0.15)',
        borderRadius: 12,
        marginBottom: 24,
        fontSize: 13, color: '#93c5fd', lineHeight: 1.7,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, fontWeight: 600, fontSize: 13, color: '#60a5fa' }}>
          <Activity size={14} /> Architecture Notes
        </div>
        {data.architecture_notes}
      </div>

      {/* Impact score */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <div style={{
          padding: '12px 20px',
          background: 'rgba(139, 92, 246, 0.1)',
          border: '1px solid rgba(139, 92, 246, 0.25)',
          borderRadius: 12,
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span style={{ fontSize: 28, fontWeight: 900, color: '#a78bfa' }}>{data.impact_score}</span>
          <div>
            <div style={{ fontSize: 12, color: '#a78bfa', fontWeight: 600 }}>Impact Score</div>
            <div style={{ fontSize: 11, color: '#4a6180' }}>Repo change scope</div>
          </div>
        </div>
        <div style={{ fontSize: 13, color: '#4a6180' }}>
          {data.files_to_change.length} files affected · {data.affected_apis.length} APIs impacted · {data.risky_dependencies.length} risky deps
        </div>
      </div>

      {/* Files to change */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <FileCode size={15} color="#60a5fa" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Files Requiring Changes</span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr>
                {['File Path', 'Risk', 'Change', 'Reason'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '8px 12px',
                    color: '#4a6180', fontWeight: 600, fontSize: 11,
                    letterSpacing: '0.05em', textTransform: 'uppercase',
                    borderBottom: '1px solid rgba(99, 179, 237, 0.08)',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.files_to_change.map((file, i) => (
                <motion.tr
                  key={file.path}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  style={{ borderBottom: '1px solid rgba(99, 179, 237, 0.04)' }}
                >
                  <td style={{ padding: '10px 12px', fontFamily: 'JetBrains Mono, monospace', color: '#93c5fd', fontSize: 11 }}>
                    {file.path}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: 6,
                      fontSize: 10, fontWeight: 700,
                      background: `${riskColor(file.risk_level)}15`,
                      color: riskColor(file.risk_level),
                      border: `1px solid ${riskColor(file.risk_level)}30`,
                    }}>
                      {file.risk_level.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: 6,
                      fontSize: 10, fontWeight: 600,
                      color: changeTypeColor(file.change_type),
                    }}>
                      {file.change_type}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', color: '#4a6180', lineHeight: 1.4 }}>{file.reason}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Affected APIs */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Activity size={15} color="#34d399" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Affected APIs</span>
        </div>
        {data.affected_apis.map((api, i) => (
          <div key={i} style={{
            padding: '8px 12px', marginBottom: 6,
            background: 'rgba(52, 211, 153, 0.04)',
            border: '1px solid rgba(52, 211, 153, 0.12)',
            borderRadius: 8,
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 12, color: '#6ee7b7',
          }}>
            {api}
          </div>
        ))}
      </div>

      {/* Risky deps */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Package size={15} color="#f87171" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Risky Dependencies</span>
        </div>
        {data.risky_dependencies.map((dep, i) => (
          <div key={i} style={{
            padding: '8px 12px', marginBottom: 6,
            background: 'rgba(239, 68, 68, 0.05)',
            border: '1px solid rgba(239, 68, 68, 0.15)',
            borderRadius: 8, fontSize: 12, color: '#fca5a5',
          }}>
            ⚠️ {dep}
          </div>
        ))}
      </div>

      {/* Patterns */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Lightbulb size={15} color="#fbbf24" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Patterns to Follow</span>
        </div>
        {data.patterns_to_follow.map((pattern, i) => (
          <div key={i} style={{
            padding: '8px 12px', marginBottom: 6,
            background: 'rgba(245, 158, 11, 0.05)',
            border: '1px solid rgba(245, 158, 11, 0.12)',
            borderRadius: 8, fontSize: 12, color: '#fde68a',
          }}>
            💡 {pattern}
          </div>
        ))}
      </div>
    </div>
  );
}
