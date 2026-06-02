import { Navbar } from './Navbar';
import { Hero } from './Hero';
import { AgentCards } from './AgentCards';
import { WorkflowSection } from './WorkflowSection';
import { DashboardPreview } from './DashboardPreview';
import { SecuritySection } from './SecuritySection';
import { CTASection } from './CTASection';

interface LandingPageProps {
  onLogin: () => void;
  loading?: boolean;
  error?: string | null;
}

export function LandingPage({ onLogin, loading, error }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans overflow-x-hidden">
      <Navbar onLogin={onLogin} loading={loading} />
      <Hero onLogin={onLogin} loading={loading} error={error} />
      <AgentCards />
      <WorkflowSection />
      <DashboardPreview />
      <SecuritySection />
      <CTASection onLogin={onLogin} loading={loading} />
      <footer className="py-8 text-center text-xs text-slate-600 border-t border-slate-800/40">
        ShipMate AI · AI-native release readiness platform · Built for hackathon 2026
      </footer>
    </div>
  );
}
