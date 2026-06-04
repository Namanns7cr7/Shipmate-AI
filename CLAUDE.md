# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Frontend — port MUST be 5173 (OAuth redirect URI is hardcoded to this port)
cd frontend && npm run dev       # starts on port 5173
npm run build                    # tsc -b && vite build
npm run lint
npx tsc --noEmit                 # type-check only

# Backend
cd backend && venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

> **Port note:** If port 5173 is already in use, Vite falls back to 5174 and GitHub OAuth breaks. Kill any process holding 5173 before starting the dev server.

---

## Architecture

### Frontend (`frontend/src/`)

```
src/
├── App.tsx                  — App shell: auth gate, routing (page state), sidebar + topbar, agent simulation
├── main.tsx                 — Entry; routes /github/callback to GitHubCallback, else App
├── index.css                — Full design system (CSS vars, utility classes, keyframes)
├── lib/
│   ├── agents.ts            — AGENTS[], PIPE[], scoreColor(), scoreTone(), LANG_COLORS
│   └── api.ts               — Axios API client (getRepos, getBranches, getPulls, analyze)
├── hooks/
│   └── useGithubAuth.ts     — GitHub OAuth: popup flow, localStorage token, postMessage listener
├── types/index.ts           — All TypeScript interfaces (GitHubRepo, ShipMateReport, AgentProgress…)
├── components/
│   ├── ui/                  — Reusable design-system components
│   │   ├── LogoMark.tsx     — Geometric compass SVG mark + Wordmark
│   │   ├── RadarBg.tsx      — Radar/compass backdrop (aurora blobs, compass rings, sweep)
│   │   ├── ScoreRing.tsx    — Animated SVG score ring with CountUp
│   │   ├── VerdictPill.tsx  — Ready / Needs Fixes / Blocked chip + toVerdict() helper
│   │   ├── GitHubConnectButton.tsx — White/primary button with GitHub SVG icon
│   │   ├── GitHubIcon.tsx   — Inline GitHub SVG (lucide-react 1.x has no Github export)
│   │   ├── WorkflowPipeline.tsx — Autoplay node pipeline band
│   │   ├── AgentCard.tsx    — Agent status card (pending/running/complete/error + stats)
│   │   ├── LiveActivityLog.tsx — Terminal-style timestamped log stream
│   │   ├── EmptyState.tsx   — GitHub-first empty state with radar texture
│   │   ├── RepoCard.tsx     — Repository card with score ring + analyze button
│   │   └── Reveal.tsx       — Transform-only scroll-reveal (whileInView, no opacity stranding)
│   ├── app/
│   │   └── AppSidebar.tsx   — 248px sidebar: LogoMark, repo switcher dropdown, nav items, user row
│   └── landing/
│       ├── LandingPage.tsx  — Root; composes all landing sections
│       ├── Navbar.tsx       — Fixed 68px nav: LogoMark, centered links, Sign in + Connect GitHub
│       ├── Hero.tsx         — Two-column: headline + LiveAgentPreview + workflow pipeline band
│       ├── LiveAgentPreview.tsx — Animated preview card cycling agent states
│       ├── ValueBadges.tsx  — 5 feature chips (PR Risk, Security, Tests, CI/CD, Score)
│       ├── AgentCards.tsx   — 5 agent cards grid (4 agents + Ship Report)
│       ├── WhySection.tsx   — 3 "why" cards
│       └── CTASection.tsx   — Radar-texture CTA glass card + footer
└── pages/
    ├── DashboardPage.tsx    — Deployment Readiness hero card, agent summary row, analyses table, AI insights
    ├── RepositoriesPage.tsx — EmptyState or stat cards + search/filter + RepoCard list
    ├── AnalysisPage.tsx     — PipelineRadar + live log + per-agent AgentCards
    ├── ReportsPage.tsx      — ExecutiveReportHeader + 5 tabs (Overview/RepoLens/PlanForge/GuardRail/TestPilot)
    └── GitHubCallback.tsx   — OAuth callback handler (popup postMessage or redirect)
```

### Backend (`backend/app/`)

```
app/
├── main.py                  — FastAPI app, CORS, routes
├── api/routes/
│   ├── auth.py              — GET /api/auth/github/* (login, callback, me, repos, branches, pulls)
│   └── analysis.py          — POST /api/analyze (triggers 4-agent pipeline)
├── orchestrator/
│   └── shipmate_orchestrator.py — RepoLens → PlanForge/GuardRail/TestPilot → Scoring → Report
├── agents/                  — base_agent.py + 4 agent implementations
├── services/                — llm_service, github_api_service, repo_analysis_service, scoring_service, report_service
└── schemas/                 — agent_schemas.py (ShipMateReport + per-agent outputs), api_schemas.py
```

---

## Design System

### CSS Variables (`src/index.css`)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#070c18` | Page background |
| `--panel` | `rgba(13,21,40,0.72)` | Glass card background |
| `--line` | `rgba(255,255,255,0.07)` | Default hairlines |
| `--line-2` | `rgba(255,255,255,0.12)` | Hover / emphasis borders |
| `--ink` | `#f3f6fc` | Primary text |
| `--ink-2` | `#aeb9cf` | Secondary text |
| `--ink-3` | `#6f7d97` | Muted text |
| `--ink-4` | `#495368` | Faint / disabled text |

**Accent hex values:** `--blue #3b82f6` · `--blue-2 #60a5fa` · `--cyan #22d3ee` · `--purple #8b5cf6` · `--emerald #10b981` · `--amber #f59e0b` · `--orange #f97316` · `--red #ef4444`

### Key CSS Classes

| Class | Purpose |
|---|---|
| `.card` | Glass card: `var(--panel)` bg + `var(--line)` border + `blur(14px)` |
| `.card-hover` | Lift + blue glow on hover |
| `.glow-border` | Gradient hairline border (blue→purple→cyan via mask-composite) |
| `.grid-bg` | Radar grid: radial glow + 46px line grid |
| `.compass-ring` | Decorative concentric circle |
| `.radar-sweep` | Rotating conic-gradient cyan sector |
| `.aurora` | Blurred radial blob (position with inline style) |
| `.btn` · `.btn-primary` · `.btn-secondary` · `.btn-light` · `.btn-ghost` · `.btn-danger` | Button variants |
| `.btn-sm` · `.btn-lg` | Button size modifiers |
| `.pill` | Rounded-full label chip |
| `.chip` | 8px-radius label chip |
| `.tone-{blue\|cyan\|purple\|emerald\|amber\|orange\|red\|slate}` | Semantic color modifier for `.pill` / `.chip` |
| `.nav-item` · `.nav-item.active` · `.nav-item.disabled` | Sidebar nav button states |
| `.tbl` | Table base styles |
| `.tab` · `.tab.active` | Tab bar button states |
| `.input` | Form input base |
| `.track` | Progress bar track; fill with `<i style="width:X%">` |
| `.eyebrow` | `11px / 700 / uppercase / 0.18em spacing` label |
| `.mono` | JetBrains Mono font |
| `.muted` | `color: var(--ink-3)` |
| `.skel` | Shimmer skeleton block |
| `.dot` · `.dot-pulse` | 7px status dot with ping animation |

### Agent Colors

| Agent | Hex | Tone class |
|---|---|---|
| RepoLens | `#10b981` | `tone-emerald` |
| PlanForge | `#8b5cf6` | `tone-purple` |
| GuardRail | `#f59e0b` | `tone-amber` |
| TestPilot | `#22d3ee` | `tone-cyan` |
| Ship Report | `#60a5fa` | `tone-blue` |

Score thresholds: `≥80 → emerald` · `≥60 → blue` · `≥40 → amber` · else `red`

### Important Notes

- **`Github` is not in lucide-react 1.x** — use `src/components/ui/GitHubIcon.tsx` instead.
- **`Reveal` uses transform-only** (`initial={{ y: 20 }}`) — never animates opacity, so content is never stranded invisible.
- **Routing** is a `page` useState variable in `App.tsx`, not a router library.
- **Agent simulation** is client-side timed delays in `App.tsx#useAgentSimulation`; the real pipeline runs synchronously in the backend.
