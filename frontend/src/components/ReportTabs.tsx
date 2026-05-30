import { motion } from 'framer-motion';
import { useState } from 'react';
import type { AnalyzeResponse } from '../types';
import { PlanTab } from './tabs/PlanTab';
import { RepoTab } from './tabs/RepoTab';
import { TestsTab } from './tabs/TestsTab';
import { SecurityTab } from './tabs/SecurityTab';
import { ReleaseTab } from './tabs/ReleaseTab';
import { Download, FileText } from 'lucide-react';

const TABS = [
  { id: 'plan', label: '📋 Plan', icon: '📋' },
  { id: 'repo', label: '🔍 Repo Impact', icon: '🔍' },
  { id: 'tests', label: '🧪 Tests', icon: '🧪' },
  { id: 'security', label: '🔒 Security', icon: '🔒' },
  { id: 'release', label: '🚢 Release', icon: '🚢' },
] as const;

type TabId = typeof TABS[number]['id'];

interface ReportTabsProps {
  data: AnalyzeResponse;
}

export function ReportTabs({ data }: ReportTabsProps) {
  const [activeTab, setActiveTab] = useState<TabId>('plan');

  function downloadMarkdown() {
    const blob = new Blob([data.markdown_report], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'shipmate-production-report.md';
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={{
        background: 'rgba(17, 24, 39, 0.85)',
        border: '1px solid rgba(99, 179, 237, 0.1)',
        borderRadius: 20,
        overflow: 'hidden',
        backdropFilter: 'blur(12px)',
      }}
    >
      {/* Tab bar */}
      <div style={{
        display: 'flex', alignItems: 'center',
        padding: '16px 20px',
        borderBottom: '1px solid rgba(99, 179, 237, 0.08)',
        gap: 6,
        flexWrap: 'wrap',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '8px 16px',
                borderRadius: 8,
                border: activeTab === tab.id ? '1px solid rgba(59, 130, 246, 0.5)' : '1px solid transparent',
                background: activeTab === tab.id ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                color: activeTab === tab.id ? '#93c5fd' : '#4a6180',
                fontSize: 13,
                fontWeight: activeTab === tab.id ? 600 : 400,
                cursor: 'pointer',
                transition: 'all 0.2s',
                fontFamily: 'Inter, sans-serif',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Download button */}
        <button
          onClick={downloadMarkdown}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '8px 16px',
            borderRadius: 8,
            border: '1px solid rgba(16, 185, 129, 0.3)',
            background: 'rgba(16, 185, 129, 0.08)',
            color: '#34d399',
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            fontFamily: 'Inter, sans-serif',
            transition: 'all 0.2s',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLButtonElement).style.background = 'rgba(16, 185, 129, 0.15)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLButtonElement).style.background = 'rgba(16, 185, 129, 0.08)';
          }}
        >
          <Download size={14} />
          Export Report
        </button>
      </div>

      {/* Tab content */}
      <div style={{ padding: '24px' }}>
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.25 }}
        >
          {activeTab === 'plan' && <PlanTab data={data.agents.planner} />}
          {activeTab === 'repo' && <RepoTab data={data.agents.repo_analyst} />}
          {activeTab === 'tests' && <TestsTab data={data.agents.test_generator} />}
          {activeTab === 'security' && <SecurityTab data={data.agents.security_guard} />}
          {activeTab === 'release' && <ReleaseTab data={data.agents.delivery_manager} />}
        </motion.div>
      </div>
    </motion.div>
  );
}
