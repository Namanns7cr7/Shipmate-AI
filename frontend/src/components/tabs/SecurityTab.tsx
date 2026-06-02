import { motion } from 'framer-motion';
import type { SecurityGuardOutput, SecurityRisk } from '../../types';
import { AlertTriangle, Key, Terminal, Lock, Package, Siren } from 'lucide-react';

function severityConfig(sev: string) {
  const map: Record<string, { color: string; bg: string; icon: string }> = {
    critical: { color: '#fca5a5', bg: 'rgba(220, 38, 38, 0.12)', icon: '🔴' },
    high: { color: '#fdba74', bg: 'rgba(234, 88, 12, 0.1)', icon: '🟠' },
    medium: { color: '#fde68a', bg: 'rgba(245, 158, 11, 0.08)', icon: '🟡' },
    low: { color: '#86efac', bg: 'rgba(34, 197, 94, 0.08)', icon: '🟢' },
  };
  return map[sev] || map.medium;
}

function RiskCard({ risk, index }: { risk: SecurityRisk; index: number }) {
  const { color, bg, icon } = severityConfig(risk.severity);
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      style={{
        padding: '16px', marginBottom: 12,
        background: bg,
        border: `1px solid ${color}25`,
        borderRadius: 12,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ flexShrink: 0 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
            <span style={{
              padding: '2px 10px', borderRadius: 20,
              fontSize: 10, fontWeight: 800, letterSpacing: '0.06em',
              background: `${color}20`, color,
              border: `1px solid ${color}40`,
            }}>
              {icon} {risk.severity.toUpperCase()}
            </span>
            <span style={{
              padding: '2px 10px', borderRadius: 20,
              fontSize: 10, fontWeight: 600, color: '#8ba3c1',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
            }}>
              {risk.category}
            </span>
            {risk.cve_reference && (
              <span style={{
                padding: '2px 10px', borderRadius: 20,
                fontSize: 10, fontWeight: 600, color: '#a78bfa',
                background: 'rgba(139, 92, 246, 0.1)',
                border: '1px solid rgba(139, 92, 246, 0.2)',
                fontFamily: 'JetBrains Mono, monospace',
              }}>
                {risk.cve_reference}
              </span>
            )}
          </div>
          <div style={{ fontWeight: 700, fontSize: 13, color: '#f0f6ff', marginBottom: 6 }}>
            [{risk.id}] {risk.title}
          </div>
          <p style={{ fontSize: 12, color: '#8ba3c1', lineHeight: 1.6, marginBottom: 8 }}>
            {risk.description}
          </p>
          <div style={{
            padding: '8px 12px',
            background: 'rgba(16, 185, 129, 0.06)',
            border: '1px solid rgba(16, 185, 129, 0.15)',
            borderRadius: 8, fontSize: 12, color: '#6ee7b7', lineHeight: 1.5,
          }}>
            💡 {risk.recommendation}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function ListSection({ icon: Icon, title, color, items }: { icon: any; title: string; color: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <Icon size={14} color={color} />
        <span style={{ fontWeight: 700, fontSize: 13, color: '#e2e8f0' }}>{title}</span>
      </div>
      {items.map((item, i) => (
        <div key={i} style={{
          padding: '8px 12px', marginBottom: 5,
          background: `${color}06`,
          border: `1px solid ${color}18`,
          borderRadius: 8, fontSize: 12, color: '#8ba3c1', lineHeight: 1.5,
        }}>
          {item}
        </div>
      ))}
    </div>
  );
}

export function SecurityTab({ data }: { data: SecurityGuardOutput }) {
  const criticalCount = data.risks.filter(r => r.severity === 'critical').length;
  const highCount = data.risks.filter(r => r.severity === 'high').length;

  return (
    <div>
      {/* Security score */}
      <div style={{
        display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap',
      }}>
        <div style={{
          flex: 1, minWidth: 100, padding: '16px', textAlign: 'center',
          background: criticalCount > 0 ? 'rgba(220, 38, 38, 0.1)' : 'rgba(16, 185, 129, 0.08)',
          border: criticalCount > 0 ? '1px solid rgba(220, 38, 38, 0.3)' : '1px solid rgba(16, 185, 129, 0.2)',
          borderRadius: 12,
        }}>
          <div style={{ fontSize: 26, fontWeight: 900, color: data.overall_security_score >= 80 ? '#10b981' : data.overall_security_score >= 60 ? '#f59e0b' : '#ef4444' }}>
            {data.overall_security_score}
          </div>
          <div style={{ fontSize: 11, color: '#4a6180' }}>Security Score</div>
        </div>
        {[
          { label: 'Critical', count: criticalCount, color: '#ef4444' },
          { label: 'High', count: highCount, color: '#f97316' },
          { label: 'Medium', count: data.risks.filter(r => r.severity === 'medium').length, color: '#f59e0b' },
          { label: 'Low', count: data.risks.filter(r => r.severity === 'low').length, color: '#10b981' },
        ].map(({ label, count, color }) => (
          <div key={label} style={{
            flex: 1, minWidth: 80, padding: '16px', textAlign: 'center',
            background: `${color}08`,
            border: `1px solid ${color}20`,
            borderRadius: 12,
          }}>
            <div style={{ fontSize: 24, fontWeight: 900, color }}>{count}</div>
            <div style={{ fontSize: 11, color: '#4a6180' }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Risk cards */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <Siren size={15} color="#f87171" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Security Risk Findings</span>
        </div>
        {data.risks.map((risk, i) => <RiskCard key={risk.id} risk={risk} index={i} />)}
      </div>

      {/* Additional findings */}
      <div style={{
        padding: '16px',
        background: 'rgba(17, 24, 39, 0.6)',
        border: '1px solid rgba(99, 179, 237, 0.08)',
        borderRadius: 14,
      }}>
        <ListSection icon={AlertTriangle} title="Prompt Injection Risks" color="#f87171" items={data.prompt_injection_risks} />
        <ListSection icon={Key} title="Exposed Secrets Detected" color="#f59e0b" items={data.exposed_secrets} />
        <ListSection icon={Terminal} title="Unsafe Tool Calls" color="#f97316" items={data.unsafe_tool_calls} />
        <ListSection icon={Lock} title="Auth Bypass Risks" color="#a78bfa" items={data.auth_bypass_risks} />
        <ListSection icon={Package} title="Dependency Vulnerabilities" color="#ef4444" items={data.dependency_warnings} />
      </div>
    </div>
  );
}
