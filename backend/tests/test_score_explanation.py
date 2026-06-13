"""Phase 3, Task 8 — score_explanation on ShipMateReport.

RED: tests fail until ScoringService.calculate() returns score_explanation.
GREEN: add explanation generation to ScoringService and wire into the report.
"""
import pytest
from app.services.scoring_service import ScoringService
from app.schemas.agent_schemas import (
    RepoLensOutput, PlanForgeOutput, GuardRailOutput, TestPilotOutput,
    ExistingTests, ArchitectureRisk,
)


def _base_repo(repo_score=100, has_ci=True, has_tests=True, has_docker=True):
    return RepoLensOutput(
        tech_stack=[], primary_language="Python", architecture_pattern="fullstack",
        key_modules=[], entry_points=[], config_files=[],
        has_ci_cd=has_ci, has_dockerfile=has_docker, has_tests=has_tests,
        architecture_risks=[], dependency_summary={},
        file_count=50, repo_score=repo_score,
    )


def _base_plan(delivery_score=100):
    return PlanForgeOutput(
        milestones=[], blockers=[],
        dependencies=[], next_best_action="x", estimated_effort="1d",
        delivery_score=delivery_score,
    )


def _base_guard(security_score=100):
    return GuardRailOutput(
        findings=[], exposed_secrets=[], cors_issues=[],
        auth_risks=[], dependency_vulnerabilities=[],
        security_score=security_score,
    )


def _base_test(test_score=100):
    return TestPilotOutput(
        existing_tests=ExistingTests(count=5, coverage_estimate=60, frameworks=["pytest"], test_files=[]),
        missing_coverage_areas=[], suggested_tests=[],
        qa_readiness="ready", test_score=test_score,
    )


class TestScoreExplanation:
    def test_explanation_in_calculate_result(self):
        result = ScoringService.calculate(
            _base_repo(), _base_plan(), _base_guard(), _base_test()
        )
        assert "score_explanation" in result

    def test_perfect_score_has_empty_or_minimal_explanation(self):
        result = ScoringService.calculate(
            _base_repo(100), _base_plan(100), _base_guard(100), _base_test(100)
        )
        # When everything is 100, there's nothing to explain
        assert isinstance(result["score_explanation"], list)

    def test_low_security_score_explained(self):
        result = ScoringService.calculate(
            _base_repo(), _base_plan(), _base_guard(security_score=40), _base_test()
        )
        expl = result["score_explanation"]
        assert any("security" in e.lower() for e in expl), (
            f"Expected 'security' in explanation, got: {expl}"
        )

    def test_low_test_score_explained(self):
        result = ScoringService.calculate(
            _base_repo(), _base_plan(), _base_guard(), _base_test(test_score=30)
        )
        expl = result["score_explanation"]
        assert any("test" in e.lower() for e in expl), (
            f"Expected 'test' in explanation, got: {expl}"
        )

    def test_low_repo_score_explained(self):
        result = ScoringService.calculate(
            _base_repo(repo_score=50), _base_plan(), _base_guard(), _base_test()
        )
        expl = result["score_explanation"]
        assert any("repo" in e.lower() for e in expl), (
            f"Expected 'repo' in explanation, got: {expl}"
        )

    def test_explanation_max_6_items(self):
        result = ScoringService.calculate(
            _base_repo(30), _base_plan(30), _base_guard(30), _base_test(30)
        )
        assert len(result["score_explanation"]) <= 6

    def test_each_explanation_under_80_chars(self):
        result = ScoringService.calculate(
            _base_repo(50), _base_plan(50), _base_guard(50), _base_test(50)
        )
        for e in result["score_explanation"]:
            assert len(e) <= 80, f"Explanation too long ({len(e)} chars): {e!r}"

    def test_score_explanation_in_shipmate_report(self):
        """score_explanation must flow through to ShipMateReport."""
        from app.schemas.agent_schemas import ShipMateReport, RepoInfo, AgentOutputs, ScoreBreakdown, ShipRecommendation
        report = ShipMateReport(
            repo=RepoInfo(owner="o", name="r", full_name="o/r", branch="main", html_url=""),
            readiness_score=70,
            ship_recommendation=ShipRecommendation.NEEDS_REVIEW,
            score_breakdown=ScoreBreakdown(repo_score=70, delivery_score=70, security_score=70, test_score=70),
            agents=AgentOutputs(
                repo_lens=_base_repo(), plan_forge=_base_plan(), guardrail=_base_guard(), testpilot=_base_test(),
            ),
            key_blockers=[], next_actions=[], generated_at="2026-01-01T00:00:00Z",
            score_explanation=["-20 security_score: exposed secrets detected"],
        )
        assert report.score_explanation == ["-20 security_score: exposed secrets detected"]
