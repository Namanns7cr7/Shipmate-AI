# Plan: Dead Code Cleanup + End-to-End Verification

## Context

The ShipMate AI frontend completed a full UI redesign (8 phases). New page and UI components were written from scratch; old implementations were never deleted. Additionally, some cleanup hacks (`void _scoreColor`) were left in newly written pages. This plan removes all dead code and verifies the full app flow works in the browser.

---

## Phase 1 — Dead Code Cleanup

### 1a. Delete 19 obsolete files

Confirmed zero imports for all of these:

**`src/tabs/` (6 files)** — replaced by inline tabs in `ReportsPage.tsx`
- `OverviewTab.tsx`, `PlanTab.tsx`, `ReleaseTab.tsx`, `RepoTab.tsx`, `SecurityTab.tsx`, `TestsTab.tsx`

**`src/components/` root-level (8 files)** — all replaced by new counterparts
- `AgentSwarm.tsx`, `GitHubUserProfile.tsx`, `LandingPage.tsx`, `ReadinessScore.tsx`
- `ReportTabs.tsx`, `RiskCard.tsx`, `Sidebar.tsx`, `TaskCard.tsx`

**`src/components/dashboard/`**
- `DashboardShell.tsx` — replaced by `DashboardPage.tsx`; uses old `.glass-card` classes throughout

**`src/components/landing/` (3 files)** — not imported by new `LandingPage.tsx`
- `DashboardPreview.tsx`, `SecuritySection.tsx`, `WorkflowSection.tsx`

**Acceptance criteria:** `grep -r "DashboardShell\|AgentSwarm\|ReportTabs\|ReadinessScore\|DashboardPreview\|SecuritySection" src/` returns nothing after deletion.

---

### 1b. Remove import suppression hacks

Two files import `scoreColor` but don't use it, suppressed with a `void` hack:

```typescript
// src/pages/RepositoriesPage.tsx — lines 130-131
const _scoreColor = scoreColor; void _scoreColor;

// src/pages/ReportsPage.tsx — lines 354-355
const _sc = scoreColor; void _sc;
```

**Fix:** Remove the import line AND the suppression lines in both files.

---

### 1c. Clean up `src/App.css`

Check if `App.css` is imported anywhere after the deletions. If not, delete it. If still imported, strip the unused rules.

---

### 1d. Update `CLAUDE.md`

Refresh the design section to describe the new component tree and remove references to deleted files.

**✓ Phase 1 checkpoint:** `npx tsc --noEmit && npm run lint` must both pass with zero errors/warnings.

---

## Phase 2 — End-to-End Verification

### 2a. Validate port/CORS configuration

**Known risk:** `GITHUB_REDIRECT_URI=http://localhost:5173/github/callback` in `backend/.env`. If Vite starts on 5174 (port conflict), OAuth breaks.

**Fix:** Document in `CLAUDE.md` that port 5173 must be free. Confirm `vite.config.ts` has `port: 5173` (it does). Confirm backend CORS allows both 5173 and 5174 (it does in `main.py`).

---

### 2b. Run the full stack and walk each screen

```bash
# Backend
cd backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000

# Frontend  
cd frontend && npm run dev   # must claim port 5173
```

**Verification journey:**

| Step | Success condition |
|------|-------------------|
| Landing page loads | Navbar, hero with live preview, pipeline, agent cards, CTA all visible |
| Connect GitHub | OAuth popup opens at `github.com/login/oauth/…` |
| Auth success | Popup closes, Dashboard renders with user greeting |
| Repos load | Repo cards appear in Repositories page |
| Analyze a repo | Analysis page shows PipelineRadar + live log |
| Analysis completes | Auto-navigates to Reports |
| All 5 report tabs | Overview / RepoLens / PlanForge / GuardRail / TestPilot render without crash |
| Reports locked state | Nav "Reports" is locked until first analysis |
| Logout | localStorage cleared, lands on landing page |

---

### 2c. Fix runtime bugs found during 2b

Anticipated issues:
- **`GitHubCallback.tsx`** uses Tailwind classes (`bg-slate-950`, `text-blue-400`) — migrate to new CSS system (`var(--bg)`, `.card`, etc.)
- **Empty dashboard** — verify graceful "no report yet" state renders correctly
- **Cancel analysis** — verify returning to Repos doesn't crash
- **CORS errors** — verify backend reaches frontend at the correct port

---

### 2d. Final validation

```bash
cd frontend && npx tsc --noEmit && npm run lint
```

Both must be clean.

---

## Dependency Order

```
1a → 1b → 1c → 1d → [tsc + lint ✓] → 2a → 2b → 2c → 2d [tsc + lint ✓]
```

Phase 1 completes before Phase 2 starts.

---

## Files Modified

| File | Change |
|------|--------|
| `src/tabs/*.tsx` (×6) | Delete |
| `src/components/ReportTabs.tsx` | Delete |
| `src/components/dashboard/DashboardShell.tsx` | Delete |
| `src/components/AgentSwarm.tsx` + 7 others | Delete |
| `src/components/landing/DashboardPreview.tsx` + 2 others | Delete |
| `src/pages/RepositoriesPage.tsx` | Remove scoreColor import + void hack |
| `src/pages/ReportsPage.tsx` | Remove scoreColor import + void hack |
| `src/App.css` | Delete or strip |
| `CLAUDE.md` | Refresh design section |
| `src/pages/GitHubCallback.tsx` | Migrate to new CSS system |
