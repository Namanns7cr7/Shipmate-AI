# 🚀 ShipMate AI — Agentic Engineering Command Center

> **Hackathon Theme:** AI-Powered Production Function: Reinventing Work

ShipMate AI transforms a messy repo, feature request, or team discussion into a complete, execution-ready engineering workflow — powered by 5 specialized AI agents.

---

## ✨ What It Does

Paste a feature request → Click **Run Production Swarm** → Watch 5 agents execute:

| Agent | Output |
|-------|--------|
| 🧠 **Planner** | Frontend/backend/DB tasks, story points, sprint count |
| 🔍 **Repo Analyst** | Files to change, affected APIs, risky dependencies |
| 🧪 **Test Generator** | Unit tests, API tests, edge cases, regression checklist |
| 🛡️ **Security Guard** | CVEs, exposed secrets, auth bypass risks, OWASP findings |
| 🚢 **Delivery Manager** | Sprint plan, standup, PR review, CI/CD recommendations |

**Final output:** Production Readiness Score (0–100) + full Markdown report export.

---

## 🛠 Tech Stack

**Frontend:** React + TypeScript + Vite + Tailwind CSS + Framer Motion + Lucide Icons  
**Backend:** Python FastAPI + Pydantic + Uvicorn  

---

## ⚡ Quick Start

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --port 8000
```

Backend runs at: http://localhost:8000  
API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at: http://localhost:5173

---

## 🎯 Demo Flow

1. Open http://localhost:5173
2. Click **"Use Sample"** to load the demo feature request
3. Click **"Load Sample Repo"** to use the e-commerce demo repo
4. Click **"Run Production Swarm"**
5. Watch 5 agents execute with live animations
6. View the Production Readiness Score and explore all 5 report tabs
7. Click **"Export Report"** to download the full Markdown report

### Sample Feature Request
```
Add login with role-based access and dashboard analytics.

Requirements:
- Support email/password login and Google OAuth
- Three roles: Admin, Editor, Viewer with different permissions
- Admin dashboard with user management
- Analytics dashboard showing MAU, DAU, retention metrics
- All data endpoints secured behind RBAC middleware
```

---

## 📁 Project Structure

```
shipmate-ai/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.tsx          # Navigation sidebar
│   │   │   ├── AgentSwarm.tsx       # Animated agent status cards
│   │   │   ├── ReadinessScore.tsx   # Circular score visualization
│   │   │   ├── ReportTabs.tsx       # Tab navigation + export
│   │   │   └── tabs/
│   │   │       ├── PlanTab.tsx      # Implementation plan
│   │   │       ├── RepoTab.tsx      # Repo impact analysis
│   │   │       ├── TestsTab.tsx     # Test suite
│   │   │       ├── SecurityTab.tsx  # Security risks
│   │   │       └── ReleaseTab.tsx   # Sprint/release plan
│   │   ├── lib/api.ts               # Backend API client
│   │   ├── types/index.ts           # TypeScript types
│   │   └── App.tsx                  # Main dashboard
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI routes
│   │   ├── agents/
│   │   │   ├── planner.py           # Planner Agent
│   │   │   ├── repo_analyst.py      # Repo Analyst Agent
│   │   │   ├── test_generator.py    # Test Generator Agent
│   │   │   ├── security_guard.py    # Security Guard Agent
│   │   │   └── delivery_manager.py  # Delivery Manager Agent
│   │   ├── services/
│   │   │   ├── analyzer.py          # Agent orchestrator + scoring
│   │   │   └── repo_service.py      # ZIP extraction + repo parsing
│   │   └── models/schemas.py        # Pydantic request/response models
│   └── requirements.txt
│
└── README.md
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/analyze` | Run full 5-agent analysis |
| `POST` | `/api/upload-repo` | Upload repository ZIP |
| `GET` | `/api/sample` | Get sample repo context |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI |

---

## 📊 Readiness Score Logic

```
Score = 100
- Task clarity deduction (0–15)
- Test coverage deduction (0–20)  
- Security risk deduction (0–20 based on critical/high findings)
- Deployment risk deduction (0–15)
- Repo impact uncertainty deduction (0–10)
- CI/CD readiness deduction (0–10)
```

---

## 🏆 Hackathon Notes

- **No real LLM calls required** — agents return high-quality simulated outputs
- All agents are pluggable — swap in OpenAI/Gemini API calls in `agents/*.py`
- Report export generates a complete Markdown document for sharing
- Dark mode command center UI designed to wow hackathon judges
