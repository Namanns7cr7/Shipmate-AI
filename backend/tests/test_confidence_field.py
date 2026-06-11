"""Phase 1, Task 1 — confidence field on finding types.

RED: these tests fail until confidence is added to the schemas.
GREEN: add `confidence: Literal["high", "medium", "low"] = "high"` to
SecurityFinding, Milestone, Blocker, SuggestedTest.
"""
from app.schemas.agent_schemas import (
    SecurityFinding,
    Milestone,
    Blocker,
    SuggestedTest,
    Severity,
)


class TestSecurityFindingConfidence:
    def test_default_is_high(self):
        f = SecurityFinding(
            id="SEC-001", title="Test", severity=Severity.MEDIUM,
            category="secrets", description="d", recommendation="r",
        )
        assert f.confidence == "high"

    def test_explicit_medium(self):
        f = SecurityFinding(
            id="SEC-002", title="Test", severity=Severity.LOW,
            category="auth", description="d", recommendation="r",
            confidence="medium",
        )
        assert f.confidence == "medium"

    def test_explicit_low(self):
        f = SecurityFinding(
            id="SEC-003", title="Test", severity=Severity.INFO,
            category="cors", description="d", recommendation="r",
            confidence="low",
        )
        assert f.confidence == "low"


class TestMilestoneConfidence:
    def test_default_is_high(self):
        m = Milestone(
            title="Add tests", description="desc",
            estimated_days=3, priority="high", category="testing",
        )
        assert m.confidence == "high"

    def test_explicit_medium(self):
        m = Milestone(
            title="CI setup", description="desc",
            estimated_days=1, priority="medium", category="ci_cd",
            confidence="medium",
        )
        assert m.confidence == "medium"


class TestBlockerConfidence:
    def test_default_is_high(self):
        b = Blocker(
            id="BLK-001", title="No tests", description="desc",
            severity="critical", resolution="Add tests", category="testing",
        )
        assert b.confidence == "high"

    def test_explicit_medium(self):
        b = Blocker(
            id="BLK-002", title="Missing CI", description="desc",
            severity="high", resolution="Add CI", category="ci_cd",
            confidence="medium",
        )
        assert b.confidence == "medium"


class TestSuggestedTestConfidence:
    def test_default_is_high(self):
        s = SuggestedTest(
            name="test_auth", type="unit",
            priority="high", description="desc",
        )
        assert s.confidence == "high"

    def test_explicit_medium(self):
        s = SuggestedTest(
            name="test_api", type="integration",
            priority="medium", description="desc",
            confidence="medium",
        )
        assert s.confidence == "medium"
