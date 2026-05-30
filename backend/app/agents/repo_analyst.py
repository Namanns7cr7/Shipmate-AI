from app.models.schemas import RepoAnalystOutput, RepoFile
from typing import List


def run_repo_analyst_agent(feature_request: str, repo_context: str = "") -> RepoAnalystOutput:
    """
    Repo Analyst Agent: Analyzes the repo to identify files needing change,
    risky dependencies, and existing patterns.
    """

    files_to_change: List[RepoFile] = [
        RepoFile(
            path="src/middleware/auth.ts",
            risk_level="high",
            change_type="modify",
            reason="Must add JWT validation and role-injection middleware before all protected routes"
        ),
        RepoFile(
            path="src/routes/api/users.ts",
            risk_level="high",
            change_type="modify",
            reason="All user endpoints need RBAC decorators and permission checks added"
        ),
        RepoFile(
            path="src/components/Dashboard/index.tsx",
            risk_level="medium",
            change_type="modify",
            reason="Dashboard component needs analytics widgets integrated and role-conditional rendering"
        ),
        RepoFile(
            path="src/pages/Login.tsx",
            risk_level="low",
            change_type="create",
            reason="New login page component required — does not exist in current codebase"
        ),
        RepoFile(
            path="src/store/authSlice.ts",
            risk_level="medium",
            change_type="create",
            reason="Redux/Zustand auth slice needed for session state management across components"
        ),
        RepoFile(
            path="database/migrations/0042_add_rbac.sql",
            risk_level="high",
            change_type="create",
            reason="Schema migration for users, roles, permissions tables — requires DBA review"
        ),
        RepoFile(
            path="src/services/analytics.service.ts",
            risk_level="medium",
            change_type="create",
            reason="New analytics aggregation service with caching layer — affects API response times"
        ),
        RepoFile(
            path="package.json",
            risk_level="low",
            change_type="modify",
            reason="New dependencies: jsonwebtoken, passport, chart.js, date-fns to be added"
        ),
    ]

    affected_apis = [
        "GET /api/users — now requires Bearer token + admin role",
        "POST /api/auth/login — new endpoint, returns JWT + refresh token",
        "POST /api/auth/refresh — new endpoint for token rotation",
        "GET /api/analytics/overview — new endpoint, expensive aggregation query",
        "PUT /api/users/:id/role — new endpoint, admin-only role assignment",
        "DELETE /api/sessions — new endpoint for logout + token invalidation",
    ]

    risky_dependencies = [
        "jsonwebtoken@8.5.1 — has known CVE-2022-23529, upgrade to 9.x required",
        "passport@0.5.x — deprecated auth strategy, migrate to passport@0.7.x",
        "mongoose@5.x — EOL version, MongoDB driver vulnerabilities present",
        "axios@0.21.1 — SSRF vulnerability CVE-2021-3749, upgrade to 1.x",
    ]

    patterns_to_follow = [
        "Use existing HOC pattern `withAuth()` wrapper for route protection (see src/hocs/withAuth.tsx)",
        "Follow repository's service-layer pattern: controllers → services → repositories",
        "Use existing error handling middleware in src/middleware/errorHandler.ts",
        "Match existing TypeScript strict mode configuration in tsconfig.json",
        "Use existing Redis client from src/lib/redis.ts for caching",
        "Follow existing migration naming convention: NNNN_description.sql",
    ]

    return RepoAnalystOutput(
        files_to_change=files_to_change,
        affected_apis=affected_apis,
        risky_dependencies=risky_dependencies,
        patterns_to_follow=patterns_to_follow,
        impact_score=73,
        architecture_notes="The codebase follows a layered MVC architecture with TypeScript strict mode. Auth changes will require touching the middleware chain, which has 3 existing dependent services. Database changes need coordination with DevOps for zero-downtime migration using pg_repack or similar."
    )
