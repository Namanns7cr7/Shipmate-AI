import { GitPullRequest, ShieldCheck, FlaskConical, Cpu, Gauge } from 'lucide-react';
import { Reveal } from '../ui/Reveal';

const ITEMS = [
  { Icon: GitPullRequest, label: 'Auto-Fix Pull Requests', tone: 'blue'    },
  { Icon: ShieldCheck,    label: 'Security Guardrails',    tone: 'amber'   },
  { Icon: FlaskConical,   label: 'Test Coverage Gaps',     tone: 'cyan'    },
  { Icon: Cpu,            label: 'Self-Healing CI',        tone: 'purple'  },
  { Icon: Gauge,          label: 'Deployment Score',       tone: 'emerald' },
];

export function ValueBadges() {
  return (
    <section id="product" style={{ maxWidth: 1100, margin: '0 auto', padding: '8px 28px 20px', scrollMarginTop: 84 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', gap: 10 }}>
        {ITEMS.map((it, i) => (
          <Reveal key={it.label} delay={i * 60}>
            <div className={`chip tone-${it.tone}`} style={{ padding: '9px 15px', fontSize: 13 }}>
              <it.Icon size={15} /> {it.label}
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
