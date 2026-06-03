# Handoff: ShipMate AI — UI Redesign (Agentic Engineering Command Center)

## Overview
A premium redesign of **ShipMate AI** — a GitHub-first agentic engineering command center. Users connect a GitHub repository, and five agents (RepoLens, PlanForge, GuardRail, TestPilot → Ship Report) analyze repo health, PR/security risk, test coverage and CI/CD readiness, returning a single **Deployment Readiness score** with a `Ready / Needs Fixes / Blocked` verdict.

This redesign covers the **landing page** and the full **authenticated app** (Dashboard, Repositories, Analysis, Reports), all wired into one GitHub-first journey: `Landing → Connect GitHub → Dashboard → Repositories → live Analysis → executive Report`.

The redesign goals: explain the product in 5 seconds, make **Connect GitHub** the primary action everywhere, add a recurring **radar/compass "navigation console"** identity, raise visual polish, and tighten hierarchy + spacing.

---

## About the Design Files
The files in this bundle are **design references created in HTML/React (Babel-transpiled JSX with inline styles)** — a working prototype showing intended look and behavior. **They are not production code to copy directly.**

Your task is to **recreate these designs in the existing ShipMate frontend**: **Vite + React + TypeScript + Tailwind CSS + Framer Motion + lucide-react**, using the patterns already documented in the repo's root `CLAUDE.md` (the `.glass-card`, `.gradient-border`, `.btn-primary`, `.grid-bg`, `.score-ring`, `.badge-*` classes, the agent accent hexes, the `src/components/` + `src/pages/` structure). Translate:

| Prototype | Target codebase |
|---|---|
| Inline `style={{}}` objects | Tailwind utility classes / existing global classes in `src/index.css` |
| Hand-drawn `<Icon name="…">` SVGs | `lucide-react` components |
| CSS `@keyframes` + `.anim-*` / `.reveal` classes | Framer Motion (`motion.div`, `initial/animate`, `whileInView`) |
| `.jsx` + `Object.assign(window,…)` globals | `.tsx` modules with `import/export` and typed props |
| Mock `REPORT` / `REPOS` constants | Real FastAPI responses from the backend |

---

## Fidelity
**High-fidelity (hifi).** Final colors, typography, spacing, layout, copy and interactions are all intentional. Recreate the UI faithfully using the codebase's existing libraries and the design tokens below. The one area you should treat as *additive* to the current system is the **radar/compass identity** (Design Tokens → "Radar / compass identity" section) — those primitives are new and documented precisely so they can be added to `src/index.css`.

---

## Design Tokens

### Colors — surfaces
| Token | Value | Use |
|---|---|---|
| Page bg | `#070c18` (fallback `#060b16`) | app + landing base |
| Card / panel bg | `rgba(13,21,40,0.72)` w/ `backdrop-filter: blur(14px)` | glass cards |
| Solid panel | `#0c1426` | opaque surfaces |
| Sidebar | `linear-gradient(180deg,#080f1f,#060b16)` | app sidebar |
| Border subtle | `rgba(255,255,255,0.07)` | default hairlines |
| Border hover | `rgba(255,255,255,0.12)` | hover / emphasis |

### Colors — text
| Token | Value |
|---|---|
| Ink (primary) | `#f3f6fc` |
| Ink-2 (secondary) | `#aeb9cf` |
| Ink-3 (muted) | `#6f7d97` |
| Ink-4 (faint) | `#495368` |

### Colors — accents (agent + semantic)
| Color | Hex | Use |
|---|---|---|
| Blue | `#3b82f6` (light `#60a5fa`) | primary actions, active nav, Ship Report |
| Cyan | `#22d3ee` | TestPilot, secondary accent, button gradients |
| Purple | `#8b5cf6` | PlanForge |
| Emerald | `#10b981` | RepoLens, success, "Ready" |
| Amber | `#f59e0b` | GuardRail, warning, medium severity |
| Orange | `#f97316` | high severity |
| Red | `#ef4444` | critical / "Blocked" |

**Agent → color map** (used for icon tint, card border, progress fill, pipeline node):
`RepoLens → emerald #10b981` · `PlanForge → purple #8b5cf6` · `GuardRail → amber #f59e0b` · `TestPilot → cyan #22d3ee` · `Ship Report → blue #60a5fa`.

### Score thresholds (rings, pills, verdict)
`≥80 → emerald #10b981` · `≥60 → blue #3b82f6` · `≥40 → amber #f59e0b` · else `red #ef4444`.
Verdict mapping: `Ready → emerald` · `Needs Fixes → amber` · `Blocked → red`.

### Typography
- **Inter** for UI (weights 400–850 used; headings 800–850). **JetBrains Mono** for repo names, branches, timestamps, log lines, commit hashes.
- Page H1: `25px / weight 840 / letter-spacing -0.025em`.
- Hero H1 (landing): `56px / 850 / -0.035em`, line-height 1.04.
- Section H2 (landing): `38px / 820 / -0.03em`.
- Eyebrow label: `11px / 700 / uppercase / letter-spacing 0.18em / color ink-3`.
- Body: `14px / 1.6 line-height / color ink-2`.

### Spacing / radius / shadow
- Page wrap: `padding: 28px 32px; max-width: 1180px; margin: 0 auto`.
- Card radius `18px`; small `12px`; pills `999px`; chips `8px`; buttons `12px` (lg `13px`, sm `10px`).
- Card gap in grids: `14–20px`. Section vertical rhythm on landing: `70px`.
- Glow shadow: `0 0 0 1px rgba(59,130,246,0.12), 0 24px 70px -30px rgba(37,99,235,0.45)`.
- Soft shadow: `0 24px 60px -24px rgba(0,0,0,0.7)`.

### Radar / compass identity (NEW — add to `src/index.css`)
These create the "navigation console" texture. Recurs on: hero, empty state, deployment-readiness card, analysis center, report header, final CTA.
- **`.grid-bg`** — layered: `radial-gradient(circle at center, rgba(59,130,246,0.05), transparent 70%)` + two `linear-gradient` 1px lines at `46px` spacing (`rgba(255,255,255,0.022)`).
- **Compass rings** — concentric circles, `border: 1px solid rgba(96,165,250,0.10)`, sizes ~260/460/680/920px, centered, absolute, `pointer-events:none`.
- **Radar sweep** — `conic-gradient(from 0deg, transparent 0deg, rgba(34,211,238,0.28) 36deg, transparent 60deg)` on a circle, `animation: sweep 4.5s linear infinite` (`@keyframes sweep { to { transform: rotate(360deg) } }`).
- **Aurora blobs** — large `border-radius:50%` divs, `filter: blur(90px)`, blue/purple/cyan radial gradients at ~0.4–0.5 opacity, behind content.
- **Status dot pulse** — 7px dot + `::after` ping ring (`@keyframes ping { 75%,100% { transform: scale(2.4); opacity:0 } }`).

### Animation guidance (Framer Motion equivalents)
- **Page enter:** `initial={{opacity:0, y:14}} animate={{opacity:1, y:0}} transition={{duration:0.55, ease:[.2,.7,.2,1]}}`.
- **Scroll reveal (landing cards):** `whileInView={{opacity:1, y:0}} initial={{opacity:0, y:22}} viewport={{once:true, margin:"-12%"}}`, stagger via `delay: index * 0.06`.
- **Score ring:** animate `strokeDashoffset` from full circumference to `c − (value/100)*c` over ~1.3s; count the number up in parallel.
- **Progress bars:** `width` 0 → `value%` over ~0.9s.
- ⚠️ **Lesson from the prototype:** prefer **transform-only** entrance animations (translate/scale) over opacity-fill animations. A CSS opacity entrance with `fill-mode: both` can occasionally strand content at `opacity:0`. Framer Motion's `animate` avoids this, but if you ever hand-roll CSS, don't rely on `both` fill for opacity. Respect `prefers-reduced-motion`.

---

## Screens / Views

> Files referenced below live in `prototype/` in this bundle. Each maps to a target path in the existing repo.

### 1. Landing Page → `src/components/landing/`
Prototype: `prototype/assets/landing.jsx`

- **Navbar** (`Navbar.tsx`) — fixed, height 68px, 3-column (logo · centered nav links · CTA). Transparent until `scrollY>20`, then `rgba(7,12,24,0.82)` + `blur(16px)` + bottom hairline. Logo = **custom geometric mark** (see Assets) + "ShipMate **AI**" (AI in `#60a5fa`). Nav links: Product, Agents, Why ShipMate, Pricing (ghost text buttons). Right: "Sign in" secondary button + **white** `Connect GitHub` button with GitHub glyph.
- **Hero** (`Hero.tsx`) — two-column grid `1.05fr / 0.95fr`, gap 56px, `padding-top:132px`. Background = `.grid-bg` + radar rings + sweep + aurora blobs, with a bottom fade to page bg.
  - *Left:* pill badge ("Agentic Engineering Command Center" + pulsing emerald dot) → **H1**: "Ship **production-ready** code with AI agents" (the middle phrase uses a blue→purple gradient text clip) → subhead explaining the flow → an inline mono **step strip**: `Connect GitHub → Analyze repo → Detect risks → Generate tests → Ship readiness` (arrows between) → CTAs: white `Connect GitHub` (lg) + secondary `View Demo` (play icon) → trust row: "No code changes · Read-only access · Results in ~90s" with emerald check icons.
  - *Right:* **Live product preview** card (`gradient-border` + glass). This is the centerpiece the client specifically requested: a window-chrome header (`github` icon + mono `northwind-labs/atlas-checkout` + green "connected" pill + mono `main · a9f3c21`), then a 2-column body — **left:** the 4 agents listed, each flipping `queued → working… (spinner) → complete (✓ + a stat)` one-by-one on a timer; **right:** a **readiness ScoreRing** that fills to **72** + a `Needs Fixes` verdict pill once agents finish; a findings strip at the bottom (`1 critical · 3 high · 6 medium · 61%→79% coverage`) that brightens when complete.
  - **Workflow band** under the hero: a horizontal **WorkflowPipeline** card — `GitHub Repo → RepoLens → PlanForge → GuardRail → TestPilot → Ship Report`, each a rounded icon node with connector bars, auto-playing a lit progression (each lit node glows in its agent color).
- **ValueBadges** (`ValueBadges.tsx`) — centered row of 5 chips with icons: PR Risk Detection (blue), Security Guardrails (amber), Test Generation (cyan), CI/CD Readiness (purple), Deployment Score (emerald). Reveal-stagger in.
- **AgentsSection** (`AgentCards.tsx`) — centered heading "A crew of agents for your codebase" + 5 cards (the 4 agents + Ship Report). Each card: icon in tinted rounded square (agent color), name, a tone-colored tag chip, one-line description. `card-hover` lift on hover.
- **WhySection** (`WhySection.tsx`) — "Why teams use ShipMate AI" + 3 large cards: **Understand repo health instantly** (emerald radar icon), **Catch risky changes before merge** (amber shield icon), **Ship with confidence** (blue rocket icon). Big icon tile w/ glow + title + paragraph.
- **FinalCTA** (`CTASection.tsx`) — single centered glass+gradient-border panel with radar texture: the logo mark, H2 "Connect GitHub. Get your readiness score.", subtext, a white `Connect GitHub` (lg) button + "SOC 2 · read-only scopes" note. Footer below: wordmark, copyright line ("Navigate every repo to production."), Docs/Security/GitHub links.

### 2. App Shell (authenticated)
Layout: `flex; min-height:100vh; background:#070c18`. Left = sticky `248px` sidebar; right = `flex-1; height:100vh; overflow-y:auto` with sticky topbar, content wrapped in a `.grid-bg`.
Prototype: `prototype/assets/appshell.jsx`

- **Sidebar** (`src/components/app/AppSidebar.tsx`):
  1. Brand: logo mark + "ShipMate **AI**".
  2. **Repo switcher** (NEW) — a button showing the current repo (gradient icon tile + mono repo name + owner + chevron) that opens a dropdown panel listing all connected repos (language dot + mono name + check on the active one). This is the small workspace/repo switcher the client asked for.
  3. **"Connected to GitHub"** status strip — emerald-tinted, GitHub glyph + label + pulsing dot.
  4. Nav: Dashboard, Repositories, Analysis, Reports. Each `icon + label`, radius 11px. **Active state:** blue gradient bg `linear-gradient(100deg, rgba(37,99,235,0.28), rgba(37,99,235,0.06))` + blue border + a glowing blue dot on the right. **Disabled** (Reports before any analysis): faint text, `cursor:not-allowed`, a small "locked" kbd tag.
  5. Bottom: "All Systems Operational" emerald pill + user row (gradient avatar `AR`, name `Alex Rivera`, `@alex-rivera` mono, logout icon button).
- **Topbar** (`App.tsx`) — sticky, height 60px, `rgba(7,12,24,0.82)` + blur + bottom hairline. Left: breadcrumb `ShipMate › PageName` + a divider + **context chips**: `repo name`, `branch`, `scanned <time>` (the selected repo / branch / last analysis time the client requested). Right: **`Run Analysis`** primary button (becomes a spinner + "Running…" while active), a bell icon button, and a connected-user pill (pulsing dot + `@username` + avatar).
- **Connect GitHub modal** (`ConnectGitHubModal.tsx`) — centered glass modal over a blurred scrim. Stage 1: GitHub glyph → arrow → ShipMate mark, "requesting **read-only** access" copy, a 3-item scope checklist, and a white **"Authorize & continue"** button. Stages 2–4 (simulated OAuth): spinner with "Authorizing with GitHub…" → "Fetching your repositories…" → checkmark "Connected!", then resolves into the app. In production, replace the simulated stages with the real GitHub OAuth round-trip.

### 3. Dashboard Page → `src/pages/DashboardPage.tsx`
Prototype: `prototype/assets/dashboard.jsx`

1. Header row: greeting "Good afternoon, Alex" (H1) + subtext + "View Reports" secondary button.
2. **Deployment Readiness hero card** (NEW, large — replaces the old small stat row as the first thing on the page). Glass + gradient-border + radar texture. Two columns split by a vertical hairline:
   - *Left:* "Deployment Readiness" eyebrow + a large **158px ScoreRing** showing **72** with the verdict word ("NEEDS FIXES") inside, + a mono `branch · commit` line.
   - *Right:* verdict heading row (colored verdict icon + "Needs Fixes" + `owner/repo`) + an **Open Ship Report** primary button; a red-tinted **Top Blocker** callout ("Top Blocker · GuardRail" + the blocker text); and a 4-up **score breakdown** (Repo Health 81 / Delivery 74 / Security 58 / Testing 66) each with an agent-colored mini progress bar.
3. **Agent summary row** — 4 `card-hover` cards (one per agent): icon tile, score `/100` (threshold-colored), agent name, a big stat (e.g. "4 vuln", "4 milestones", "6 findings", "61% cov") + sub-label. Reveal-stagger.
4. **Two-column** (`1.7fr / 1fr`):
   - *Recent Analyses table* — looks like a GitHub repo/PR analysis table. Columns: Repository (lock/repo icon + mono name), Score (bold threshold-colored), Verdict (pill), Risks (e.g. `1C` red + `3H` orange chips, or "clean"), Coverage (mono %), Last scan (mono relative time), and a re-analyze icon button. Rows hover-highlight and are clickable → open that repo's report. "View all" ghost button in the header.
   - *AI Insights panel* — a card with the **highest-risk issue** (red-tinted: "Highest risk" chip + file path + title + description) and a blue-tinted **Next action** block (target icon + recommendation + a "View full analysis" primary button). Below it: a **Readiness trend** mini bar chart (7 bars, last bar a blue gradient with glow, "+12 this week" emerald chip, M–S day labels).

### 4. Repositories Page → `src/pages/RepositoriesPage.tsx`
Prototype: `prototype/assets/repos_analysis.jsx`

- **Empty state** (when no repos connected) — `EmptyState.tsx`: centered glass+gradient-border panel with radar sweep, a large GitHub tile, "Connect a repository to begin", explanatory copy, a large white `Connect GitHub` button, and a "Read-only · revoke anytime" pill. This is the GitHub-first empty state the client asked for; show it whenever the connected-repo list is empty.
- **Populated:** header ("Repositories" + `org · N connected` line + "Connect Repository" white button) → 4 mini stat cards (Repositories / Analyzed / Avg readiness / Open risks, each tinted) → a search + language `<select>` + sort `<select>` bar in a card → a list of **RepoCard**s.
- **RepoCard** (`RepoCard.tsx`): lock/repo icon tile + mono repo name + private/public chip + description; a meta row of chips (language dot+name, ⭐ stars, mono branch, last-scan time OR a blue "Not analyzed" chip); on the right a **62px ScoreRing** + a red "N risks" chip (only if analyzed). Footer divider: verdict pill + "PR risk: …" chip on the left; "View Report" ghost + "Analyze"/"Re-analyze" primary buttons on the right. Loading state = 3 shimmer skeleton blocks.

### 5. Analysis Page → `src/pages/AnalysisPage.tsx`
Prototype: `prototype/assets/repos_analysis.jsx` (`AnalysisPage`, `PipelineRadar`)

- Header: "Analysis in Progress" (→ "Analysis Complete" at 100%) + a "running" chip + mono `owner/repo · branch` + a red **"Cancel Analysis"** button.
- **2-column grid** (`1fr / 340px`):
  - *Center (cinematic):* a glass+gradient-border card with aurora texture containing the **PipelineRadar** — a 300px radar with concentric rings + a slow sweep, the **Ship Report** rocket in a glowing gradient tile at center, and the 4 agent nodes placed N/E/S/W. Dashed connector lines from center to each node light up in agent color as that agent runs/completes; the active node scales up + glows + shows a spinner, completed nodes show a check. Above it a pill announces "<Agent> working…". Below: an **Overall progress** bar (0→100%, tri-color gradient) with a counting `%`. Under the card: the **LiveActivityLog**.
  - *Right:* 4 compact **AgentCard**s with per-agent progress bars; when an agent completes it reveals a 2-stat mini-grid.
- **LiveActivityLog** (`LiveActivityLog.tsx`) — terminal-style card: header (pulsing green dot + "Agent Activity Log" + "stream"), then a mono scroll area (dark `rgba(0,0,0,0.22)` bg) of timestamped lines `HH:MM:SS [Agent] message`, colored per agent, with a blinking cursor block. Example script the client asked for (drive these from real backend events in production):
  ```
  › Cloning northwind-labs/atlas-checkout @ main…
  [RepoLens] scanning dependency graph (1,184 deps)…
  [GuardRail] checking exposed secrets & CVEs…
  ⚠ live Stripe key found in env.example:14
  [TestPilot] generating missing test cases…
  ✓ Readiness score computed: 72 · Needs Fixes
  ```
  Auto-scroll to the newest line. New lines should fade/slide in (transform-based).

### 6. Reports Page → `src/pages/ReportsPage.tsx`
Prototype: `prototype/assets/reports.jsx`

- **ExecutiveReportHeader** (`ExecutiveReportHeader.tsx`) — glass+gradient-border+radar header, 3 columns: a 130px **ScoreRing** | the report identity (eyebrow "Ship Report" + scan timestamp, H1 mono `owner/repo` + verdict pill, and a red **Top Blocker** callout) | a stacked action group (Download PDF, Share — ghost; Re-run — primary).
- **Tab bar** (`border-bottom` hairline): Overview · RepoLens · PlanForge · GuardRail · TestPilot. Active tab = white text + 2px blue underline. Tab content enters with a transform animation on switch.
- **Overview tab:** 3-up top (Score card w/ 92px ring + verdict word; Verdict card w/ pill + explanation; Issues-by-severity card w/ colored-dot counts) → "Score breakdown" card with 4× 84px rings (one per agent area) → **Recommended actions** list (numbered rows, each with the action text, an agent chip, and a priority chip).
- **RepoLens tab:** 2-up — Tech stack (emerald mono chips) + Architecture badges (check/x chips: CI/CD, Dockerfile, Tests, Type Safety, Edge Runtime, E2E Suite) | Dependencies (Total/Outdated/Vulnerable stat tiles) + Architecture risks (amber ⚠ list).
- **PlanForge tab:** a purple-tinted "Next best action" banner + a grid of milestone cards (category chip + priority chip + title + "~N days · est." with clock icon).
- **GuardRail tab:** full-width finding cards colored by severity (critical=red, high=orange, medium=amber, low=blue). Each: severity chip + title, mono file path, description, and an emerald **"Fix:"** recommendation line with an arrow.
- **TestPilot tab:** 3 stat cards (Tests / Coverage % w/ "+18%" chip / QA Status) + a "Suggested tests" list (mono test name + description, a uppercase type chip [unit/integration/e2e], and a priority chip).

---

## Interactions & Behavior
- **Routing / journey:** Landing `Connect GitHub` (any instance) → opens Connect modal → on authorize → app at Dashboard. `View Demo` / `Sign in` → straight into the app (demo). In production, wire these to your real auth + router (e.g. React Router) instead of the prototype's single-component `view`/`page` state.
- **Run Analysis** (topbar or a repo's Analyze button) → navigates to the Analysis page in a live/streaming state. On completion (~all log lines streamed), it marks the repo analyzed (sets score/verdict/lastScan/coverage), unlocks Reports, and routes to the Report. **Cancel** → back to Repositories.
- **Repo switcher** (sidebar) selects the active repo for the topbar/analysis; selecting an analyzed repo also focuses its report.
- **Recent Analyses rows** are clickable → open that repo's report; the inline re-analyze button stops propagation and starts analysis.
- **Report tabs** switch content with an enter animation; **Reports nav item is disabled** until at least one analysis exists.
- **Hover states:** cards lift + blue-tinted border + glow (`card-hover`); buttons lift + shadow; nav items tint; table rows highlight.
- **Animations:** see Design Tokens → Animation guidance. Live preview agents advance on a ~950ms timer (prototype only — drive from real events in prod). Analysis log streams ~760ms/line in the prototype.
- **Responsive:** the two-column hero, dashboard, analysis and report grids should collapse to single column on narrow viewports; the sidebar should become a drawer/hamburger on mobile (the prototype is desktop-first — implement the mobile collapse using your existing responsive patterns). Hit targets ≥44px. Wrap chip rows.

## State Management
- `view` (`landing | app`), `page` (`dashboard | repositories | analysis | reports`) → replace with your router.
- `repos[]` (connected repositories), `currentRepo` (topbar/analysis target), `reportRepo` (focused report), `analyzeRepo` (in-flight), `analyzing` (bool), `hasReport` (gates Reports nav), `showConnect` (modal).
- Data fetching (production): GitHub OAuth → list repos → trigger analysis (ideally a streaming/SSE/websocket endpoint feeding the live log + per-agent progress) → fetch the assembled report. The prototype's `REPORT`/`REPOS` shapes (in `prototype/assets/data.jsx`) are a ready blueprint for the backend payloads.

## Assets
- **Logo / brand mark** — a **custom geometric ShipMate mark** drawn as inline SVG (a rounded-square tile with a blue→cyan gradient, a compass ring with N/E/S/W ticks, and a compass-needle/sail pointing north). Source: `prototype/assets/ui.jsx` (`LogoMark`, `Wordmark`). Reproduce as a React component or export to SVG; it replaces the old 🚢 emoji. The favicon/thumbnail variant is in `ShipMate AI.html` (`<template id="__bundler_thumbnail">`).
- **Icons** — the prototype hand-draws a lucide-style set in `prototype/assets/ui.jsx` (`ICONS`). **In the target codebase use `lucide-react` directly.** Suggested mappings: RepoLens→`Radar`, PlanForge→`Compass`, GuardRail→`ShieldCheck`, TestPilot→`FlaskConical`, Ship Report→`Rocket`; plus `Github, Play, Zap, AlertTriangle, CheckCircle2, Clock, GitBranch, Lock, Star, Search, Filter, Bell, LogOut, Download, Share2, RefreshCw, Sparkles, Target, Gauge, Cpu, Activity, Terminal, FileText, LayoutGrid`.
- **No external images** — all visuals are CSS/SVG. No raster assets to migrate.

## Files (in this bundle, under `prototype/`)
- `ShipMate AI.html` — entry; load order of the JSX modules + favicon thumbnail.
- `assets/shipmate.css` — **the full design system** (tokens, buttons, cards, chips, nav, table, tabs, inputs, radar/compass primitives, keyframes). Closest thing to a spec for `src/index.css` additions.
- `assets/ui.jsx` — icons, `LogoMark`/`Wordmark`, `ScoreRing`, `CountUp`, `Badge`, `Reveal`, agent + score helpers.
- `assets/data.jsx` — mock GitHub account, repos, the full report payload, the live-log script (= backend payload blueprints).
- `assets/components.jsx` — `RadarBg`, `GitHubConnectButton`, `Spinner`, `WorkflowPipeline`, `AgentStatusCard`, `LiveActivityLog`, `EmptyState`, `RepoRiskCard`, `VerdictPill`.
- `assets/landing.jsx` — full landing page incl. the live hero preview.
- `assets/appshell.jsx` — sidebar, repo switcher, topbar, connect modal.
- `assets/dashboard.jsx` — dashboard incl. deployment-readiness hero card + AI insights.
- `assets/repos_analysis.jsx` — repositories page + cinematic analysis page + radar.
- `assets/reports.jsx` — executive report header + all 5 tabs.
- `assets/app.jsx` — root: routing, connect flow, analysis→report transitions, state.

To run the reference locally: open `ShipMate AI.html` in a browser (no build step — it transpiles JSX via Babel in-page).
