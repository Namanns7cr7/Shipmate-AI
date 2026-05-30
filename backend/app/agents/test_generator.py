from app.models.schemas import TestGeneratorOutput, TestCase
from typing import List


def run_test_generator_agent(feature_request: str, repo_context: str = "") -> TestGeneratorOutput:
    """
    Test Generator Agent: Produces comprehensive test cases for the feature.
    """

    unit_tests: List[TestCase] = [
        TestCase(
            id="UT-001",
            name="test_jwt_token_generation",
            type="unit",
            priority="high",
            description="Verify JWT token contains correct claims, expiry, and is signed with the expected secret",
            assertions=[
                "Token payload contains userId, email, and role fields",
                "Token expiry is set to 15 minutes for access tokens",
                "Refresh token expiry is set to 7 days",
                "Invalid secret produces verification failure",
            ]
        ),
        TestCase(
            id="UT-002",
            name="test_rbac_permission_matrix",
            type="unit",
            priority="high",
            description="Unit test all role-permission combinations to prevent privilege escalation",
            assertions=[
                "Admin role has access to all resources",
                "Editor role cannot access user management endpoints",
                "Viewer role has read-only access",
                "Unauthenticated requests return 401",
                "Insufficient permissions return 403 not 404",
            ]
        ),
        TestCase(
            id="UT-003",
            name="test_analytics_aggregation",
            type="unit",
            priority="medium",
            description="Test analytics computation functions with various data inputs",
            assertions=[
                "Handles empty dataset without exception",
                "Correctly computes MAU, DAU, retention metrics",
                "Date range filtering works correctly",
                "Null values are excluded from averages",
            ]
        ),
    ]

    api_tests: List[TestCase] = [
        TestCase(
            id="API-001",
            name="test_login_endpoint",
            type="integration",
            priority="high",
            description="Integration test for POST /api/auth/login covering all success and failure paths",
            assertions=[
                "Valid credentials return 200 with access_token and refresh_token",
                "Invalid password returns 401 with error message",
                "Non-existent user returns 401 (not 404, to prevent user enumeration)",
                "Rate limiting kicks in after 5 failed attempts",
                "SQL injection in email field is rejected",
                "Response sets httpOnly cookie for refresh token",
            ]
        ),
        TestCase(
            id="API-002",
            name="test_protected_route_auth",
            type="integration",
            priority="high",
            description="Verify auth middleware correctly guards all protected endpoints",
            assertions=[
                "Request without token returns 401",
                "Request with expired token returns 401 with token_expired code",
                "Request with valid token returns 200",
                "Request with tampered token returns 401",
                "Admin-only endpoint rejects editor role with 403",
            ]
        ),
        TestCase(
            id="API-003",
            name="test_analytics_dashboard_endpoint",
            type="integration",
            priority="medium",
            description="Test GET /api/analytics/overview for correctness and performance",
            assertions=[
                "Returns 200 with expected data structure",
                "Response time under 500ms with cached data",
                "Date range parameters correctly filter results",
                "Viewer role can access but editor cannot see raw user data",
            ]
        ),
    ]

    edge_cases: List[TestCase] = [
        TestCase(
            id="EDGE-001",
            name="test_concurrent_login_sessions",
            type="integration",
            priority="medium",
            description="Test behavior when user logs in from multiple devices simultaneously",
            assertions=[
                "Each device receives a unique refresh token",
                "Revoking one session does not invalidate others",
                "Maximum session limit (configurable) is enforced",
            ]
        ),
        TestCase(
            id="EDGE-002",
            name="test_role_change_active_session",
            type="integration",
            priority="high",
            description="Verify role changes take effect without requiring re-login",
            assertions=[
                "Token refresh after role change returns new permissions",
                "Old token is invalidated immediately after role downgrade",
                "Cached permissions are invalidated on role change",
            ]
        ),
        TestCase(
            id="EDGE-003",
            name="test_analytics_high_load",
            type="integration",
            priority="low",
            description="Analytics aggregation under high concurrent request load",
            assertions=[
                "No data race conditions in aggregation",
                "Cache prevents thundering herd on cold start",
                "Graceful degradation when data store is slow",
            ]
        ),
    ]

    regression_checklist = [
        "✅ Existing user endpoints still return correct data structure",
        "✅ Password reset flow still works after auth middleware changes",
        "✅ Public routes (health check, swagger) remain accessible without token",
        "✅ Existing webhook integrations not broken by auth changes",
        "✅ Email notification service still functions correctly",
        "✅ File upload endpoints still accept multipart/form-data",
        "✅ Pagination on list endpoints unchanged",
        "✅ Database connection pooling not affected by new Redis dependency",
    ]

    return TestGeneratorOutput(
        unit_tests=unit_tests,
        api_tests=api_tests,
        edge_cases=edge_cases,
        regression_checklist=regression_checklist,
        total_coverage_estimate=76
    )
