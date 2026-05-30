from app.models.schemas import SecurityGuardOutput, SecurityRisk
from typing import List


def run_security_guard_agent(feature_request: str, repo_context: str = "") -> SecurityGuardOutput:
    """
    Security Guard Agent: Identifies security risks, vulnerabilities, and compliance issues.
    """

    risks: List[SecurityRisk] = [
        SecurityRisk(
            id="SEC-001",
            title="JWT Secret Not Rotated — Hardcoded in Source",
            severity="critical",
            category="Secrets Management",
            description="The JWT signing secret appears to be stored in the .env file committed to version control. If the repo is public or the secret leaks, all existing tokens can be forged.",
            recommendation="Move JWT secret to a secrets manager (AWS Secrets Manager, HashiCorp Vault). Implement automatic rotation every 90 days. Add pre-commit hook to block secret commits.",
            cve_reference="CWE-798"
        ),
        SecurityRisk(
            id="SEC-002",
            title="Missing Rate Limiting on Auth Endpoints",
            severity="high",
            category="Brute Force Protection",
            description="The /api/auth/login and /api/auth/reset-password endpoints have no rate limiting or lockout mechanism. This enables brute-force attacks against user accounts.",
            recommendation="Implement sliding window rate limiting (5 attempts per 15 minutes per IP+email). Use Redis for distributed rate limit state. Return 429 with Retry-After header.",
            cve_reference="CWE-307"
        ),
        SecurityRisk(
            id="SEC-003",
            title="IDOR Risk on Analytics User Data Endpoint",
            severity="high",
            category="Authorization",
            description="GET /api/analytics/users/:id does not verify that the requesting user has permission to view data for the specified userId. Attackers can enumerate user analytics by iterating IDs.",
            recommendation="Add resource-level ownership check: verify requesting user's role is admin OR userId matches their own ID. Log all cross-user data access attempts.",
            cve_reference="CWE-639"
        ),
        SecurityRisk(
            id="SEC-004",
            title="OAuth State Parameter Not Validated",
            severity="medium",
            category="OAuth Security",
            description="The OAuth2 callback handler does not validate the state parameter, making the application vulnerable to CSRF attacks during the OAuth flow.",
            recommendation="Generate cryptographically random state parameter, store in session, and validate on callback. Reject requests with missing or mismatched state.",
            cve_reference="CWE-352"
        ),
        SecurityRisk(
            id="SEC-005",
            title="Sensitive Data in Analytics Event Payload",
            severity="medium",
            category="Data Privacy",
            description="Analytics events may capture PII (email addresses, IP addresses, user behavior) without explicit consent mechanism or data retention policy.",
            recommendation="Implement data anonymization for analytics (hash user IDs, truncate IPs). Add GDPR-compliant consent banner. Define and enforce data retention TTL.",
            cve_reference="GDPR Art. 25"
        ),
    ]

    prompt_injection_risks = [
        "Feature request field accepts freeform text — sanitize before passing to any LLM pipeline",
        "User display names rendered without HTML escaping in dashboard — XSS vector",
        "Analytics event descriptions injected into admin dashboard without sanitization",
    ]

    exposed_secrets = [
        "⚠️  .env file detected in git history — JWT_SECRET, DATABASE_URL may be exposed",
        "⚠️  API keys found in src/config/constants.ts — move to environment variables",
        "⚠️  Test database credentials hardcoded in test/setup.ts",
    ]

    unsafe_tool_calls = [
        "eval() usage detected in src/utils/queryBuilder.ts — potential code injection",
        "Dynamic require() with user input in src/plugins/loader.ts",
        "Unvalidated redirect URL in OAuth callback — open redirect vulnerability",
    ]

    auth_bypass_risks = [
        "Role check middleware can be bypassed by sending role claim directly in request body",
        "Admin panel accessible via direct URL navigation if frontend-only route guard used",
        "Token revocation list not checked on every request — revoked tokens valid until expiry",
    ]

    dependency_warnings = [
        "jsonwebtoken@8.5.1 — CVE-2022-23529 (Algorithm confusion attack) — UPGRADE IMMEDIATELY",
        "passport@0.5.3 — Deprecated, CVE-2022-25896 (session fixation) — migrate to 0.7.x",
        "axios@0.21.1 — CVE-2021-3749 (SSRF) — upgrade to 1.6.x",
        "mongoose@5.13.x — EOL, multiple CVEs — upgrade to 8.x",
    ]

    return SecurityGuardOutput(
        risks=risks,
        prompt_injection_risks=prompt_injection_risks,
        exposed_secrets=exposed_secrets,
        unsafe_tool_calls=unsafe_tool_calls,
        auth_bypass_risks=auth_bypass_risks,
        dependency_warnings=dependency_warnings,
        overall_security_score=61
    )
