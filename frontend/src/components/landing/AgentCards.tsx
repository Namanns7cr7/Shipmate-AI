import { Rocket } from 'lucide-react';
import { AGENTS } from '../../lib/agents';
import { Reveal } from '../ui/Reveal';

const ALL_CARDS = [
  ...AGENTS,
  { key: 'ship', name: 'Ship Report', tone: 'blue', hex: '#60a5fa', Icon: Rocket, tag: 'Deployment Readiness', sub: 'Synthesizes every agent into one go/no-go readiness score.' },
];

export function AgentCards() {
  return (
    <section style={{ maxWidth: 1160, margin: '0 auto', padding: '70px 28px' }}>
      <Reveal>
        <div style={{ textAlign: 'center', marginBottom: 44 }}>
          <span className="eyebrow" style={{ display: 'block', marginBottom: 12 }}>Four specialists · one readiness verdict</span>
          <h2 style={{ fontSize: 38, fontWeight: 820, letterSpacing: '-0.03em', margin: 0 }}>
            A crew of agents for your codebase
          </h2>
          <p className="muted" style={{ fontSize: 16, maxWidth: 560, margin: '12px auto 0' }}>
            Four agents each own one slice of readiness; the Ship Report folds them into a single
            score — then the Coder agent turns the findings into pull requests.
          </p>
        </div>
      </Reveal>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 16 }}>
        {ALL_CARDS.map((a, i) => (
          <Reveal key={a.key} delay={i * 70}>
            <div className="card card-hover" style={{ padding: 22, height: '100%' }}>
              <div style={{
                width: 46, height: 46, borderRadius: 13, display: 'grid', placeItems: 'center',
                background: `${a.hex}18`, border: `1px solid ${a.hex}44`, color: a.hex, marginBottom: 16,
              }}>
                <a.Icon size={23} />
              </div>
              <h3 style={{ fontSize: 17, fontWeight: 750, margin: '0 0 6px' }}>{a.name}</h3>
              <div className={`chip tone-${a.tone}`} style={{ marginBottom: 12 }}>{a.tag}</div>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.6, margin: 0 }}>{a.sub}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
