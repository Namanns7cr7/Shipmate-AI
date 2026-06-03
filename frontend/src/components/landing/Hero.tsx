import { Check, Play } from 'lucide-react';
import { RadarBg } from '../ui/RadarBg';
import { GitHubConnectButton } from '../ui/GitHubConnectButton';
import { WorkflowPipeline } from '../ui/WorkflowPipeline';
import { LiveAgentPreview } from './LiveAgentPreview';
import { Compass } from 'lucide-react';
import { motion } from 'framer-motion';

interface HeroProps { onLogin: () => void; loading?: boolean; error?: string | null; }

export function Hero({ onLogin, loading, error }: HeroProps) {
  return (
    <section style={{ position: 'relative', paddingTop: 132, paddingBottom: 70, overflow: 'hidden' }}>
      <RadarBg sweep rings blobs />
      {/* bottom fade */}
      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, transparent 60%, var(--bg))' }} aria-hidden="true" />

      <div style={{ position: 'relative', maxWidth: 1200, margin: '0 auto', padding: '0 28px', display: 'grid', gridTemplateColumns: 'clamp(0px,55%,680px) 1fr', gap: 56, alignItems: 'center' }}>
        {/* Left column */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: [0.2, 0.7, 0.2, 1] }}
        >
          <span className="pill" style={{ marginBottom: 22, display: 'inline-flex' }}>
            <span className="dot dot-pulse" style={{ background: '#34d399' }} />
            Agentic Engineering Command Center
          </span>

          <h1 style={{ fontSize: 'clamp(36px, 4.5vw, 56px)', lineHeight: 1.04, fontWeight: 850, letterSpacing: '-0.035em', margin: '0 0 20px' }}>
            Ship{' '}
            <span className="gradient-ink">production-ready</span>
            {' '}code with AI agents
          </h1>

          <p style={{ fontSize: 17, lineHeight: 1.6, color: 'var(--ink-2)', maxWidth: 520, margin: '0 0 16px' }}>
            Connect GitHub and ShipMate's agents analyze your repo, detect PR &amp; security risks,
            generate the tests you're missing, and return a single deployment-readiness score.
          </p>

          {/* Step strip */}
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6, marginBottom: 30 }}>
            {['Connect GitHub', 'Analyze repo', 'Detect risks', 'Generate tests', 'Ship readiness'].map((s, i) => (
              <span key={s} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="mono" style={{ fontSize: 12, color: i === 4 ? 'var(--blue-2)' : 'var(--ink-3)', fontWeight: 600 }}>{s}</span>
                {i < 4 && <span style={{ color: 'var(--ink-4)', fontSize: 12 }}>→</span>}
              </span>
            ))}
          </div>

          {/* CTAs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <GitHubConnectButton onClick={onLogin} label="Connect GitHub" variant="light" size="lg" loading={loading} />
            <button className="btn btn-secondary btn-lg" onClick={onLogin}>
              <Play size={15} /> View Demo
            </button>
          </div>

          {error && <p style={{ marginTop: 12, fontSize: 13, color: 'var(--red)' }}>{error}</p>}

          {/* Trust row */}
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 20, marginTop: 26 }}>
            {['No code changes', 'Read-only access', 'Results in ~90s'].map(t => (
              <span key={t} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, color: 'var(--ink-3)' }}>
                <Check size={14} style={{ color: '#34d399' }} /> {t}
              </span>
            ))}
          </div>
        </motion.div>

        {/* Right column — live preview card */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.15, ease: [0.2, 0.7, 0.2, 1] }}
        >
          <LiveAgentPreview />
        </motion.div>
      </div>

      {/* Workflow band */}
      <div style={{ position: 'relative', maxWidth: 1100, margin: '58px auto 0', padding: '0 28px' }}>
        <div className="card" style={{ padding: '22px 20px' }}>
          <div className="eyebrow" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 16 }}>
            <Compass size={13} /> The ShipMate Pipeline
          </div>
          <WorkflowPipeline autoplay />
        </div>
      </div>
    </section>
  );
}
