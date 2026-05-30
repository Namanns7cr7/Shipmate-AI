import { motion } from 'framer-motion';
import { useState } from 'react';
import type { TestGeneratorOutput, TestCase } from '../../types';
import { CheckSquare, FlaskConical, Zap, RotateCcw } from 'lucide-react';

function TestCaseCard({ test, index }: { test: TestCase; index: number }) {
  const [open, setOpen] = useState(false);
  const typeColors: Record<string, string> = {
    unit: '#60a5fa',
    integration: '#a78bfa',
    e2e: '#34d399',
    security: '#f87171',
  };
  const color = typeColors[test.type] || '#60a5fa';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      style={{
        marginBottom: 8,
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(99, 179, 237, 0.08)',
        borderRadius: 10,
        overflow: 'hidden',
      }}
    >
      <div
        onClick={() => setOpen(!open)}
        style={{
          padding: '12px 16px',
          cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 12,
          transition: 'background 0.15s',
        }}
      >
        <span style={{
          padding: '2px 8px', borderRadius: 6, fontSize: 10, fontWeight: 700,
          background: `${color}15`, color, border: `1px solid ${color}25`, flexShrink: 0,
        }}>
          {test.type.toUpperCase()}
        </span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#93c5fd', flex: 1 }}>
          {test.name}
        </span>
        <span style={{ fontSize: 11, color: '#4a6180' }}>{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          transition={{ duration: 0.2 }}
          style={{
            padding: '0 16px 14px',
            borderTop: '1px solid rgba(99, 179, 237, 0.06)',
          }}
        >
          <p style={{ fontSize: 12, color: '#4a6180', lineHeight: 1.5, margin: '12px 0 10px' }}>
            {test.description}
          </p>
          <div style={{ fontSize: 11, color: '#4a6180', fontWeight: 600, marginBottom: 6 }}>ASSERTIONS:</div>
          {test.assertions.map((a, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 4, fontSize: 12, color: '#8ba3c1' }}>
              <span style={{ color: '#34d399', flexShrink: 0 }}>☐</span>
              {a}
            </div>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}

export function TestsTab({ data }: { data: TestGeneratorOutput }) {
  return (
    <div>
      {/* Coverage meter */}
      <div style={{
        padding: '16px 20px',
        background: 'rgba(52, 211, 153, 0.06)',
        border: '1px solid rgba(52, 211, 153, 0.2)',
        borderRadius: 14,
        marginBottom: 24,
        display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 32, fontWeight: 900, color: '#34d399' }}>{data.total_coverage_estimate}%</div>
          <div style={{ fontSize: 11, color: '#4a6180' }}>Estimated Coverage</div>
        </div>
        <div style={{ flex: 1, minWidth: 150 }}>
          <div style={{ height: 8, background: 'rgba(255,255,255,0.05)', borderRadius: 4, marginBottom: 8 }}>
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${data.total_coverage_estimate}%` }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
              style={{
                height: '100%', borderRadius: 4,
                background: data.total_coverage_estimate >= 80 ? '#10b981' : data.total_coverage_estimate >= 60 ? '#f59e0b' : '#ef4444',
                boxShadow: '0 0 8px rgba(52, 211, 153, 0.4)',
              }}
            />
          </div>
          <div style={{ fontSize: 12, color: '#4a6180' }}>
            {data.unit_tests.length + data.api_tests.length + data.edge_cases.length} total test cases generated
          </div>
        </div>
      </div>

      {/* Unit tests */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Zap size={15} color="#60a5fa" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Unit Tests</span>
          <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: 11, background: 'rgba(96, 165, 250, 0.1)', color: '#60a5fa' }}>
            {data.unit_tests.length}
          </span>
        </div>
        {data.unit_tests.map((t, i) => <TestCaseCard key={t.id} test={t} index={i} />)}
      </div>

      {/* API tests */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <FlaskConical size={15} color="#a78bfa" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>API Integration Tests</span>
          <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: 11, background: 'rgba(167, 139, 250, 0.1)', color: '#a78bfa' }}>
            {data.api_tests.length}
          </span>
        </div>
        {data.api_tests.map((t, i) => <TestCaseCard key={t.id} test={t} index={i} />)}
      </div>

      {/* Edge cases */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Zap size={15} color="#fbbf24" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Edge Cases</span>
          <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: 11, background: 'rgba(251, 191, 36, 0.1)', color: '#fbbf24' }}>
            {data.edge_cases.length}
          </span>
        </div>
        {data.edge_cases.map((t, i) => <TestCaseCard key={t.id} test={t} index={i} />)}
      </div>

      {/* Regression checklist */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <RotateCcw size={15} color="#06b6d4" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#e2e8f0' }}>Regression Checklist</span>
        </div>
        {data.regression_checklist.map((item, i) => (
          <div key={i} style={{
            padding: '8px 12px', marginBottom: 6,
            background: 'rgba(6, 182, 212, 0.04)',
            border: '1px solid rgba(6, 182, 212, 0.12)',
            borderRadius: 8, fontSize: 12, color: '#67e8f9',
          }}>
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
