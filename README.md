# 🚀 ShipMate AI — Agentic Engineering Command Center

> **Microsoft-First SaaS Product**: AI-Powered Production Function — Reinventing Work

---

## ✨ What It Does

**ShipMate AI** connects to your GitHub repository, accepts a feature request, and generates a **delivery-readiness analysis** using 5 specialized AI agents running as an agentic swarm.

Paste a feature request → Click **Analyze Delivery Readiness** → Watch 5 agents execute in sequence:

| Agent | Role | Output |
|-------|------|--------|
| 🧠 **Planner Agent** | Decomposes feature into structured engineering tasks | Frontend/backend/DB tasks, story points, sprint count, deployment risks |
| 🔍 **Repo Analyst Agent** | Maps feature impact across the codebase | Files to change, affected APIs, risky dependencies, architecture notes |
| 🧪 **Test Architect Agent** | Creates a complete test suite for the feature | Unit tests, API tests, edge cases, regression checklist, coverage estimate |
| 🛡️ **Security Guard Agent** | Identifies security vulnerabilities and compliance risks | CVEs, exposed secrets, auth bypass risks, OWASP findings, dependency warnings |
| 🚢 **Delivery Manager Agent** | Produces a release-ready sprint plan | Sprint plan, standup summary, PR review notes, CI/CD recommendations |

**Final Output**: Production Readiness Score (0–100) with detailed breakdown + full Markdown report export.

---

## 🏛️ Microsoft-First Architecture

### Frontend
- **React + TypeScript** with Vite
- **Tailwind CSS** for premium SaaS styling
- **Framer Motion** for smooth animations
- **Deployed to**: Azure Static Web Apps
- **GitHub-First UI** with repo/branch selection and feature request input

### Backend
- **FastAPI** with Python 3.11+
- **Read-only GitHub API** integration
- **Mock agent outputs** for demo (Azure OpenAI integration ready)
- **Deployed to**: Azure App Service
- **Environment-ready** for Azure Key Vault, Application Insights

### AI & Cloud Services
- **AI Model**: Azure OpenAI (GPT-4) via Azure AI Foundry
- **Database**: Azure Cosmos DB (report metadata)
- **Storage**: Azure Blob Storage (exported reports)
- **Secrets**: Azure Key Vault
- **Telemetry**: Application Insights
- **CI/CD**: GitHub Actions
- **Authentication**: GitHub App (OAuth)

---

## � Quick Start with GitHub OAuth

### Prerequisites
- GitHub account
- Node.js and Python installed
- GitHub OAuth App credentials (see setup guide)

### Setup Steps

1. **Create GitHub OAuth App**:
   - Visit https://github.com/settings/developers/oauth-apps
   - Click "New OAuth App"
   - Set Authorization callback URL to `http://localhost:8000/github-callback.html`
   - Copy Client ID and Client Secret

2. **Configure Environment**:
   ```bash
   # Backend
   cd backend
   cp .env.example .env
   # Edit .env with your GitHub credentials:
   # GITHUB_CLIENT_ID=your_client_id
   # GITHUB_CLIENT_SECRET=your_client_secret
   ```

3. **Install Dependencies**:
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   
   # Frontend
   cd frontend
   npm install
   ```

4. **Start the Application**:
   ```bash
   # Terminal 1: Backend
   cd backend
   python -m uvicorn app.main:app --reload
   
   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```

5. **Open Dashboard**:
   - Visit http://localhost:5174
   - Click "Connect Your GitHub Account"
   - Select a repository and run analysis

**📖 Detailed Setup**: See [GITHUB_OAUTH_SETUP.md](GITHUB_OAUTH_SETUP.md) for complete instructions, troubleshooting, and production deployment.

---

### User Flow
1. User opens ShipMate AI dashboard
2. User clicks "Connect GitHub"
3. User authorizes ShipMate GitHub App (read-only)
4. User selects a repository
5. User selects a branch
6. User enters a feature request or issue description
7. User clicks "Analyze Delivery Readiness"
8. Four agents run and generate analysis
9. Dashboard displays results + export option

### GitHub App Permissions (Minimum)
- **Contents**: read-only
- **Metadata**: read-only
- **Pull requests**: read-only
- **Issues**: read-only
- **Actions**: read-only

### Security Principles
- ✅ Never expose GitHub tokens in frontend
- ✅ Never expose Azure OpenAI keys in frontend
- ✅ Backend handles all sensitive API calls
- ✅ Mock agent outputs if credentials unavailable
- ✅ Trust message: "ShipMate uses read-only GitHub access. We analyze selected repositories only and never modify your code."

---

## 🗂️ Project Structure

```
shipmate-ai/
├── frontend/                    # React + TypeScript SaaS dashboard
│   ├── src/
│   │   ├── App.tsx            # GitHub-first main app
│   │   ├── components/        # Reusable UI components
│   │   │   ├── Sidebar.tsx    # Navigation sidebar
│   │   │   ├── AgentSwarm.tsx # Agent status timeline
│   │   │   ├── ReadinessScore.tsx # Score visualization
│   │   │   ├── ReportTabs.tsx # Analysis result tabs
│   │   │   └── tabs/          # Individual tab components
│   │   ├── lib/
│   │   │   └── api.ts         # API client
│   │   ├── types/
│   │   │   └── index.ts       # TypeScript interfaces
│   │   ├── App.css
│   │   └── index.css
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/                     # FastAPI Python backend
│   ├── app/
│   │   ├── main.py            # FastAPI app + endpoints
│   │   ├── agents/            # AI agents
│   │   │   ├── planner.py
│   │   │   ├── repo_analyst.py
│   │   │   ├── test_generator.py
│   │   │   ├── security_guard.py
│   │   │   └── delivery_manager.py
│   │   ├── services/          # Business logic
│   │   │   ├── analyzer.py    # Main analysis engine
│   │   │   ├── github_service.py # GitHub integration
│   │   │   ├── repo_service.py   # Repository utilities
│   │   │   └── azure_openai_service.py # LLM abstraction
│   │   └── models/
│   │       └── schemas.py     # Pydantic models
│   ├── requirements.txt
│   ├── verify.py
│   └── main.py (for local dev)
│
└── README.md                    # This file
```

---

## 🔌 API Reference

### GitHub Integration Endpoints

#### `GET /api/github/app-install-url`
Get GitHub App installation URL for OAuth flow.

```
Response:
{
  "install_url": "https://github.com/apps/shipmate-ai/installations/new",
  "permissions": ["Contents: read-only", ...],
  "message": "Click to authorize..."
}
```

#### `GET /api/github/repos`
Get list of repositories accessible to user.

```
Response: [
  {
    "id": "repo-1",
    "name": "shipmate-frontend",
    "full_name": "myorg/shipmate-frontend",
    "description": "...",
    "tech_stack": ["React", "TypeScript"],
    "stars": 42,
    "language": "TypeScript"
  },
  ...
]
```

#### `GET /api/github/repos/{repoId}/branches`
Get branches for a repository.

```
Response: [
  {
    "name": "main",
    "commit": {
      "sha": "abc123...",
      "message": "feat: ..."
    }
  },
  ...
]
```

### Analysis Endpoints

#### `POST /api/analyze`
Run full 5-agent production analysis.

```
Request:
{
  "repo_id": "repo-1",
  "branch": "main",
  "feature_request": "Add GitHub OAuth login...",
  "github_token": "gho_..."  // optional
}

Response:
{
  "repo_summary": {
    "name": "shipmate-frontend",
    "branch": "main",
    "tech_stack": ["React", "TypeScript"],
    "files_to_modify": ["src/App.tsx", ...],
    "stars": 42,
    "language": "TypeScript"
  },
  "agents": {
    "planner": { ... },
    "repo_analyst": { ... },
    "test_generator": { ... },
    "security_guard": { ... },
    "delivery_manager": { ... }
  },
  "readiness_score": 82,
  "recommendation": "Needs fixes before shipping",
  "summary": "ShipMate AI analyzed your feature request...",
  "markdown_report": "# Production Readiness Report\n...",
  "score_breakdown": {
    "task_clarity": 28,
    "test_coverage": 75,
    "security_score": 72,
    ...
  }
}
```

### Report Export

#### `POST /api/reports/export`
Generate exportable report.

#### `GET /api/reports/{analysisId}/download`
Download report as file.

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ (frontend)
- Python 3.11+ (backend)
- Git

### Local Development

#### 1. Clone Repository
```bash
git clone https://github.com/Namanns7cr7/Shipmate-AI.git
cd Shipmate-AI
```

#### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate
  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional for demo)
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4"

# Run backend
python main.py
# Server runs on http://localhost:8000
```

#### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# App runs on http://localhost:5173
```

#### 4. Open Dashboard
Visit `http://localhost:5173` in your browser.

Click "Connect GitHub" to start analyzing repositories!

---

## 🔐 Environment Variables

### Backend (.env)
```
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# GitHub App
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
GITHUB_WEBHOOK_SECRET=your-secret

# Azure Services
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_COSMOS_CONNECTION_STRING=AccountEndpoint=https://...;
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
```

---

## 🧪 Testing Agents Locally

### Run Verification
```bash
cd backend
python verify.py
```

This runs all agents with sample data and validates outputs.

---

## 🔄 Agent Details

### Planner Agent
**Input**: Feature request + repo context
**Output**: 
- Frontend tasks
- Backend tasks
- Database changes
- Test requirements
- Deployment risks
- Story points estimate
- Sprint count

### Repo Analyst Agent
**Input**: Feature request + repo context
**Output**:
- Files to change (with risk levels)
- Affected APIs
- Risky dependencies
- Patterns to follow
- Impact score
- Architecture notes

### Test Architect Agent
**Input**: Feature request + repo context
**Output**:
- Unit tests
- API integration tests
- Edge case scenarios
- Regression checklist
- Test coverage estimate

### Security Guard Agent
**Input**: Feature request + repo context
**Output**:
- Security risks (critical/high/medium/low)
- Exposed secrets check
- Auth bypass risks
- Dependency vulnerabilities
- Unsafe tool calls
- Overall security score

### Delivery Manager Agent
**Input**: All agent outputs + feature request
**Output**:
- Sprint plan (day-by-day tasks)
- Standup summary
- PR review summary
- CI/CD recommendations
- Release readiness score
- Next actions
- Estimated release date

---

## 🚢 Deployment

### Deploy to Azure

#### Frontend: Azure Static Web Apps
```bash
# Build
cd frontend
npm run build

# Deploy via Azure CLI or GitHub Actions
az staticwebapp create --name shipmate-ai --source . --location eastus
```

#### Backend: Azure App Service
```bash
# Create App Service
az appservice plan create --name shipmate-plan --sku B1 --is-linux
az webapp create --plan shipmate-plan --name shipmate-api --runtime "python|3.11"

# Deploy
az webapp up --name shipmate-api --runtime "python:3.11"
```

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Static Web Apps                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │     React + TypeScript Frontend (GitHub-First UI)       │  │
│  │  - GitHub repo selection                                │  │
│  │  - Branch selector                                      │  │
│  │  - Feature request input                                │  │
│  │  - Live agent timeline                                  │  │
│  │  - Analysis result dashboard                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ↕ HTTPS
┌─────────────────────────────────────────────────────────────────┐
│                    Azure App Service                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │      FastAPI Backend + Agent Swarm                       │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────┐    │  │
│  │  │ GitHub Service Layer                           │    │  │
│  │  │ - OAuth flow                                   │    │  │
│  │  │ - Repo/branch enumeration                      │    │  │
│  │  └────────────────────────────────────────────────┘    │  │
│  │                    ↕                                    │  │
│  │  ┌────────────────────────────────────────────────┐    │  │
│  │  │ Agentic Swarm Engine                           │    │  │
│  │  │ ① Planner Agent       ③ Test Architect        │    │  │
│  │  │ ② Repo Analyst        ④ Security Guard        │    │  │
│  │  │ ⑤ Delivery Manager                            │    │  │
│  │  └────────────────────────────────────────────────┘    │  │
│  │                    ↕                                    │  │
│  │  ┌────────────────────────────────────────────────┐    │  │
│  │  │ LLM Abstraction Layer                          │    │  │
│  │  │ - Mock outputs (demo)                          │    │  │
│  │  │ - Azure OpenAI (production)                    │    │  │
│  │  └────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                        ↕
        ┌───────────────────────────────┐
        │    Azure Services Stack       │
        ├───────────────────────────────┤
        │ • Azure OpenAI (GPT-4)       │
        │ • Azure Cosmos DB             │
        │ • Azure Blob Storage          │
        │ • Azure Key Vault             │
        │ • Application Insights        │
        └───────────────────────────────┘
                        ↕
        ┌───────────────────────────────┐
        │    GitHub API                 │
        │ (Read-only access)            │
        └───────────────────────────────┘
```

---

## 🛠️ Development Roadmap

### Phase 1: MVP (Current) ✅
- [x] GitHub OAuth integration (mock)
- [x] Repo/branch selection UI
- [x] Feature request input
- [x] 5-agent swarm architecture
- [x] Mock agent outputs
- [x] Readiness score calculation
- [x] Report export (Markdown)

### Phase 2: Real Azure Integration
- [ ] Azure OpenAI API integration
- [ ] Real GitHub App OAuth flow
- [ ] Azure Cosmos DB storage
- [ ] Azure Blob Storage for reports
- [ ] Application Insights telemetry

### Phase 3: Enterprise Features
- [ ] Multi-team workspaces
- [ ] Report history & comparison
- [ ] Webhook integrations
- [ ] API rate limiting
- [ ] Advanced analytics

### Phase 4: Scale & Compliance
- [ ] SOC 2 compliance
- [ ] HIPAA/GDPR support
- [ ] Multi-region deployment
- [ ] Advanced audit logging

---

## 🤝 Contributing

### Code Style
- **Frontend**: Prettier + ESLint
- **Backend**: Black + isort

### Branch Strategy
- `main` → Production
- `develop` → Staging
- `feature/*` → Feature branches

### Pull Request Process
1. Fork the repo
2. Create feature branch (`feature/my-feature`)
3. Commit changes
4. Push to branch
5. Open Pull Request
6. Address review feedback
7. Merge when approved

---

## 📄 License

MIT License — See LICENSE file for details.

---

## 🙏 Acknowledgments

Built with ❤️ using:
- **React** + **TypeScript** + **Tailwind CSS** + **Framer Motion**
- **FastAPI** + **Pydantic** + **Python**
- **Azure OpenAI** + **Azure Services**
- **GitHub API**

---

## 📞 Support

- 📧 Email: support@shipmate.ai
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions
- 📖 Docs: [Full Documentation](https://docs.shipmate.ai)

---

**ShipMate AI** — Where Code Meets Intelligence ⚡

*Powered by Azure AI Foundry + Azure OpenAI*
│  │  Upload  │  │  cards     │  └──────────────────────────┘ │
│  └──────────┘  └────────────┘  ┌──────────────────────────┐ │
│                                │  ReadinessScore (ring +  │ │
│                                │  6-dim bar breakdown)    │ │
│                                └──────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP (Axios)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Python)                        │
│                                                             │
│  POST /api/analyze          POST /api/upload-repo           │
│  GET  /api/sample           GET  /health                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              analyzer.py (Orchestrator)             │   │
│  │                                                     │   │
│  │  planner → repo_analyst → test_generator            │   │
│  │  → security_guard → delivery_manager                │   │
│  │                                                     │   │
│  │  calculate_readiness_score()                        │   │
│  │  generate_markdown_report()                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────┐   ┌───────────────────────────────┐  │
│  │  repo_service.py │   │      models/schemas.py        │  │
│  │  ZIP extraction  │   │  Pydantic type-safe contracts  │  │
│  │  stack detection │   │  for every agent output       │  │
│  └──────────────────┘   └───────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.x | UI framework |
| TypeScript | ~6.0 | Type safety |
| Vite | 8.x | Build tool & dev server |
| Tailwind CSS | 4.x | Utility-first styling |
| Framer Motion | 12.x | Animations & transitions |
| Lucide React | 1.x | Icon library |
| Axios | 1.x | HTTP client |
| clsx + tailwind-merge | latest | Conditional class merging |

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.10+ | Runtime |
| FastAPI | ≥0.111.0 | REST API framework |
| Pydantic v2 | ≥2.0.0 | Data validation & schemas |
| Uvicorn | ≥0.29.0 | ASGI server |
| python-multipart | ≥0.0.6 | File upload handling |
| aiofiles | ≥23.1.0 | Async file I/O |
| httpx | ≥0.24.0 | Async HTTP client (for future LLM calls) |
| python-dotenv | ≥1.0.0 | Environment variable management |

---

## 📁 Project Structure

```
shipmate-ai/
├── README.md
│
├── frontend/                          # React + TypeScript + Vite
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── src/
│       ├── main.tsx                   # React entry point
│       ├── App.tsx                    # Root component & state management
│       ├── App.css                    # Global component styles
│       ├── index.css                  # CSS custom properties & resets
│       ├── types/
│       │   └── index.ts               # TypeScript interfaces (mirrors Pydantic schemas)
│       ├── lib/
│       │   └── api.ts                 # Axios API client (analyzeFeature, uploadRepo, getSample)
│       └── components/
│           ├── Sidebar.tsx            # Navigation sidebar with repo upload
│           ├── AgentSwarm.tsx         # Animated agent status cards
│           ├── ReadinessScore.tsx     # SVG ring + 6-dimension bar breakdown
│           ├── ReportTabs.tsx         # Tab navigation + Markdown export
│           └── tabs/
│               ├── PlanTab.tsx        # Implementation plan: tasks + risks
│               ├── RepoTab.tsx        # Repo impact: files + APIs + deps
│               ├── TestsTab.tsx       # Test suite: unit + API + edge cases
│               ├── SecurityTab.tsx    # Security findings: CVEs + secrets
│               └── ReleaseTab.tsx     # Sprint plan + CI/CD + next actions
│
└── backend/                           # Python FastAPI
    ├── requirements.txt
    ├── verify.py                      # Startup verification script
    └── app/
        ├── __init__.py
        ├── main.py                    # FastAPI app + CORS + routes
        ├── models/
        │   └── schemas.py             # Pydantic models for all I/O
        ├── services/
        │   ├── analyzer.py            # Agent orchestrator + scoring + report gen
        │   └── repo_service.py        # ZIP extraction + tech stack detection
        └── agents/
            ├── __init__.py
            ├── planner.py             # 🧠 Planner Agent
            ├── repo_analyst.py        # 🔍 Repo Analyst Agent
            ├── test_generator.py      # 🧪 Test Generator Agent
            ├── security_guard.py      # 🛡️ Security Guard Agent
            └── delivery_manager.py   # 🚢 Delivery Manager Agent
```

---

## 🤖 Agent System — What's Built

### 🧠 Planner Agent (`agents/planner.py`)

**Input:** Feature request text + optional repo context string  
**Keyword detection:** Scans for auth, analytics, API, database keywords to adjust outputs  
**Output schema (`PlannerOutput`):**

```python
frontend_tasks: List[Task]         # e.g., FE-001..FE-004
backend_tasks: List[Task]          # e.g., BE-001..BE-004
database_changes: List[Task]       # e.g., DB-001..DB-002
test_requirements: List[Task]      # e.g., TEST-001..TEST-002
deployment_risks: List[str]        # Color-coded risk flags
total_story_points: int            # e.g., 34
recommended_sprint_count: int      # e.g., 2
```

Each `Task` has: `id`, `title`, `type`, `priority (high/medium/low)`, `effort (S/M/L/XL)`, `description`

---

### 🔍 Repo Analyst Agent (`agents/repo_analyst.py`)

**Input:** Feature request + repo context  
**Output schema (`RepoAnalystOutput`):**

```python
files_to_change: List[RepoFile]    # path, risk_level, change_type, reason
affected_apis: List[str]           # Endpoint paths impacted
risky_dependencies: List[str]      # Libraries that could break
patterns_to_follow: List[str]      # Coding conventions to maintain
impact_score: int                  # 0-100 codebase impact confidence
architecture_notes: str            # Architectural guidance note
```

---

### 🧪 Test Generator Agent (`agents/test_generator.py`)

**Input:** Feature request + repo context  
**Output schema (`TestGeneratorOutput`):**

```python
unit_tests: List[TestCase]         # Function-level tests with assertions
api_tests: List[TestCase]          # Endpoint integration tests
edge_cases: List[TestCase]         # Boundary & failure scenarios
regression_checklist: List[str]    # Manual regression items
total_coverage_estimate: int       # Estimated % coverage
```

Each `TestCase` has: `id`, `name`, `type (unit/integration/e2e/security)`, `priority`, `description`, `assertions: List[str]`

---

### 🛡️ Security Guard Agent (`agents/security_guard.py`)

**Input:** Feature request + repo context  
**Output schema (`SecurityGuardOutput`):**

```python
risks: List[SecurityRisk]          # Structured vulnerability findings
prompt_injection_risks: List[str]  # LLM-specific attack vectors
exposed_secrets: List[str]         # Leaked credentials / API keys
unsafe_tool_calls: List[str]       # eval(), dynamic imports, open redirects
auth_bypass_risks: List[str]       # Access control weaknesses
dependency_warnings: List[str]     # CVE-flagged npm/pip packages
overall_security_score: int        # 0-100 security posture score
```

Each `SecurityRisk` has: `id`, `title`, `severity (critical/high/medium/low)`, `category`, `description`, `recommendation`, `cve_reference`

---

### 🚢 Delivery Manager Agent (`agents/delivery_manager.py`)

**Input:** Feature request + repo context  
**Output schema (`DeliveryManagerOutput`):**

```python
sprint_plan: List[SprintTask]      # Day-by-day task assignments
standup_summary: str               # Done / Doing / Blocked standup
pr_review_summary: str             # Code review feedback with line refs
cicd_recommendations: List[str]    # GitHub Actions / pipeline advice
release_readiness_score: int       # 0-100 release confidence
next_actions: List[str]            # Priority-tagged next steps
estimated_release_date: str        # Estimate with caveats
```

---

## 🔌 API Reference

### `POST /api/analyze`

Run the full 5-agent production analysis swarm.

**Request Body:**
```json
{
  "feature_request": "Add login with role-based access and dashboard analytics.",
  "repo_context": "Optional: stringified repo summary from /api/upload-repo"
}
```

**Response:** `AnalyzeResponse`
```json
{
  "readiness_score": 72,
  "agents": {
    "planner": { ... },
    "repo_analyst": { ... },
    "test_generator": { ... },
    "security_guard": { ... },
    "delivery_manager": { ... }
  },
  "summary": "ShipMate AI analyzed your feature...",
  "markdown_report": "# 🚀 ShipMate AI — Production Readiness Report\n...",
  "score_breakdown": {
    "task_clarity": 30,
    "test_coverage": 75,
    "security_score": 61,
    "deployment_confidence": 50,
    "repo_confidence": 70,
    "cicd_readiness": 40
  }
}
```

**Validation:** Request must have `feature_request` ≥ 10 characters.

---

### `POST /api/upload-repo`

Upload a ZIP file of a repository for context injection.

**Constraints:** ZIP only, max 50 MB  
**Returns:** `RepoSummary`
```json
{
  "file_tree": ["src/index.ts", "package.json", ...],
  "file_count": 47,
  "detected_stack": ["TypeScript", "React", "PostgreSQL"],
  "readme_content": "...",
  "package_json": { ... },
  "requirements_txt": "...",
  "key_files": { "src/auth/middleware.ts": "..." },
  "repo_context": "Full stringified context for agents"
}
```

---

### `GET /api/sample`

Returns a built-in e-commerce TypeScript project as demo repo context.

### `GET /health`

Returns agent roster and service status.

### `GET /docs`

Interactive Swagger UI auto-generated by FastAPI.

---

## 📐 Data Models & Schemas

All models are defined in `backend/app/models/schemas.py` using **Pydantic v2** and mirrored as TypeScript interfaces in `frontend/src/types/index.ts`.

```
AnalyzeRequest
  └── feature_request: str
  └── repo_context?: str

AnalyzeResponse
  └── readiness_score: int
  └── agents: AgentResults
  │     ├── planner: PlannerOutput
  │     │     └── frontend_tasks, backend_tasks, database_changes,
  │     │         test_requirements, deployment_risks,
  │     │         total_story_points, recommended_sprint_count
  │     ├── repo_analyst: RepoAnalystOutput
  │     │     └── files_to_change (RepoFile[]), affected_apis,
  │     │         risky_dependencies, patterns_to_follow,
  │     │         impact_score, architecture_notes
  │     ├── test_generator: TestGeneratorOutput
  │     │     └── unit_tests, api_tests, edge_cases (TestCase[]),
  │     │         regression_checklist, total_coverage_estimate
  │     ├── security_guard: SecurityGuardOutput
  │     │     └── risks (SecurityRisk[]), prompt_injection_risks,
  │     │         exposed_secrets, unsafe_tool_calls,
  │     │         auth_bypass_risks, dependency_warnings,
  │     │         overall_security_score
  │     └── delivery_manager: DeliveryManagerOutput
  │           └── sprint_plan (SprintTask[]), standup_summary,
  │               pr_review_summary, cicd_recommendations,
  │               release_readiness_score, next_actions,
  │               estimated_release_date
  └── summary: str
  └── markdown_report: str
  └── score_breakdown: Dict[str, int]

RepoSummary
  └── file_tree, file_count, detected_stack,
      readme_content, package_json, requirements_txt,
      key_files, repo_context
```

---

## 📊 Readiness Score Engine (`analyzer.py`)

The scoring engine (`calculate_readiness_score`) deducts from 100 across 6 weighted dimensions:

| Dimension | Max Deduction | Logic |
|-----------|--------------|-------|
| **Task Clarity** | –15 pts | Deducts if total tasks < 3 (–15) or < 6 (–8) |
| **Test Coverage** | –20 pts | Deducts based on `total_coverage_estimate`: <50% → –20, <70% → –10, <80% → –5 |
| **Security Risk** | –20 pts | `critical × 8 + high × 4`, capped at 20 |
| **Deployment Confidence** | –15 pts | Based on count of `deployment_risks`: >5 → –15, >3 → –8, else → –3 |
| **Repo Impact** | –10 pts | `high_risk_files × 2`, capped at 10 |
| **CI/CD Readiness** | –10 pts | `cicd_recommendations × 2`, capped at 10 |

**Breakdown fields exposed to frontend:**

```python
task_clarity        → 30 - (task_deduction × 2)        # Normalized 0-30
test_coverage       → min(100, coverage_estimate)       # Raw % estimate
security_score      → overall_security_score            # Agent's own score
deployment_confidence → max(0, 100 - dep_risk_count×10)
repo_confidence     → repo_analyst.impact_score
cicd_readiness      → max(0, 100 - cicd_count×15)
```

---

## 🎨 Frontend Components

### `AgentSwarm.tsx`
- Renders 5 animated agent status cards
- Shows `idle → running → complete` state with Framer Motion transitions
- Each card: icon, name, description, status badge + spinner

### `ReadinessScore.tsx`
- **SVG ring** (`ScoreRing`): Animated `strokeDashoffset` from 0 → score%, with glow `drop-shadow` color-coded (green ≥80, amber ≥60, red <60)
- **6-dimension bar breakdown**: Animated `width` bars with color per dimension
- Score label: `Production Ready / Needs Work / Not Ready`

### `ReportTabs.tsx`
- 5-tab navigator: Plan | Repo | Tests | Security | Release
- **Export button**: Triggers a browser download of the `markdown_report` string as a `.md` file

### `Sidebar.tsx`
- Feature request textarea + "Use Sample" helper
- Repo context: "Load Sample Repo" button + ZIP file upload (drag-and-drop or click)
- "Run Production Swarm" CTA button

### `tabs/PlanTab.tsx`
- Task cards by category (Frontend / Backend / Database)
- Priority badges, effort size tags, story points
- Deployment risk list with color-coded indicators

### `tabs/RepoTab.tsx`
- File impact table with risk-level color coding
- Affected APIs list
- Risky dependencies + patterns to follow cards

### `tabs/TestsTab.tsx`
- Unit tests + API tests with assertion checklists
- Edge case cards
- Regression checklist
- Coverage estimate progress bar

### `tabs/SecurityTab.tsx`
- Vulnerability table with severity badges (critical/high/medium/low)
- CVE reference links
- Exposed secrets, unsafe calls, auth bypass risks, dependency CVEs

### `tabs/ReleaseTab.tsx`
- Sprint plan timeline (Sprint 1–2 with day-level breakdown)
- Standup summary (Done / Doing / Blocked)
- PR review feedback with approval/revision/blocking sections
- CI/CD recommendation list
- Priority-tagged next actions

---

## ⚡ Quick Start

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

- Frontend: http://localhost:5173

---

## 🎯 Demo Flow

1. Open http://localhost:5173
2. Click **"Use Sample"** to load the demo feature request
3. Click **"Load Sample Repo"** to inject the e-commerce demo repo context
4. Click **"Run Production Swarm"**
5. Watch 5 agents animate through `idle → running → complete`
6. View the **Production Readiness Score** ring and 6-dimension breakdown
7. Explore all 5 report tabs (Plan, Repo, Tests, Security, Release)
8. Click **"Export Report"** to download the full Markdown report

---

## 🔮 What We Can Build Next

> Organized by impact level and implementation effort.

---

### 🔴 High Impact — Core Intelligence Upgrades

#### 1. Real LLM Integration
All agents currently return high-quality deterministic mock data. The architecture is already wired to swap in real LLM calls.

**How:** Replace the body of each `run_*_agent()` function with an OpenAI / Gemini / Anthropic API call. The `httpx` client is already in `requirements.txt`.

```python
# Current (mock)
def run_planner_agent(feature_request, repo_context):
    return PlannerOutput(frontend_tasks=[...])

# Future (LLM-backed)
async def run_planner_agent(feature_request, repo_context):
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": PLANNER_PROMPT.format(...)}],
        response_format={"type": "json_object"}
    )
    return PlannerOutput(**json.loads(response.choices[0].message.content))
```

#### 2. Parallel Agent Execution
Agents currently run sequentially. For LLM-backed agents, parallel execution cuts latency by ~5×.

```python
# In analyzer.py
async def run_full_analysis_parallel(request):
    results = await asyncio.gather(
        run_planner_agent(feature_request, repo_context),
        run_repo_analyst_agent(feature_request, repo_context),
        run_test_generator_agent(feature_request, repo_context),
        run_security_guard_agent(feature_request, repo_context),
        run_delivery_manager_agent(feature_request, repo_context),
    )
```

#### 3. Real-Time Streaming (`SSE` or `WebSocket`)
Replace the current fire-and-wait pattern with streaming agent updates so the UI shows each agent completing live.

**Endpoint:** `GET /api/analyze/stream` using FastAPI `StreamingResponse` + Server-Sent Events.

---

### 🟠 Medium Impact — Feature Additions

#### 4. GitHub / GitLab Repository Integration
Instead of ZIP upload, connect directly to GitHub via OAuth + GitHub API to pull live repo structure.

- Auth: GitHub OAuth2 (PKCE flow)
- API: `GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1`
- Read key files: `GET /repos/{owner}/{repo}/contents/{path}`

#### 5. Persistent Analysis History
Add a database (SQLite for local, PostgreSQL for production) to store past analyses.

```
New tables: analyses, agent_outputs, users (optional)
New endpoints:
  GET  /api/history          → List past analyses
  GET  /api/history/{id}     → Retrieve a specific analysis
  DELETE /api/history/{id}   → Delete an analysis
```

#### 6. Shareable Report Links
Generate a unique token per analysis and allow sharing via URL (`/report/{token}`). The report renders server-side or as a read-only React view.

#### 7. Agent Configuration Panel
Let users tune agent behaviour from the UI:
- Toggle agents on/off (run only Security + Tests)
- Set LLM model per agent (GPT-4o for Planner, Gemini for Security, etc.)
- Adjust scoring weights per dimension

#### 8. Slack / Teams / Jira Integration
After analysis completes, push outputs to team tools:
- **Slack:** Post readiness score + critical security findings to a channel
- **Jira:** Auto-create tickets from Planner tasks with story points + labels
- **Linear:** Create issues in a project from task breakdown

---

### 🟡 Lower Effort — Polish & Developer Experience

#### 9. Dark / Light Mode Toggle
The design system already uses CSS custom properties. Add a `data-theme` attribute toggle and define a light-mode token set in `index.css`.

#### 10. Analysis Comparison View
Allow users to run two analyses side-by-side (e.g., before vs. after a refactor) and see score deltas per dimension.

#### 11. Prompt Template Library
Pre-built feature request templates (Auth, Payments, Real-Time, File Upload, etc.) that users can select from a dropdown to pre-fill the textarea.

#### 12. Dockerization
```dockerfile
# Dockerfile.backend / Dockerfile.frontend
# docker-compose.yml with hot-reload volumes for dev
```
Makes the project one-command deployable for demos.

#### 13. Deployable to Cloud
- **Frontend:** Vercel / Netlify (Vite build → static)
- **Backend:** Railway / Render / Fly.io (Docker + Uvicorn)
- **Env vars:** `OPENAI_API_KEY`, `DATABASE_URL`, `REDIS_URL`

#### 14. Unit Tests for Backend
Add `pytest` + `pytest-asyncio` test suite for:
- `calculate_readiness_score()` edge cases
- Pydantic schema validation
- `process_repo_zip()` with fixture ZIP files
- Each agent function with mocked LLM responses

#### 15. Repo Context Improvement
`repo_service.py` already extracts file trees and key files from ZIP. Enhancements:
- Parse **function signatures** from Python/TypeScript files using AST
- Detect **test frameworks** (pytest, Jest, Vitest)
- Detect **CI/CD config** (`.github/workflows`, `Dockerfile`, `Makefile`)
- Compute **file complexity scores**

---

### 🔵 Advanced / Stretch Goals

#### 16. Agent-to-Agent Communication (True Agentic Loop)
Let agents share findings with each other. For example:
- Security Guard findings → fed into Planner (auto-adds security tasks)
- Repo Analyst file list → fed into Test Generator (tests target real files)
- Delivery Manager reads Test Generator coverage → adjusts sprint estimate

#### 17. Code Diff Generation
Have the Planner Agent produce actual code snippets / diffs for the highest-priority tasks using LLM code generation, displayed in a diff viewer component.

#### 18. Custom Agent Builder
A UI where users can define their own agent (name, prompt template, output schema) and add it to the swarm. Store agent definitions in the database.

#### 19. Multi-Repo Analysis
Analyze multiple microservices together to understand cross-service impact of a feature (e.g., how an auth change in `auth-service` affects `api-gateway`, `user-service`, `billing-service`).

#### 20. Voice Input Mode
Use the Web Speech API to let users describe the feature request verbally instead of typing.

---

## 🏆 Hackathon Notes

- **No real LLM calls required** — agents return high-quality simulated outputs that demonstrate the full workflow
- **LLM-ready** — every agent is a single function, swap in any LLM provider in one place
- **Type-safe end-to-end** — Pydantic schemas on backend, TypeScript interfaces on frontend, identical shape
- **Report export** — generates a complete shareable Markdown document
- **Dark mode command center UI** — built to impress

---

*ShipMate AI — Reinventing how software teams ship.*
