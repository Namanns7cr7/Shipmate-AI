import { Navbar }      from './Navbar';
import { Hero }        from './Hero';
import { ValueBadges } from './ValueBadges';
import { AgentCards }  from './AgentCards';
import { WhySection }  from './WhySection';
import { CTASection }  from './CTASection';

interface LandingPageProps {
  onLogin: () => void;
  loading?: boolean;
  error?: string | null;
}

export function LandingPage({ onLogin, loading, error }: LandingPageProps) {
  return (
    <div style={{ background: 'var(--bg)', color: 'var(--ink)', overflowX: 'hidden', minHeight: '100vh' }}>
      <Navbar   onLogin={onLogin} loading={loading} />
      <Hero     onLogin={onLogin} loading={loading} error={error} />
      <ValueBadges />
      <AgentCards />
      <WhySection />
      <CTASection onLogin={onLogin} loading={loading} />
    </div>
  );
}
