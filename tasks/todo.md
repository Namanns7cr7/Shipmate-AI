# Todo

## Phase 1 — Dead Code Cleanup

- [ ] **1a** Delete `src/tabs/` (6 files: OverviewTab, PlanTab, ReleaseTab, RepoTab, SecurityTab, TestsTab)
- [ ] **1a** Delete `src/components/ReportTabs.tsx`
- [ ] **1a** Delete `src/components/dashboard/DashboardShell.tsx`
- [ ] **1a** Delete `src/components/AgentSwarm.tsx`
- [ ] **1a** Delete `src/components/GitHubUserProfile.tsx`
- [ ] **1a** Delete `src/components/LandingPage.tsx` (root-level, not landing/)
- [ ] **1a** Delete `src/components/ReadinessScore.tsx`
- [ ] **1a** Delete `src/components/RiskCard.tsx`
- [ ] **1a** Delete `src/components/Sidebar.tsx`
- [ ] **1a** Delete `src/components/TaskCard.tsx`
- [ ] **1a** Delete `src/components/landing/DashboardPreview.tsx`
- [ ] **1a** Delete `src/components/landing/SecuritySection.tsx`
- [ ] **1a** Delete `src/components/landing/WorkflowSection.tsx`
- [ ] **1b** Remove `scoreColor` import + void suppression from `src/pages/RepositoriesPage.tsx`
- [ ] **1b** Remove `scoreColor` import + void suppression from `src/pages/ReportsPage.tsx`
- [ ] **1c** Check and delete/strip `src/App.css`
- [ ] **1d** Update `CLAUDE.md` design section
- [ ] **✓** `npx tsc --noEmit && npm run lint` — zero errors

## Phase 2 — End-to-End Verification

- [ ] **2a** Confirm port 5173 is free; verify Vite claims it; document in CLAUDE.md
- [ ] **2b** Start backend (`uvicorn app.main:app --reload --port 8000`)
- [ ] **2b** Start frontend (`npm run dev` on port 5173)
- [ ] **2b** Walk full journey: landing → OAuth → dashboard → repos → analyze → reports → all tabs → logout
- [ ] **2c** Migrate `src/pages/GitHubCallback.tsx` from Tailwind to new CSS system
- [ ] **2c** Fix any CORS / port / runtime errors found in 2b
- [ ] **2c** Verify empty-state (no report) on Dashboard renders gracefully
- [ ] **2c** Verify Cancel on Analysis page returns to Repos without crash
- [ ] **2d** `npx tsc --noEmit && npm run lint` — zero errors
