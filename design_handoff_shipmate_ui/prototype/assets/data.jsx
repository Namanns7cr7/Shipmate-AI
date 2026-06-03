/* ShipMate AI — demo data (believable GitHub account + analysis findings) */

const GH_USER = { login: "alex-rivera", name: "Alex Rivera", initials: "AR", org: "northwind-labs" };

const LANGS = {
  TypeScript: "#3178c6", Python: "#3572A5", Go: "#00ADD8",
  Rust: "#dea584", JavaScript: "#f1e05a", Kotlin: "#A97BFF",
};

const REPOS = [
  {
    id: "atlas-checkout", name: "atlas-checkout", owner: "northwind-labs", private: true,
    language: "TypeScript", stars: 248, branch: "main", desc: "Next.js checkout & payments surface for Atlas commerce.",
    lastScan: "4 min ago", score: 72, verdict: "Needs Fixes",
    risks: { critical: 1, high: 3, medium: 6, low: 4 }, coverage: 61, coverageDelta: 18, prRisk: "High", primary: true,
  },
  {
    id: "orbital-api", name: "orbital-api", owner: "northwind-labs", private: true,
    language: "Go", stars: 511, branch: "main", desc: "Core REST + gRPC gateway powering Orbital services.",
    lastScan: "2 days ago", score: 88, verdict: "Ready",
    risks: { critical: 0, high: 1, medium: 3, low: 5 }, coverage: 84, coverageDelta: 6, prRisk: "Low",
  },
  {
    id: "ledger-service", name: "ledger-service", owner: "northwind-labs", private: true,
    language: "Rust", stars: 132, branch: "release/2.4", desc: "Double-entry ledger & reconciliation engine.",
    lastScan: "6 hours ago", score: 54, verdict: "Blocked",
    risks: { critical: 2, high: 4, medium: 2, low: 3 }, coverage: 47, coverageDelta: 0, prRisk: "Critical",
  },
  {
    id: "pulse-dashboard", name: "pulse-dashboard", owner: "northwind-labs", private: false,
    language: "TypeScript", stars: 1043, branch: "main", desc: "Public analytics dashboard & embeddable widgets.",
    lastScan: null, score: null, verdict: null,
    risks: { critical: 0, high: 0, medium: 0, low: 0 }, coverage: null, coverageDelta: 0, prRisk: null,
  },
  {
    id: "drift-cli", name: "drift-cli", owner: "northwind-labs", private: false,
    language: "Python", stars: 367, branch: "main", desc: "Infra drift detection CLI for Terraform & Pulumi.",
    lastScan: null, score: null, verdict: null,
    risks: { critical: 0, high: 0, medium: 0, low: 0 }, coverage: null, coverageDelta: 0, prRisk: null,
  },
];

/* full report payload for the primary repo (atlas-checkout) */
const REPORT = {
  repo: "atlas-checkout",
  score: 72,
  verdict: "Needs Fixes",
  scannedAt: "Jun 3, 2026 · 14:08 UTC",
  commit: "a9f3c21",
  branch: "main",
  topBlocker: "Stripe secret key committed to env.example — rotate & purge before deploy.",
  breakdown: [
    { key: "repolens", label: "Repo Health", score: 81 },
    { key: "planforge", label: "Delivery", score: 74 },
    { key: "guardrail", label: "Security", score: 58 },
    { key: "testpilot", label: "Testing", score: 66 },
  ],
  actions: [
    { p: "high", text: "Rotate the exposed Stripe live key and remove it from git history.", agent: "GuardRail" },
    { p: "high", text: "Add input validation on /api/checkout — unvalidated amount field.", agent: "GuardRail" },
    { p: "medium", text: "Generate tests for the discount-engine module (0% covered).", agent: "TestPilot" },
    { p: "medium", text: "Pin next@14 — currently floating on ^14, CVE in 14.1.0.", agent: "RepoLens" },
    { p: "low", text: "Split the 1.2k-line CheckoutForm into smaller components.", agent: "PlanForge" },
  ],
  repolens: {
    stack: ["TypeScript", "Next.js 14", "React 18", "Stripe", "Prisma", "PostgreSQL", "Tailwind", "Zod"],
    arch: [
      { label: "CI/CD", on: true }, { label: "Dockerfile", on: true },
      { label: "Tests", on: true }, { label: "Type Safety", on: true },
      { label: "Edge Runtime", on: false }, { label: "E2E Suite", on: false },
    ],
    deps: { total: 1184, outdated: 23, vulnerable: 4 },
    risks: [
      "next floating on ^14 — known CVE in 14.1.0 (RSC cache poisoning).",
      "lodash 4.17.19 is below the prototype-pollution patch line.",
      "Two transitive deps unmaintained > 24 months.",
    ],
  },
  planforge: {
    next: "Resolve the GuardRail security blockers, then ship the checkout refactor behind a flag.",
    milestones: [
      { title: "Security remediation sprint", cat: "Security", days: 2, p: "high" },
      { title: "Raise checkout coverage to 80%", cat: "Quality", days: 3, p: "medium" },
      { title: "Decompose CheckoutForm component", cat: "Refactor", days: 4, p: "low" },
      { title: "Add edge-runtime A/B for pricing", cat: "Feature", days: 5, p: "low" },
    ],
  },
  guardrail: {
    findings: [
      { sev: "critical", title: "Stripe live secret key committed", desc: "A live sk_live_… key is present in env.example and reachable in git history.", rec: "Rotate the key in Stripe and purge it from history with git-filter-repo.", file: "env.example:14" },
      { sev: "high", title: "Unvalidated amount on checkout", desc: "POST /api/checkout trusts a client-supplied amount with no server-side validation.", rec: "Recompute the order total server-side and validate with Zod.", file: "app/api/checkout/route.ts:42" },
      { sev: "high", title: "Missing rate limit on auth", desc: "The /api/login route has no throttling, enabling credential stuffing.", rec: "Add an IP + account rate limit (e.g. Upstash ratelimit).", file: "app/api/login/route.ts:9" },
      { sev: "high", title: "Verbose error leakage", desc: "Stack traces are returned to the client in production builds.", rec: "Strip error internals behind a generic 500 in production.", file: "lib/handler.ts:71" },
      { sev: "medium", title: "Permissive CORS policy", desc: "Access-Control-Allow-Origin is set to * on API routes.", rec: "Restrict origins to the known web app domains.", file: "middleware.ts:18" },
      { sev: "medium", title: "Outdated crypto helper", desc: "Password reset tokens use Math.random instead of a CSPRNG.", rec: "Switch to crypto.randomBytes for token generation.", file: "lib/token.ts:5" },
    ],
  },
  testpilot: {
    tests: 214, coverage: 61, delta: 18, qa: "At Risk",
    suggested: [
      { name: "discount-engine.applyCode()", type: "unit", p: "high", desc: "No tests cover stacked & expired promo codes." },
      { name: "checkout.route POST", type: "integration", p: "high", desc: "Validate rejection of negative & tampered amounts." },
      { name: "useCartTotals()", type: "unit", p: "medium", desc: "Edge cases for tax rounding and multi-currency." },
      { name: "PaymentRetry flow", type: "e2e", p: "medium", desc: "Simulate a declined card then a successful retry." },
    ],
  },
};

/* live analysis log lines, streamed during the Analysis page */
const LOG_SCRIPT = [
  { agent: "system", text: "Cloning northwind-labs/atlas-checkout @ main…", tone: "slate" },
  { agent: "system", text: "Repository acquired · 1,184 files · 64.2k LOC", tone: "slate" },
  { agent: "RepoLens", text: "scanning dependency graph (1,184 deps)…", tone: "emerald" },
  { agent: "RepoLens", text: "stack detected: Next.js 14 · Prisma · Stripe", tone: "emerald" },
  { agent: "RepoLens", text: "4 vulnerable, 23 outdated dependencies flagged", tone: "emerald" },
  { agent: "PlanForge", text: "mapping delivery surface & ownership…", tone: "purple" },
  { agent: "PlanForge", text: "sequenced 4 milestones · critical path = security", tone: "purple" },
  { agent: "GuardRail", text: "checking exposed secrets & CVEs…", tone: "amber" },
  { agent: "GuardRail", text: "⚠ live Stripe key found in env.example:14", tone: "red" },
  { agent: "GuardRail", text: "6 findings · 1 critical · 3 high", tone: "amber" },
  { agent: "TestPilot", text: "generating missing test cases…", tone: "cyan" },
  { agent: "TestPilot", text: "coverage modelled 61% → 79% with 4 suites", tone: "cyan" },
  { agent: "system", text: "Synthesising Ship Report…", tone: "slate" },
  { agent: "system", text: "✓ Readiness score computed: 72 · Needs Fixes", tone: "emerald" },
];

Object.assign(window, { GH_USER, LANGS, REPOS, REPORT, LOG_SCRIPT });
