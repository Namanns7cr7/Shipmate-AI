# Product

## Register

product

> Dual-surface project. `product` is the default (the app shell: Dashboard, Analysis, Reports, Repositories). The marketing **landing page** (`components/landing/`) is treated as `brand` and should be overridden to `brand` per-task when working on it. Both surfaces are maintained at equal priority.

## Users

Software engineers who connect a GitHub repository and want a fast, trustworthy **go / no-go deployment-readiness call before they ship to production**. They arrive with a repo, branch, or open PR and a question: "Is this safe to deploy?" Their context is pre-release — often under time pressure, mid-workflow, switching between code and this tool. They want the verdict and the few things blocking it, not a wall of metrics to interpret themselves.

## Product Purpose

ShipMate AI runs a four-agent pipeline (RepoLens → PlanForge / GuardRail / TestPilot → Ship Report) over a repository and produces a deployment-readiness score with an actionable verdict (Ready / Needs Fixes / Blocked), plus per-agent findings on code health, planning, security/risk, and test coverage. Success is a developer trusting the verdict enough to act on it — shipping with confidence or fixing the named blockers first — without re-doing the analysis by hand.

## Brand Personality

**Precise, confident, technical.** The voice of mission control / an instrument panel: an expert co-pilot that has already done the work and reports the truth plainly. Trustworthy and exact, never hand-wavy or hypey. The radar / compass motif (ShipMate, navigation, sweeping for risk) is the throughline. Emotional goal: the calm confidence of a pilot reading a clean instrument panel before takeoff.

## Anti-references

- **Generic SaaS template.** No hero-metric template (big gradient number + small label + supporting stats), no identical icon-heading-text card grids repeated down the page, no tiny uppercase tracked eyebrow above every section, no numbered `01 / 02 / 03` section scaffolding. This must not read as a Stripe/Linear/Vercel clone assembled from defaults.
- Avoid anything that screams "AI made this from a category prompt" — the verdict, the radar identity, and the real per-agent data are the differentiators; lean on them, not on stock SaaS scaffolding.

## Design Principles

1. **Verdict first, evidence on demand.** The single most important output is the readiness call. Lead with it; let supporting detail recede until asked for. Never make the user assemble the conclusion from scattered numbers.
2. **Instrument-panel honesty.** Show real state — scores, risk, blockers — without softening or inflating. Color and weight encode severity truthfully (emerald = ready, red = blocked), the same language everywhere.
3. **One coherent radar identity.** The compass / radar / sweep motif and the agent color system (RepoLens emerald, PlanForge purple, GuardRail amber, TestPilot cyan, Ship Report blue) are a system, not decoration. Reuse them consistently; don't invent one-off visual languages per screen.
4. **Earned motion.** Motion communicates pipeline progress and state change (sweep, score count-up, agent status). It is part of the build, never ornament for its own sake — and never gates content visibility.
5. **Density without clutter.** This is a dev tool with a lot to say, but hierarchy does the work: the opposite of a cluttered Jenkins/Jira dashboard. Every screen has a clear primary focus.

## Accessibility & Inclusion

- Target **WCAG 2.1 AA**: body text ≥ 4.5:1 contrast, large text ≥ 3:1 — verified against the dark `--bg #070c18` background. Watch muted text tokens (`--ink-3`, `--ink-4`) on tinted panels.
- Never encode meaning by color alone — verdicts and severities also carry text labels and icons (color-blind safe; emerald/amber/red is not distinguishable for all users).
- Honor `prefers-reduced-motion: reduce` for every animation (framer-motion is used heavily): provide a crossfade or instant alternative for the radar sweep, score count-up, and agent transitions.
- Maintain visible focus states and keyboard navigation across the app shell (sidebar nav, repo switcher, tabs).
