# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Design System

### Color Palette
- **Page background:** `#070c18` / `#080c14` (near-black navy)
- **Card background:** `rgba(11,18,35,0.9)` — dark navy with slight transparency
- **Sidebar background:** `linear-gradient(180deg, #070d1a 0%, #060b16 100%)`
- **Borders:** `rgba(255,255,255,0.06)` (subtle) · `rgba(255,255,255,0.1)` (hover)
- **Text primary:** `text-white` / `text-slate-200`
- **Text secondary:** `text-slate-400` / `text-slate-500`
- **Text muted:** `text-slate-600`

**Accent colors (used consistently for agents, badges, tags):**
| Color | Hex | Use |
|-------|-----|-----|
| Blue | `#3b82f6` | Primary actions, active nav, repo health |
| Cyan | `#0891b2` | Button gradients, secondary accent |
| Purple | `#8b5cf6` | PlanForge agent, delivery planning |
| Emerald | `#10b981` | Success, "ready", RepoLens agent |
| Amber | `#f59e0b` | Warning, GuardRail agent, medium severity |
| Red | `#ef4444` | Critical/error |
| Orange | `#f97316` | High severity |

### Global CSS Classes (`src/index.css`)
- `.glass-card` — `bg-[#111827]/85 backdrop-blur-[12px]` with subtle blue border, glows on hover
- `.gradient-border` — wraps element with an animated blue→purple→cyan gradient border (pseudo-element)
- `.neon-text` — blue-to-purple gradient text (`#60a5fa` → `#a78bfa`)
- `.neon-green` — green-to-cyan gradient text
- `.grid-bg` — subtle 40px dot-grid background overlay (blue tint, 3% opacity)
- `.btn-primary` — blue→purple gradient button, lifts on hover with blue glow shadow
- `.btn-secondary` — dark transparent button with subtle border, glows blue on hover
- `.shimmer` — animated shimmer loading effect
- `.score-ring` — drop-shadow filter for SVG score rings
- `.tab-active` / `.tab-inactive` — tab button states

**Badge classes:**
- `.badge-critical` — red · `.badge-high` — orange · `.badge-medium` — amber · `.badge-low` — green

### Typography
- Font: `Inter` (body), `JetBrains Mono` / `font-mono` (code, repo names, timestamps)
- Page headings: `text-[22px] font-black text-white tracking-tight`
- Section labels: `text-xs font-bold text-slate-500 uppercase tracking-wider`
- Body: `text-sm text-slate-400 leading-relaxed`

### Shared UI Patterns
- **Cards:** `rounded-2xl p-5 border border-white/6` + `background: rgba(11,18,35,0.9)`
- **Small cards:** `rounded-xl p-4`
- **Pill badges:** `text-[10px] font-bold px-2.5 py-0.5 rounded-full border`
- **Tag chips:** `text-[10px] font-medium px-2 py-0.5 rounded-full border`
- **Primary gradient button:** `background: linear-gradient(135deg, #1d4ed8, #0891b2)` + `rounded-xl text-xs font-bold text-white`
- **Ghost button:** `border border-white/8 text-slate-300 hover:text-white hover:border-white/15 rounded-xl`
- **Score rings:** SVG circle with `stroke-dasharray` animation (Framer Motion), color thresholds: ≥80 emerald, ≥60 blue, ≥40 amber, else red
- **Animated progress bar:** `h-1.5 rounded-full` track + Motion `width` animation from 0 to value%
- **Page enter animation:** `initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}` on page headers
- **Card stagger:** `transition={{ delay: index * 0.05 }}` on list items

---

## Pages

### Landing Page (`src/components/landing/`)
Full-screen marketing page shown when not authenticated. Background: `bg-slate-950`. Sections stacked vertically:

**Navbar** (`Navbar.tsx`) — fixed, `h-16`, 3-column grid (`logo | nav links | CTA`). Transparent until scrolled, then `bg-slate-950/90 backdrop-blur-lg border-b border-slate-800/60`. Logo: 🚢 emoji + "ShipMate **AI**" (blue). Desktop nav links: text buttons. CTA: white button with GitHub SVG icon. Mobile: hamburger menu slides down.

**Hero** (`Hero.tsx`) — two-column grid (text left, mock dashboard card right). Background uses `.grid-bg` + 3 animated blur blobs (blue/purple/cyan, `blur-3xl`). Left: badge chip → H1 with `.neon-text` gradient → subtitle → two CTA buttons (`.btn-primary` + `.btn-secondary`) → trust checkmarks. Right: `.gradient-border` wrapping a `.glass-card` showing a mock readiness score ring, 3 stat rows, 2×2 agent mini-cards, footer stats. Scroll indicator at bottom animates with bounce.

**AgentCards** (`AgentCards.tsx`) — section with 4 agent feature cards in a grid.

**WorkflowSection** (`WorkflowSection.tsx`) — step-by-step workflow explanation.

**DashboardPreview** (`DashboardPreview.tsx`) — scrollable preview of the app UI.

**SecuritySection** (`SecuritySection.tsx`) — security feature highlights.

**CTASection** (`CTASection.tsx`) — final call-to-action with GitHub connect button.

---

### App Shell (authenticated)
Layout: `flex min-h-screen bg-[#070c18]`. Left: fixed `w-56` sidebar. Right: `flex-1 overflow-y-auto h-screen` with a sticky topbar.

**Sidebar** (`src/components/app/AppSidebar.tsx`) — `w-56`, dark navy gradient. Sections:
1. Brand: 🚢 icon in blue→cyan gradient square + "ShipMate **AI**" text
2. `<hr>` divider (`bg-white/5`)
3. Nav items: icon + label, `rounded-xl px-4 py-2.5`. Active state: blue gradient background (`rgba(37,99,235,0.25)`) + blue border + blue dot indicator. Disabled items: `text-slate-600 cursor-not-allowed`
4. Bottom: "All Systems Operational" pill (emerald glow) + user avatar row (avatar, name, logout button reveals on hover)

**Topbar** (in `App.tsx`) — `h-14 sticky top-0 bg-[#070c18]/95 backdrop-blur-xl border-b border-slate-800/50`. Left: breadcrumb "ShipMate AI / PageName". Right: animated emerald pulse dot + `@username` + avatar.

---

### Dashboard Page (`src/pages/DashboardPage.tsx`)
`px-8 py-7 max-w-[1080px] space-y-6`

1. **Header row** — greeting text (`text-[22px] font-black`) + "View Reports" ghost button
2. **4-column stat row** — `StatCard` components: icon in colored square (`w-9 h-9 rounded-xl`), large number (`text-2xl font-black`), label, trend badge (emerald up / red down with `TrendingUp`/`TrendingDown` lucide icons). Backgrounds: blue/purple/emerald/red tinted.
3. **Two-column layout** (table left, insights right):
   - *Recent Analyses table* — dark card, thead with 10px uppercase labels, rows hover `bg-white/3`. Score shown as `ScorePill` (colored rounded badge). Status as colored pill badge using `REC` map.
   - *AI Insights panel* — highest risk repo with red-tinted card + critical issue + recommendation + "View Analysis" gradient button. Below: *Trends bar chart* — 7 bars (`h-14`), last bar blue gradient, others `rgba(59,130,246,0.2)`, day labels below.

---

### Repositories Page (`src/pages/RepositoriesPage.tsx`)
`px-8 py-7 max-w-[1080px] space-y-6`

1. **Header row** — "Repositories" title + "Connect Repository" gradient button
2. **4 mini stat cards** — colored tinted backgrounds (blue/emerald/purple/red), large number + label
3. **Search + filter bar** — search input with `Search` icon inset left, language `<select>`, sort `<select>`. All inputs: dark navy bg, `border-white/7`, `rounded-xl`
4. **Repo list** — `RepoCard` per repo:
   - Icon (🔒 private / 📁 public) in `w-10 h-10 rounded-xl`
   - Repo name (`font-bold text-slate-200`) + description
   - Tag chips: language dot + name, private/public badge, star count
   - Right side: `ScoreRing` (56px animated SVG) if analyzed
   - Footer divider: last-analyzed time OR default branch · "View Report" ghost button + "Analyze" gradient button
   - Loading skeleton: 3 `animate-pulse rounded-2xl h-28` placeholders

---

### Analysis Page (`src/pages/AnalysisPage.tsx`)
`px-8 py-7 max-w-[1080px] space-y-6`

1. **Header** — "Analysis in Progress" + repo name + branch info + "Cancel Analysis" red-tinted button
2. **3-column grid:**
   - *Left column* — 2 `AgentCard` components (RepoLens, PlanForge)
   - *Center column*:
     - "Ship hologram" — `radial-gradient` dark card (`h-200`), 2 spinning rings (outer slow, inner fast reverse), blue blur glow, floating 🚢 emoji (`drop-shadow` blue glow, bounce animation)
     - Progress bar card — "Overall Progress" label, `%` counter, gradient progress bar
     - Live activity log — pulsing blue dot, scrollable timestamped log entries (monospace timestamps)
   - *Right column* — 2 `AgentCard` components (GuardRail, TestPilot) + "Analysis Information" info card (icon + label + value rows)

**AgentCard** — colored border/bg per agent (emerald/amber/blue/purple). Shows: icon square, name, subtitle, status badge (Complete/Running/Pending/Error). Running: spinner + color text. Complete: 2×2 stat mini-grid (`bg-black/20 rounded-lg`).

---

### Reports Page (`src/pages/ReportsPage.tsx`)
`px-8 py-7 max-w-[1080px] space-y-5`

**Header** — repo name + timestamp + 3 action buttons (Download PDF / Share Report ghost buttons + Re-run gradient button)

**Tab bar** — `border-b border-white/6`, tabs are `px-5 py-3 text-sm font-semibold border-b-2 -mb-px`. Active: `text-white border-blue-500`. Inactive: `text-slate-500 border-transparent`. Tabs: Overview · RepoLens · PlanForge · GuardRail · TestPilot. Tab content animates in with `opacity: 0→1, y: 8→0`.

**Overview tab:**
- 3-column top row: Score card (120px `ScoreRing` + headline), Verdict card (tinted bg per recommendation), Top Issues card (severity counts with colored dots)
- Score Breakdown row: 4×80px score rings in a card with animated progress bars below each
- Recommended Actions list: numbered, priority badge (high=red/medium=amber/low=blue)

**RepoLens tab:** 2-column grid — Tech stack tags (blue chips) + architecture badges (CI/CD, Docker, Tests). Dependencies grouped by type (monospace font chips). Architecture risks with amber ⚠ icon.

**PlanForge tab:** "Next Best Action" banner (blue tint). Milestones as cards with priority badge + days estimate + category.

**GuardRail tab:** Security findings as full-width cards, colored by severity (critical=red, high=orange, medium=amber, low=blue). Each: title, description, recommendation (emerald ›), file path (monospace).

**TestPilot tab:** 3-column stat row (test count, coverage %, QA status). Suggested tests as cards: test name (monospace font), type badge (purple), priority badge, description.

---

## Commands

```bash
# Frontend
cd frontend && npm run dev       # port 5173
npm run build                    # tsc -b && vite build
npm run lint

# Backend
cd backend && venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```
