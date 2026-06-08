# 🚢 ShipMate AI — Agentic Release-Readiness & Auto-Fix

> Connect a GitHub repo → a swarm of AI agents diagnoses release readiness, then **autonomously fixes** what it finds and opens PRs — with a closed CI feedback loop that repairs its own red builds.

ShipMate analyzes a repository with four diagnostic agents, scores its production readiness (0–100), and — when you ask it to — plans, writes, validates, and ships the fixes as real pull requests. It dogfoods itself: this repo's test count and readiness score were driven up by ShipMate fixing ShipMate.

---

## ✨ What it does

1. **Analyze** — point it at `owner/repo@branch`. Four agents run and produce a scored, code-grounded report.
2. **Build** — it discovers ranked, *grounded* self-improvement opportunities (new features, refactors, tweaks, bugs), each cited against real files.
3. **Actuate** — for a chosen finding (or one-click "Auto-fix"), the Coder agent writes a patch, it passes through lint → scope → pytest → resolution gates, and opens a PR.
4. **Watch** — a CI watcher polls the PR's checks; on red CI it feeds the failure back to the Coder, commits a fix, and loops until green or it gives up (bounded attempts + wall-clock).

### The agents

| Agent | Role |
|---|---|
| 🔍 **RepoLens** | Maps tech stack, entry points, architecture, structure (runs first; enriches the others) |
| 🗺️ **PlanForge** | Delivery milestones, blockers, next best action |
| 🛡️ **GuardRail** | Security findings — secrets, CORS, auth, injection (code-aware, with a false-positive critic) |
| 🧪 **TestPilot** | Coverage gaps + concrete suggested tests |
| 🧠 **Planner / Coder / Decomposer** | Phase 1B+: turn an opportunity into ordered steps, write the code, open the PR |

Outputs a **Readiness Score** with a weighted breakdown, plus a durable history so you can track a repo's trend over time.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend — React 19 + TypeScript + Vite (port 5173)         │
│  Dashboard · Repositories · Analysis (live SSE) · Build ·     │
│  Reports · Auto-fix drawer · CI watch panel                  │
│  Holds an OPAQUE session id (never the raw GitHub token)     │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTPS · Authorization: Bearer <session_id>
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Backend — FastAPI (port 8000)                               │
│                                                              │
│  Routes:  /api/auth/github/*   /api/analyze[/stream]         │
│           /api/build/{plan,execute,runs}  /api/actuate[...]  │
│           /api/auto-fix/start  /api/watcher/*  /api/findings/*│
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ ShipMateOrchestrator                               │    │
│  │   RepoLens → PlanForge ∥ GuardRail ∥ TestPilot     │    │
│  │   → Scoring → Report   (+ anti-recurrence filters) │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ CoderOrchestrator   (lint → scope → pytest gate →  │    │
│  │   resolution → branch/commit/PR → CIWatcher)       │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ LLM provider — ONE switch (SHIPMATE_LLM_PROVIDER):  │    │
│  │   bedrock (default, local/demo) | azure (hosted)   │    │
│  └────────────────────────────────────────────────────┘    │
│  Session vault · RepoIndex cache · unified sqlite store     │
└──────────────────────────────────────────────────────────────┘
                            ▼
        GitHub REST API   ·   AWS Bedrock / Azure OpenAI
```

### Key design points

- **One LLM switch.** `SHIPMATE_LLM_PROVIDER=bedrock` (default — AWS Bedrock Converse, creds via `ada credentials update`) or `azure` (Azure OpenAI tool-calling, for hosted). Same code path; no changes to flip. Everything **fails open** — no/expired creds → heuristic-only outputs, never a crash.
- **Server-side token vault.** The OAuth callback mints an opaque `shipmate_sess_…` id; the raw GitHub token lives only in the backend vault and is resolved at the auth boundary. The browser never holds the raw token.
- **Unified sqlite storage.** One connection manager + location policy (`SHIPMATE_STORE_DIR`, default `/tmp`) backs the inflight registry, report history, OAuth state, and the session vault.
- **RepoIndex cache.** A repo is fetched + RepoLens'd once per `(owner, repo, branch)` and reused across the analyze/build pipelines within a TTL.
- **Anti-recurrence.** Both the analyze and build paths suppress already-shipped / already-implemented / dismissed findings (journal + a capability digest fed into the discovery prompts) so the loop surfaces *new* work, not the same fixes every run.

---

## 🚀 Quick start

### Prerequisites
- **Python 3.11+**, **Node 20+**, **Git**
- A **GitHub OAuth App** (Client ID + Secret) — callback `http://localhost:5173/github/callback`
- For real AI output: **AWS Bedrock** access (`ada credentials update …`) or **Azure OpenAI** keys. Without either, ShipMate still runs in heuristic-only mode.

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                # fill in GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev                         # MUST be port 5173 (OAuth redirect is hardcoded)
```

> **Port note:** if 5173 is taken, Vite falls back to 5174 and OAuth breaks. Free 5173 first.

### 3. Use it
Open `http://localhost:5173` → **Connect GitHub** → pick a repo/branch → **Run Analysis**. Then try the **Build** tab to discover opportunities, or **Auto-fix** to let it open PRs.

### Or with Docker
```bash
docker compose up --build           # backend :8000, frontend :5173
```

---

## ⚙️ Configuration (`backend/.env`)

```bash
# GitHub OAuth (required)
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GITHUB_REDIRECT_URI=http://localhost:5173/github/callback

# LLM provider switch
SHIPMATE_LLM_PROVIDER=bedrock        # bedrock (default) | azure
#   bedrock → AWS creds via the standard chain (ada credentials update …)
#   azure   → AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY / *_DEPLOYMENT

# Storage (sqlite, one base dir; default /tmp). Point at a durable, encrypted
# volume for a hosted deploy — the session vault lives here.
# SHIPMATE_STORE_DIR=/var/lib/shipmate

# See backend/.env.example for the full set: RepoIndex TTL, validation gates,
# session TTL, CORS origins, HSTS, webhook secret.
```

`.env` is gitignored — never commit credentials.

---

## 🔌 API reference (selected)

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/auth/github/login` · `/callback` · `/me` · `/repos` · `/logout` | OAuth + repo listing |
| `POST` | `/api/analyze` · `/api/analyze/stream` | Run the 4-agent analysis (batch / live SSE) |
| `GET` | `/api/repos/{owner}/{repo}/history` | Readiness-score trend |
| `POST` | `/api/build/plan` · `/api/build/execute` | Discover opportunities · plan+critique+(optionally) ship |
| `GET` | `/api/build/runs` · `/api/build/runs/{run_id}` | Durable BuildRun state |
| `POST` | `/api/actuate` · `/api/actuate/stream` | Coder fixes one finding → PR (batch / SSE) |
| `POST` | `/api/auto-fix/start` | One-click autonomous loop (SSE) |
| `GET` | `/api/watcher/*` | CI-watcher status + log tail |
| `POST` | `/api/findings/dismiss` · `/reopen` | Finding journal |
| `GET` | `/health` · `/docs` | Health + Swagger (docs disabled in production) |

Full interactive schema at `/docs` when running locally.

---

## 🧪 Tests & CI/CD

```bash
cd backend && source venv/bin/activate
pytest -q                            # 445 tests, ~68% coverage
```

CI (`.github/workflows/ci.yml`) is a **three-tier, fastest-fails-first** pipeline on every push/PR:

| Tier | Runs | Gates |
|---|---|---|
| **quick-gate** (<60s) | always | `compileall` syntax · flake8 (E9/F63/F7/F82) · `tsc --noEmit` · gitleaks secret scan |
| **test-gate** (2–5m) | always · blocks merge | pytest + coverage (`--cov-fail-under=60`) + JUnit XML · bandit (B307/B302) · backend flake8 style · frontend ESLint |
| **integration-gate** | PR + main | backend Docker build + boot smoke (`GET /health`) |

JUnit XML is uploaded as an artifact so the CIWatcher can feed **structured** test failures (name/file/line/exception) back to the Coder instead of raw logs. A `cancel-in-progress` concurrency group keeps the auto-fix loop's wall-clock bounded. A dependency-guard test fails the build if any declared runtime dep (e.g. `boto3`) goes missing from a clean install.

---

## 📁 Layout

```
backend/
  app/
    main.py                  FastAPI app, CORS, rate-limit + security middleware, lifespan
    api/routes/              auth · analysis · build · actuate · auto_fix · watcher · findings · branches
    api/deps.py              shared auth (session→token resolution) + write-access check
    orchestrator/            ShipMateOrchestrator (4-agent pipeline + anti-recurrence)
    agents/                  repo_lens · plan_forge · guardrail · testpilot · planner · coder · decomposer
    services/                llm_provider (bedrock/azure) · session_store (vault) · sqlite_store ·
                             repo_index · validation_gate · ci_watcher · coder_orchestrator ·
                             finding_critic · opportunity_critic · report_store · github_*
    schemas/                 Pydantic models (ShipMateReport, per-agent outputs, build/actuate)
  scripts/coder_loop.py      CLI autonomous loop (analyze → pick → fix → PR → watch CI)
  tests/                     445 tests
frontend/
  src/                       App shell, pages (Dashboard/Repositories/Analysis/Build/Reports),
                             components/ui, hooks/useGithubAuth, lib/api
.github/workflows/ci.yml     three-tier CI
docker-compose.yml           backend + frontend
DEPLOYMENT.md                Azure deployment notes
```

---

## 🔐 Security model

- Raw GitHub token never reaches the browser (opaque session id only) and is never logged.
- The credential is taken from the `Authorization` header only — not a URL query param (no leakage into logs/Referer/history).
- Repo **write access is verified** before any mutating GitHub call (PRs, branch prune).
- Request bodies scanned for injection patterns; explicit CORS origin allowlist; security headers; HMAC-verified webhooks.
- Coder patches are gated (lint → scope → local pytest → resolution check) before a PR opens. For external repos, an opt-in sandbox validator (`SHIPMATE_TARGET_REPO_GATE=1`) clones + runs the target's own tests — **off by default; runs untrusted code**.

---

## 📝 Notes

- **Branch safety in this fork:** development happens on `feat/bedrock-on-v2`; pushes go to the fork remote.
- **Fail-open everywhere:** expired Bedrock creds or an LLM outage degrade to heuristic output, never an error.
- This README reflects the current Bedrock-default, auto-fix architecture. Some older docs (`DEPLOYMENT.md`) describe the earlier Azure-OpenAI/read-only design and are being updated.

---

*ShipMate AI — diagnose, then actually fix.*
