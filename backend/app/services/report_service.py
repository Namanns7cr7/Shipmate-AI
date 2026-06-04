from typing import List

from ..schemas.agent_schemas import (
    PlanForgeOutput, GuardRailOutput, TestPilotOutput, Severity
)


class ReportService:

    @staticmethod
    def extract_blockers(plan_forge: PlanForgeOutput, guardrail: GuardRailOutput) -> List[str]:
        blockers: List[str] = []

        # Critical and high PlanForge blockers
        for b in plan_forge.blockers:
            if b.severity in ("critical", "high"):
                blockers.append(b.title)

        # Critical security findings
        for f in guardrail.findings:
            if f.severity in (Severity.CRITICAL, Severity.HIGH):
                blockers.append(f.title)

        # Exposed secrets
        for secret in guardrail.exposed_secrets[:3]:
            if secret not in blockers:
                blockers.append(secret)

        # Deduplicate while preserving order
        seen = set()
        result = []
        for b in blockers:
            if b not in seen:
                seen.add(b)
                result.append(b)

        return result[:10]

    @staticmethod
    def extract_next_actions(
        plan_forge: PlanForgeOutput,
        guardrail: GuardRailOutput,
        testpilot: TestPilotOutput,
    ) -> List[str]:
        actions: List[str] = []

        # Top PlanForge recommendation
        if plan_forge.next_best_action:
            actions.append(plan_forge.next_best_action)

        # Critical security recommendations
        for f in guardrail.findings:
            if f.severity == Severity.CRITICAL and f.recommendation:
                actions.append(f.recommendation[:120])

        # Test suggestions
        if testpilot.qa_readiness == "not_ready":
            actions.append("Set up a test framework and write smoke tests for all public endpoints.")
        elif testpilot.missing_coverage_areas:
            actions.append(f"Improve test coverage: {testpilot.missing_coverage_areas[0]}")

        # CORS
        if guardrail.cors_issues:
            actions.append("Restrict CORS origins — remove wildcard * from allowed origins.")

        # CI/CD
        if any("CI/CD" in b.title for b in plan_forge.blockers):
            actions.append("Configure GitHub Actions for automated testing and deployment.")

        seen = set()
        result = []
        for a in actions:
            if a not in seen:
                seen.add(a)
                result.append(a)

        return result[:8]
