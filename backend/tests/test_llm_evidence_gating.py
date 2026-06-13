"""Phase 2, Tasks 5 & 6 — LLM evidence gating + word-overlap deduplication.

Tests the merge helpers directly:
  - LLM item with a file field matching the file tree → confidence="medium", kept
  - LLM item with a fake/missing file field → confidence="low", dropped
  - 70% word-overlap with a heuristic title → duplicate, dropped
  - Same file+category as a heuristic finding → duplicate, dropped
  - Heuristic finding remains confidence="high" (unaffected by merge)
"""
import pytest
from app.services.llm_service import (
    _merge_guardrail_discovery,
    _merge_plan_discovery,
    _merge_testpilot_discovery,
    _word_overlap_dup,
)
from app.schemas.agent_schemas import (
    GuardRailOutput, PlanForgeOutput, TestPilotOutput,
    SecurityFinding, Milestone, Blocker, SuggestedTest,
    ExistingTests, Severity,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_guardrail_base():
    return GuardRailOutput(
        findings=[
            SecurityFinding(
                id="SEC-001", title="CORS wildcard", severity=Severity.HIGH,
                category="cors", description="d", recommendation="r",
                file="backend/app/main.py", confidence="high",
            )
        ],
        exposed_secrets=[], cors_issues=[], auth_risks=[],
        dependency_vulnerabilities=[], security_score=70,
    )


def _make_planforge_base():
    return PlanForgeOutput(
        milestones=[
            Milestone(
                title="Add CI pipeline", description="d", estimated_days=3,
                priority="high", category="ci_cd", confidence="high",
            )
        ],
        blockers=[],
        dependencies=[], next_best_action="x", estimated_effort="3d",
        delivery_score=60,
    )


def _make_testpilot_base():
    return TestPilotOutput(
        existing_tests=ExistingTests(count=0, coverage_estimate=0, frameworks=[], test_files=[]),
        missing_coverage_areas=[],
        suggested_tests=[
            SuggestedTest(
                name="test_auth_flows", type="integration", priority="high",
                description="d", confidence="high",
            )
        ],
        qa_readiness="partial",
        test_score=50,
    )


# ── guard rail merge tests ────────────────────────────────────────────────────

class TestGuardrailEvidenceGating:
    def _disc(self, title, file=None, severity="high", category="auth"):
        from app.services.llm_service import GuardRailDiscovery, _DiscoveredFinding
        return GuardRailDiscovery(findings=[
            _DiscoveredFinding(
                title=title, severity=severity, category=category,
                description="d", recommendation="r",
                file=file, rationale="r",
            )
        ])

    def test_finding_with_real_file_kept_as_medium(self):
        base = _make_guardrail_base()
        disc = self._disc("Unvalidated redirect", file="backend/app/api/routes/auth.py")
        ctx = {"file_tree": ["backend/app/api/routes/auth.py", "backend/app/main.py"]}
        result = _merge_guardrail_discovery(base, disc, ctx)
        new = [f for f in result.findings if f.title == "Unvalidated redirect"]
        assert len(new) == 1
        assert new[0].confidence == "medium"

    def test_finding_with_fake_file_dropped(self):
        base = _make_guardrail_base()
        disc = self._disc("SQL injection risk", file="backend/app/does_not_exist.py")
        ctx = {"file_tree": ["backend/app/main.py"]}
        result = _merge_guardrail_discovery(base, disc, ctx)
        new = [f for f in result.findings if f.title == "SQL injection risk"]
        assert len(new) == 0

    def test_finding_with_no_file_dropped(self):
        base = _make_guardrail_base()
        disc = self._disc("Vague auth risk", file=None)
        ctx = {"file_tree": ["backend/app/main.py"]}
        result = _merge_guardrail_discovery(base, disc, ctx)
        new = [f for f in result.findings if f.title == "Vague auth risk"]
        assert len(new) == 0

    def test_finding_with_same_file_and_category_as_heuristic_dropped(self):
        """Same file+category as existing heuristic finding → duplicate."""
        base = _make_guardrail_base()
        # Same file ("backend/app/main.py") and category ("cors") as SEC-001
        disc = self._disc(
            "Different CORS title", file="backend/app/main.py",
            severity="medium", category="cors",
        )
        ctx = {"file_tree": ["backend/app/main.py"]}
        result = _merge_guardrail_discovery(base, disc, ctx)
        cors_findings = [f for f in result.findings if f.category == "cors"]
        # Should still be only 1 (the heuristic one)
        assert len(cors_findings) == 1

    def test_heuristic_finding_confidence_unchanged(self):
        """Heuristic findings must stay confidence='high' after a merge."""
        base = _make_guardrail_base()
        disc = self._disc("New finding", file="backend/app/main.py", category="auth")
        ctx = {"file_tree": ["backend/app/main.py"]}
        result = _merge_guardrail_discovery(base, disc, ctx)
        heuristic = [f for f in result.findings if f.source == "heuristic"]
        assert all(f.confidence == "high" for f in heuristic)


class TestWordOverlapDedup:
    def test_70_percent_overlap_is_dup(self):
        # "Add CI pipeline" vs "Add CI/CD pipeline setup" shares 3/4 words = 75%
        assert _word_overlap_dup("Add CI pipeline", ["Add CI pipeline setup"]) is True

    def test_exact_match_is_dup(self):
        assert _word_overlap_dup("Set up CI pipeline", ["Set up CI pipeline"]) is True

    def test_completely_different_is_not_dup(self):
        assert _word_overlap_dup("SQL injection in login", ["Missing rate limit"]) is False

    def test_partial_overlap_below_threshold_is_not_dup(self):
        assert _word_overlap_dup("Add caching", ["Add database indexing"]) is False


class TestPlanForgeMerge:
    def _disc_milestone(self, title, file=None):
        from app.services.llm_service import PlanForgeDiscovery, _DiscoveredMilestone
        return PlanForgeDiscovery(milestones=[
            _DiscoveredMilestone(
                title=title, description="d", estimated_days=3,
                priority="high", category="feature",
                rationale="r", file=file,
            )
        ], blockers=[])

    def test_milestone_with_real_file_kept_as_medium(self):
        base = _make_planforge_base()
        disc = self._disc_milestone("Add streaming endpoint", file="backend/app/api/routes/analysis.py")
        ctx = {"file_tree": ["backend/app/api/routes/analysis.py"]}
        result = _merge_plan_discovery(base, disc, ctx)
        new = [m for m in result.milestones if m.title == "Add streaming endpoint"]
        assert len(new) == 1
        assert new[0].confidence == "medium"

    def test_milestone_with_fake_file_dropped(self):
        base = _make_planforge_base()
        disc = self._disc_milestone("Add caching layer", file="backend/app/cache.py")
        ctx = {"file_tree": ["backend/app/main.py"]}
        result = _merge_plan_discovery(base, disc, ctx)
        new = [m for m in result.milestones if "caching" in m.title.lower()]
        assert len(new) == 0

    def test_word_overlap_milestone_dropped(self):
        """70%+ title overlap with existing heuristic milestone → dup."""
        base = _make_planforge_base()
        # "Add CI pipeline" has high overlap with "Set up a CI/CD pipeline"
        disc = self._disc_milestone(
            "Add CI CD pipeline", file="backend/app/main.py",
        )
        ctx = {"file_tree": ["backend/app/main.py"]}
        result = _merge_plan_discovery(base, disc, ctx)
        ci_milestones = [m for m in result.milestones if "ci" in m.title.lower()]
        assert len(ci_milestones) == 1  # only the heuristic one


class TestTestPilotMerge:
    def _disc_test(self, name, target_file=None):
        from app.services.llm_service import TestPilotDiscovery, _DiscoveredTest
        return TestPilotDiscovery(suggested_tests=[
            _DiscoveredTest(
                name=name, type="unit", priority="high",
                description="d", target_file=target_file, rationale="r",
            )
        ], missing_coverage_areas=[])

    def test_test_with_real_target_file_kept_as_medium(self):
        base = _make_testpilot_base()
        disc = self._disc_test(
            "test_analyze_handles_bad_token",
            target_file="backend/app/api/routes/analysis.py",
        )
        ctx = {"file_tree": ["backend/app/api/routes/analysis.py"]}
        result = _merge_testpilot_discovery(base, disc, ctx)
        new = [t for t in result.suggested_tests if t.name == "test_analyze_handles_bad_token"]
        assert len(new) == 1
        assert new[0].confidence == "medium"

    def test_test_with_fake_target_file_dropped(self):
        base = _make_testpilot_base()
        disc = self._disc_test(
            "test_nonexistent_module_loads",
            target_file="backend/app/nonexistent.py",
        )
        ctx = {"file_tree": ["backend/app/main.py"]}
        result = _merge_testpilot_discovery(base, disc, ctx)
        new = [t for t in result.suggested_tests if "nonexistent" in t.name]
        assert len(new) == 0
