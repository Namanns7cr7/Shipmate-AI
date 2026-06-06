// ────────────────────────────────────────────────────────────────────────────
// Agent definitions, pipeline order, score helpers, and language-color map.
//
// This module is referenced from ~10 components (DashboardPage, AnalysisPage,
// ScoreRing, RepoCard, AppSidebar, etc.) but was not committed in the rewrite.
// Re-introduced here matching the keys / fields each consumer expects.
// ────────────────────────────────────────────────────────────────────────────

import type { LucideIcon } from 'lucide-react';
import {
  Search,        // RepoLens — repo structure / tech stack
  ListChecks,    // PlanForge — milestones / blockers
  ShieldCheck,   // GuardRail — security
  FlaskConical,  // TestPilot — tests
  Rocket,        // Ship Report (composite)
} from 'lucide-react';

export interface AgentDef {
  /** Stable identifier used as React key + lookup. */
  key: string;
  /** Display name on cards / topbar. */
  name: string;
  /** Color tone class suffix (`chip tone-${tone}`). */
  tone: 'blue' | 'violet' | 'red' | 'emerald' | 'amber';
  /** Hex color for accents (used in inline styles + score rings). */
  hex: string;
  /** Lucide icon component (rendered as `<a.Icon size={…} />`). */
  Icon: LucideIcon;
  /** Short category chip text. */
  tag: string;
  /** One-line subtitle for marketing/landing cards. */
  sub: string;
}

// ── 4 swarm agents (matches ID_TO_INDEX in AnalysisPage.tsx) ────────────────
//   index 0 → repolens   (AgentProgress.id = 'repo_lens')
//   index 1 → planforge  (AgentProgress.id = 'plan_forge')
//   index 2 → guardrail  (AgentProgress.id = 'guardrail')
//   index 3 → testpilot  (AgentProgress.id = 'testpilot')
export const AGENTS: AgentDef[] = [
  {
    key: 'repolens',
    name: 'RepoLens',
    tone: 'blue',
    hex: '#60a5fa',
    Icon: Search,
    tag: 'Repository Mapping',
    sub: 'Maps your codebase: tech stack, modules, entry points, and architecture risks.',
  },
  {
    key: 'planforge',
    name: 'PlanForge',
    tone: 'violet',
    hex: '#a78bfa',
    Icon: ListChecks,
    tag: 'Delivery Planning',
    sub: 'Forges delivery milestones, surfaces blockers, and recommends next actions.',
  },
  {
    key: 'guardrail',
    name: 'GuardRail',
    tone: 'red',
    hex: '#f87171',
    Icon: ShieldCheck,
    tag: 'Security & Compliance',
    sub: 'Spots exposed secrets, CORS gaps, auth risks, and dependency CVEs before launch.',
  },
  {
    key: 'testpilot',
    name: 'TestPilot',
    tone: 'emerald',
    hex: '#34d399',
    Icon: FlaskConical,
    tag: 'Test Coverage',
    sub: 'Audits existing tests, finds coverage holes, and proposes the missing test plan.',
  },
];

// ── Pipeline visualization (used by WorkflowPipeline.tsx) ───────────────────
// Same 4 agents + a final "Ship" composite node for the readiness verdict.
export const PIPE: AgentDef[] = [
  ...AGENTS,
  {
    key: 'ship',
    name: 'Ship Report',
    tone: 'blue',
    hex: '#60a5fa',
    Icon: Rocket,
    tag: 'Deployment Readiness',
    sub: 'Synthesizes every agent into one go/no-go readiness score.',
  },
];

// ── Score → accent color helper ─────────────────────────────────────────────
// Used by ScoreRing, DashboardPage, etc. Matches the green/amber/red traffic
// light that consumers (RepoCard, VerdictPill) already use elsewhere.
export function scoreColor(score: number): string {
  if (score >= 80) return '#34d399'; // emerald — ready to ship
  if (score >= 60) return '#fbbf24'; // amber — needs review
  if (score >= 40) return '#fb923c'; // orange — risky
  return '#f87171';                  // red — not ready
}

// ── GitHub language color map (RepoCard, AppSidebar) ────────────────────────
// Subset of github-linguist's languages.yml — covers the common ones we'll
// see in user repos. Falls back to `#64748b` (slate-500) at the call site.
export const LANG_COLORS: Record<string, string> = {
  TypeScript: '#3178c6',
  JavaScript: '#f1e05a',
  Python:     '#3572A5',
  Go:         '#00ADD8',
  Rust:       '#dea584',
  Java:       '#b07219',
  Kotlin:     '#A97BFF',
  Swift:      '#F05138',
  Ruby:       '#701516',
  PHP:        '#4F5D95',
  'C++':      '#f34b7d',
  C:          '#555555',
  'C#':       '#178600',
  HTML:       '#e34c26',
  CSS:        '#563d7c',
  SCSS:       '#c6538c',
  Vue:        '#41b883',
  Svelte:     '#ff3e00',
  Shell:      '#89e051',
  Dockerfile: '#384d54',
  Solidity:   '#AA6746',
  Dart:       '#00B4AB',
  Lua:        '#000080',
  Zig:        '#ec915c',
};
