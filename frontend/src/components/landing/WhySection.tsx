import { Radar, ShieldCheck, Rocket } from 'lucide-react';
import { Reveal } from '../ui/Reveal';
import type { LucideIcon } from 'lucide-react';

interface WhyCard { Icon: LucideIcon; tone: string; hex: string; title: string; body: string; }

const CARDS: WhyCard[] = [
  {
    Icon: Radar, tone: 'emerald', hex: '#10b981',
    title: 'Understand repo health instantly',
    body: 'Connect a repo and get its stack, architecture, dependency risk and coverage mapped in under two minutes — no setup, no config.',
  },
  {
    Icon: ShieldCheck, tone: 'amber', hex: '#f59e0b',
    title: 'Catch risky changes before merge',
    body: 'GuardRail flags exposed secrets, injection paths and CVEs at PR time, so the dangerous diff never reaches production.',
  },
  {
    Icon: Rocket, tone: 'blue', hex: '#3b82f6',
    title: 'Ship with confidence',
    body: 'One readiness score with a clear Ready / Needs Fixes / Blocked verdict — and the exact next action to move the needle.',
  },
];

export function WhySection() {
  return (
    <section style={{ position: 'relative', padding: '40px 0 80px' }}>
      <div style={{ maxWidth: 1160, margin: '0 auto', padding: '0 28px' }}>
        <Reveal>
          <div style={{ textAlign: 'center', marginBottom: 44 }}>
            <span className="eyebrow" style={{ display: 'block', marginBottom: 12 }}>Why teams use ShipMate AI</span>
            <h2 style={{ fontSize: 38, fontWeight: 820, letterSpacing: '-0.03em', margin: '0 auto', maxWidth: 600 }}>
              From repo to deploy decision, without the guesswork
            </h2>
          </div>
        </Reveal>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
          {CARDS.map((c, i) => (
            <Reveal key={c.title} delay={i * 90}>
              <div className="card card-hover" style={{ padding: 28, height: '100%' }}>
                <div style={{
                  width: 52, height: 52, borderRadius: 15, display: 'grid', placeItems: 'center',
                  background: `${c.hex}18`, border: '1px solid var(--line-2)',
                  color: c.hex, marginBottom: 20, boxShadow: `0 0 30px ${c.hex}22`,
                }}>
                  <c.Icon size={26} />
                </div>
                <h3 style={{ fontSize: 20, fontWeight: 760, margin: '0 0 10px', letterSpacing: '-0.02em' }}>{c.title}</h3>
                <p className="muted" style={{ fontSize: 14, lineHeight: 1.65, margin: 0 }}>{c.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
