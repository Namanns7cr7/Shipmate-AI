from app.models.schemas import (
    PlannerOutput, Task
)
from typing import List


def run_planner_agent(feature_request: str, repo_context: str = "") -> PlannerOutput:
    """
    Planner Agent: Converts a feature request into structured engineering tasks.
    In production this calls an LLM. For MVP we return high-quality mock data.
    """
    req_lower = feature_request.lower()

    # Detect key domains from the feature request
    has_auth = any(w in req_lower for w in ["login", "auth", "role", "access", "permission", "jwt", "oauth"])
    has_analytics = any(w in req_lower for w in ["analytics", "dashboard", "chart", "report", "metrics", "stats"])
    has_api = any(w in req_lower for w in ["api", "endpoint", "rest", "graphql", "webhook"])

    frontend_tasks: List[Task] = [
        Task(
            id="FE-001",
            title="Build Login Page with OAuth/JWT support",
            type="frontend",
            priority="high",
            effort="M",
            description="Create a responsive login page with email/password form, social OAuth buttons, and JWT token storage in httpOnly cookies."
        ),
        Task(
            id="FE-002",
            title="Implement Role-Based Route Guards",
            type="frontend",
            priority="high",
            effort="M",
            description="Add React Router guards that check user roles (admin, editor, viewer) before rendering protected routes. Redirect unauthorized users."
        ),
        Task(
            id="FE-003",
            title="Build Analytics Dashboard UI",
            type="frontend",
            priority="high",
            effort="L",
            description="Create a dashboard with KPI cards, line charts for trends, pie charts for distribution, and filterable data tables using Recharts or Chart.js."
        ),
        Task(
            id="FE-004",
            title="Implement User Management Panel",
            type="frontend",
            priority="medium",
            effort="M",
            description="Admin panel for inviting users, assigning roles, deactivating accounts, and viewing audit logs."
        ),
    ]

    backend_tasks: List[Task] = [
        Task(
            id="BE-001",
            title="Implement JWT Authentication Middleware",
            type="backend",
            priority="high",
            effort="M",
            description="Create FastAPI/Express middleware for JWT verification, refresh token rotation, and secure session management with Redis."
        ),
        Task(
            id="BE-002",
            title="Build Role-Based Access Control (RBAC) System",
            type="backend",
            priority="high",
            effort="L",
            description="Design permission matrices, role inheritance, resource-level access control, and audit logging for all privileged operations."
        ),
        Task(
            id="BE-003",
            title="Create Analytics Data Aggregation Service",
            type="backend",
            priority="high",
            effort="L",
            description="Build background job that aggregates usage metrics, computes KPIs, caches results in Redis, and exposes REST/GraphQL endpoints."
        ),
        Task(
            id="BE-004",
            title="Implement OAuth2 Provider Integration",
            type="backend",
            priority="medium",
            effort="M",
            description="Integrate Google, GitHub OAuth2 flows with PKCE, state validation, and account linking for existing users."
        ),
    ]

    database_changes: List[Task] = [
        Task(
            id="DB-001",
            title="Add Users & Roles Schema",
            type="database",
            priority="high",
            effort="M",
            description="Create users, roles, user_roles, permissions, and audit_log tables with proper indexes, foreign keys, and row-level security."
        ),
        Task(
            id="DB-002",
            title="Create Analytics Events Table",
            type="database",
            priority="medium",
            effort="S",
            description="Add analytics_events table with partitioning by date, TTL policy, and materialized views for common aggregations."
        ),
    ]

    test_requirements: List[Task] = [
        Task(
            id="TEST-001",
            title="Auth Flow End-to-End Tests",
            type="test",
            priority="high",
            effort="M",
            description="Playwright/Cypress tests covering login, logout, token refresh, role switching, and unauthorized access scenarios."
        ),
        Task(
            id="TEST-002",
            title="RBAC Unit & Integration Tests",
            type="test",
            priority="high",
            effort="M",
            description="Pytest tests for all permission combinations, role inheritance, and resource access control edge cases."
        ),
    ]

    deployment_risks = [
        "🔴 Database migration required — coordinate zero-downtime migration strategy",
        "🟡 JWT secret rotation needed in all environments before go-live",
        "🟡 OAuth callback URLs must be allowlisted in all OAuth providers",
        "🟠 Redis cache dependency introduced — ensure cluster availability",
        "🟡 Analytics queries may cause read load spikes — consider read replicas",
    ]

    return PlannerOutput(
        frontend_tasks=frontend_tasks,
        backend_tasks=backend_tasks,
        database_changes=database_changes,
        test_requirements=test_requirements,
        deployment_risks=deployment_risks,
        total_story_points=34,
        recommended_sprint_count=2
    )
