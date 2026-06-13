import { CheckCircle2, AlertTriangle, X } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface VerdictPillProps { verdict: string; small?: boolean; }

const MAP: Record<string, { tone: string; Icon: LucideIcon }> = {
  'Ready':       { tone: 'emerald', Icon: CheckCircle2 },
  'Needs Fixes': { tone: 'amber',   Icon: AlertTriangle },
  'Blocked':     { tone: 'red',     Icon: X },
};

export function VerdictPill({ verdict, small = false }: VerdictPillProps) {
  const { tone, Icon } = MAP[verdict] ?? MAP['Needs Fixes'];
  return (
    <span className={`chip tone-${tone}`} style={small ? {} : { fontSize: 12, padding: '5px 11px' }}>
      <Icon size={small ? 11 : 13} />
      {verdict}
    </span>
  );
}

// toVerdict now lives in lib/verdict.ts (pure, React-free). Re-exported here so
// existing `import { toVerdict } from '.../VerdictPill'` call sites keep working.
// eslint-disable-next-line react-refresh/only-export-components
export { toVerdict } from '../../lib/verdict';
