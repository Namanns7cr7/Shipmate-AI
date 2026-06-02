import { useState, useEffect, useRef } from 'react';
import './LandingPage.css';
import { motion, useInView } from 'framer-motion';

function GithubIcon({ size = 20, className = '' }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

function ShipIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 21c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1 .6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1" />
      <path d="M19.38 20A11.6 11.6 0 0 0 21 14l-9-4-9 4c0 2.9.94 5.34 2.81 7.76" />
      <path d="M19 13V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6" />
      <path d="M12 10v4" />
      <path d="M8 10v4" />
      <path d="M16 10v4" />
    </svg>
  );
}

function AnimatedCounter({ target, duration = 2000 }: { target: number; duration?: number }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });

  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const step = target / (duration / 16);
    const timer = setInterval(() => {
      start += step;
      if (start >= target) { setCount(target); clearInterval(timer); }
      else setCount(Math.floor(start));
    }, 16);
    return () => clearInterval(timer);
  }, [inView, target, duration]);

  return <span ref={ref}>{count}</span>;
}

const NAV_ITEMS = [
  { label: 'Dashboard', icon: '⊞', active: true },
  { label: 'Repositories', icon: '⌥', active: false },
  { label: 'Analyses', icon: '◈', active: false },
  { label: 'Reports', icon: '≡', active: false },
  { label: 'Insights', icon: '◇', active: false },
  { label: 'Settings', icon: '⚙', active: false },
];

const AGENTS = [
  { name: 'RepoLens', role: 'Repository Intelligence', color: '#10b981', glow: 'rgba(16,185,129,0.4)', top: '10%', left: '5%', dot: '#10b981' },
  { name: 'GuardRail', role: 'Security Review', color: '#3b82f6', glow: 'rgba(59,130,246,0.4)', top: '10%', right: '5%', dot: '#3b82f6' },
  { name: 'TestPilot', role: 'QA & Testing', color: '#8b5cf6', glow: 'rgba(139,92,246,0.4)', bottom: '10%', left: '5%', dot: '#8b5cf6' },
  { name: 'PlanForge', role: 'Delivery Planning', color: '#f59e0b', glow: 'rgba(245,158,11,0.4)', bottom: '10%', right: '5%', dot: '#f59e0b' },
];

const METRICS = [
  { icon: '⊛', label: 'Repositories Analyzed', value: 1247, suffix: '', color: '#3b82f6', bg: 'rgba(59,130,246,0.08)' },
  { icon: '◎', label: 'Average Readiness Score', value: 84, suffix: '/100', color: '#10b981', bg: 'rgba(16,185,129,0.08)' },
  { icon: '⚠', label: 'Critical Risks Found', value: 3891, suffix: '', color: '#ef4444', bg: 'rgba(239,68,68,0.08)' },
  { icon: '✦', label: 'Projects Ready To Ship', value: 892, suffix: '', color: '#f59e0b', bg: 'rgba(245,158,11,0.08)' },
];

const FEATURES = [
  { name: 'RepoLens', subtitle: 'Deep Repository Intelligence', desc: 'Understand architecture, stack, dependencies, and risk areas across your entire codebase.', color: '#10b981', icon: '⬡', tag: 'Architecture' },
  { name: 'PlanForge', subtitle: 'Delivery Planning', desc: 'Generate milestones, identify blockers, and get next actions for confident releases.', color: '#f59e0b', icon: '◈', tag: 'Planning' },
  { name: 'GuardRail', subtitle: 'Security Analysis', desc: 'Detect vulnerabilities, exposed secrets, OAuth issues, and dependency risks before they reach production.', color: '#3b82f6', icon: '⬟', tag: 'Security' },
  { name: 'TestPilot', subtitle: 'QA Readiness', desc: 'Find missing tests, coverage gaps, and improve release confidence with AI-generated test plans.', color: '#8b5cf6', icon: '◎', tag: 'Quality' },
];

const HOW_STEPS = [
  { num: 1, label: 'Connect GitHub', desc: 'OAuth in one click' },
  { num: 2, label: 'Analyze Repository', desc: 'Select repo & branch' },
  { num: 3, label: 'Run AI Agents', desc: '4 agents in parallel' },
  { num: 4, label: 'Readiness Score', desc: 'Instant insights' },
  { num: 5, label: 'Ship Confidently', desc: 'Go with certainty' },
];

const FINDINGS = [
  { icon: '⚠', text: 'Missing integration tests in /api routes', sev: 'medium', sevColor: '#f59e0b' },
  { icon: '↑', text: 'Outdated dependency: lodash@4.17.15', sev: 'low', sevColor: '#10b981' },
  { icon: '⚙', text: 'OAuth token stored without rotation policy', sev: 'high', sevColor: '#ef4444' },
];

interface LandingPageProps {
  onLogin: () => void;
  loginLoading?: boolean;
  loginError?: string | null;
}

export function LandingPage({ onLogin, loginLoading, loginError }: LandingPageProps) {
  const [repoUrl, setRepoUrl] = useState('');
  const [scoreVisible, setScoreVisible] = useState(false);
  const scoreRef = useRef<HTMLDivElement>(null);
  const scoreInView = useInView(scoreRef, { once: true });

  useEffect(() => { if (scoreInView) setTimeout(() => setScoreVisible(true), 300); }, [scoreInView]);

  return (
    <div className="lp-root">
      {/* ── Sidebar ── */}
      <aside className="lp-sidebar">
        <div className="lp-logo">
          <div className="lp-logo-icon">
            <ShipIcon />
          </div>
          <div>
            <div className="lp-logo-name">ShipMate<span className="lp-accent">AI</span></div>
            <div className="lp-logo-sub">Release Readiness Platform</div>
          </div>
        </div>

        <div className="lp-divider" />

        <nav className="lp-nav">
          {NAV_ITEMS.map(item => (
            <div key={item.label} className={`lp-nav-item${item.active ? ' active' : ''}`}>
              <span className="lp-nav-icon">{item.icon}</span>
              {item.label}
            </div>
          ))}
        </nav>

        <div className="lp-sidebar-bottom">
          <div className="lp-user-card">
            <div className="lp-user-avatar">N</div>
            <div>
              <div className="lp-user-name">Naman Sharma</div>
              <div className="lp-user-role">Developer</div>
            </div>
          </div>
          <div className="lp-status-pill">
            <span className="lp-status-dot" />
            All Systems Operational
          </div>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="lp-main">
        {/* Grid background */}
        <div className="lp-grid-bg" />
        {/* Glow orbs */}
        <div className="lp-orb lp-orb-1" />
        <div className="lp-orb lp-orb-2" />

        {/* Header */}
        <header className="lp-header">
          <div className="lp-header-badge">
            <span className="lp-badge-dot">✦</span>
            AI-POWERED ANALYSIS
          </div>
          <button className="lp-github-btn" onClick={onLogin} disabled={!!loginLoading}>
            <GithubIcon size={16} />
            {loginLoading ? 'Connecting...' : 'Login with GitHub'}
          </button>
        </header>

        {/* Hero */}
        <section className="lp-hero">
          <div className="lp-hero-content">
            <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
              <div className="lp-eyebrow">Release Readiness Platform</div>
              <h1 className="lp-headline">
                Ship Smarter.<br />
                <span className="lp-gradient-text">Ship Safer.</span>
              </h1>
              <p className="lp-subheading">
                AI agents analyze your repository across architecture, security, delivery planning,
                and testing readiness before every release.
              </p>
              {loginError && <div className="lp-error-pill">{loginError}</div>}
              <div className="lp-input-row">
                <div className="lp-input-wrap">
                  <GithubIcon size={18} className="lp-input-icon" />
                  <input
                    className="lp-input"
                    placeholder="https://github.com/owner/repository"
                    value={repoUrl}
                    onChange={e => setRepoUrl(e.target.value)}
                  />
                </div>
                <button className="lp-analyze-btn" onClick={onLogin}>
                  <span>Analyze Repository</span>
                  <span className="lp-btn-arrow">→</span>
                </button>
              </div>
              <div className="lp-input-hint">Example: https://github.com/facebook/react</div>
            </motion.div>
          </div>

          {/* Agent Swarm Visualization */}
          <motion.div
            className="lp-swarm"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            {/* SVG lines */}
            <svg className="lp-swarm-svg" viewBox="0 0 400 320">
              <defs>
                <linearGradient id="lg1" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#10b981" stopOpacity="0.6"/>
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.1"/>
                </linearGradient>
                <linearGradient id="lg2" x1="100%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.6"/>
                  <stop offset="100%" stopColor="#10b981" stopOpacity="0.1"/>
                </linearGradient>
                <linearGradient id="lg3" x1="0%" y1="100%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.6"/>
                  <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.1"/>
                </linearGradient>
                <linearGradient id="lg4" x1="100%" y1="100%" x2="0%" y2="0%">
                  <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.6"/>
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.1"/>
                </linearGradient>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="blur"/>
                  <feComposite in="SourceGraphic" in2="blur" operator="over"/>
                </filter>
              </defs>
              {/* Lines from agents to center ship */}
              <line x1="80" y1="60" x2="200" y2="160" stroke="url(#lg1)" strokeWidth="1.5" strokeDasharray="4 4" filter="url(#glow)">
                <animate attributeName="stroke-dashoffset" values="0;-16" dur="1.5s" repeatCount="indefinite"/>
              </line>
              <line x1="320" y1="60" x2="200" y2="160" stroke="url(#lg2)" strokeWidth="1.5" strokeDasharray="4 4" filter="url(#glow)">
                <animate attributeName="stroke-dashoffset" values="0;-16" dur="2s" repeatCount="indefinite"/>
              </line>
              <line x1="80" y1="260" x2="200" y2="160" stroke="url(#lg3)" strokeWidth="1.5" strokeDasharray="4 4" filter="url(#glow)">
                <animate attributeName="stroke-dashoffset" values="0;-16" dur="1.8s" repeatCount="indefinite"/>
              </line>
              <line x1="320" y1="260" x2="200" y2="160" stroke="url(#lg4)" strokeWidth="1.5" strokeDasharray="4 4" filter="url(#glow)">
                <animate attributeName="stroke-dashoffset" values="0;-16" dur="2.2s" repeatCount="indefinite"/>
              </line>
            </svg>

            {/* Central ship */}
            <div className="lp-ship-center">
              <div className="lp-ship-ring lp-ship-ring-outer" />
              <div className="lp-ship-ring lp-ship-ring-inner" />
              <div className="lp-ship-core">
                <div className="lp-ship-icon-wrap">
                  <ShipIcon />
                </div>
                <div className="lp-ship-label">ShipMate AI</div>
              </div>
            </div>

            {/* Agent cards */}
            {AGENTS.map((agent) => (
              <div
                key={agent.name}
                className="lp-agent-card"
                style={{
                  top: agent.top,
                  left: agent.left,
                  right: (agent as any).right,
                  bottom: agent.bottom,
                  borderColor: `${agent.color}33`,
                  boxShadow: `0 0 20px ${agent.glow}`,
                }}
              >
                <div className="lp-agent-header">
                  <span className="lp-agent-dot" style={{ background: agent.dot, boxShadow: `0 0 8px ${agent.dot}` }} />
                  <span className="lp-agent-name" style={{ color: agent.color }}>{agent.name}</span>
                </div>
                <div className="lp-agent-role">{agent.role}</div>
                <div className="lp-agent-status">● Active</div>
              </div>
            ))}
          </motion.div>
        </section>

        {/* Metrics */}
        <section className="lp-section lp-metrics">
          {METRICS.map((m, i) => (
            <motion.div
              key={m.label}
              className="lp-metric-card"
              style={{ background: m.bg, borderColor: `${m.color}22` }}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              whileHover={{ scale: 1.03, boxShadow: `0 0 30px ${m.color}33` }}
            >
              <div className="lp-metric-icon" style={{ color: m.color }}>{m.icon}</div>
              <div className="lp-metric-value" style={{ color: m.color }}>
                <AnimatedCounter target={m.value} />{m.suffix}
              </div>
              <div className="lp-metric-label">{m.label}</div>
              <div className="lp-metric-period">This Week</div>
            </motion.div>
          ))}
        </section>

        {/* Features */}
        <section className="lp-section">
          <div className="lp-section-header">
            <div className="lp-section-badge">Core Capabilities</div>
            <h2 className="lp-section-title">Four Agents. One <span className="lp-gradient-text">Readiness Score.</span></h2>
            <p className="lp-section-sub">Each agent specializes in a critical dimension of release readiness.</p>
          </div>
          <div className="lp-features-grid">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.name}
                className="lp-feature-card"
                style={{ borderColor: `${f.color}22` }}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                whileHover={{ borderColor: `${f.color}66`, boxShadow: `0 0 40px ${f.color}22`, y: -4 }}
              >
                <div className="lp-feature-icon-wrap" style={{ background: `${f.color}15`, color: f.color }}>
                  <span style={{ fontSize: 22 }}>{f.icon}</span>
                </div>
                <div className="lp-feature-tag" style={{ color: f.color, background: `${f.color}15` }}>{f.tag}</div>
                <h3 className="lp-feature-name" style={{ color: f.color }}>{f.name}</h3>
                <div className="lp-feature-subtitle">{f.subtitle}</div>
                <p className="lp-feature-desc">{f.desc}</p>
                <div className="lp-feature-link" style={{ color: f.color }}>Learn more →</div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* How It Works */}
        <section className="lp-section lp-how">
          <div className="lp-section-header">
            <div className="lp-section-badge">How It Works</div>
            <h2 className="lp-section-title">From Code to <span className="lp-gradient-text">Confidence</span></h2>
          </div>
          <div className="lp-steps-row">
            {HOW_STEPS.map((step, i) => (
              <div key={step.num} className="lp-step-item">
                <motion.div
                  className="lp-step-circle"
                  initial={{ scale: 0 }}
                  whileInView={{ scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.15, type: 'spring' }}
                >
                  {step.num}
                  <div className="lp-step-pulse" />
                </motion.div>
                {i < HOW_STEPS.length - 1 && (
                  <div className="lp-step-line">
                    <div className="lp-step-line-fill" style={{ animationDelay: `${i * 0.3}s` }} />
                  </div>
                )}
                <div className="lp-step-label">{step.label}</div>
                <div className="lp-step-desc">{step.desc}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Readiness Preview */}
        <section className="lp-section">
          <div className="lp-section-header">
            <div className="lp-section-badge">Dashboard Preview</div>
            <h2 className="lp-section-title">See Your <span className="lp-gradient-text">Readiness Score</span></h2>
          </div>
          <motion.div
            ref={scoreRef}
            className="lp-preview-card"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <div className="lp-preview-left">
              <div className="lp-score-ring-wrap">
                <svg className="lp-score-svg" viewBox="0 0 140 140">
                  <circle cx="70" cy="70" r="58" fill="none" stroke="rgba(59,130,246,0.1)" strokeWidth="10"/>
                  <circle
                    cx="70" cy="70" r="58"
                    fill="none"
                    stroke="url(#scoreGrad)"
                    strokeWidth="10"
                    strokeLinecap="round"
                    strokeDasharray={`${scoreVisible ? 87 * 3.64 : 0} 364`}
                    strokeDashoffset="91"
                    style={{ transition: 'stroke-dasharray 1.5s ease', filter: 'drop-shadow(0 0 12px rgba(59,130,246,0.6))' }}
                    transform="rotate(-90 70 70)"
                  />
                  <defs>
                    <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#3b82f6"/>
                      <stop offset="100%" stopColor="#8b5cf6"/>
                    </linearGradient>
                  </defs>
                </svg>
                <div className="lp-score-inner">
                  <div className="lp-score-num">87</div>
                  <div className="lp-score-label">/ 100</div>
                </div>
              </div>
              <div className="lp-score-status">Mostly Ready To Ship</div>
              <div className="lp-score-repo">facebook/react · main</div>
            </div>
            <div className="lp-preview-right">
              <div className="lp-findings-title">Top Findings</div>
              {FINDINGS.map((f, i) => (
                <motion.div
                  key={i}
                  className="lp-finding-item"
                  initial={{ opacity: 0, x: 20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.2 + i * 0.1 }}
                >
                  <span className="lp-finding-icon" style={{ color: f.sevColor }}>{f.icon}</span>
                  <span className="lp-finding-text">{f.text}</span>
                  <span className="lp-finding-sev" style={{ color: f.sevColor, background: `${f.sevColor}15` }}>{f.sev}</span>
                </motion.div>
              ))}
              <div className="lp-recommendation">
                <div className="lp-rec-label">AI Recommendation</div>
                <div className="lp-rec-text">"Ship after addressing 2 medium-risk issues. Security fix is strongly advised."</div>
              </div>
              <button className="lp-analyze-btn lp-analyze-sm" onClick={onLogin}>
                <GithubIcon size={16} />
                Analyze Your Repository
              </button>
            </div>
          </motion.div>
        </section>

        {/* Footer */}
        <footer className="lp-footer">
          <div className="lp-footer-brand">
            <ShipIcon />
            <span>ShipMate AI</span>
          </div>
          <div className="lp-footer-links">
            <a href="https://github.com" target="_blank" rel="noreferrer">GitHub</a>
            <a href="#">Documentation</a>
            <a href="#">Privacy</a>
            <a href="#">Contact</a>
          </div>
          <div className="lp-footer-powered">Powered by AI Agents ✦</div>
        </footer>
      </main>
    </div>
  );
}
