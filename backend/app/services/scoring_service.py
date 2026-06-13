from typing import Dict, Any, List

from ..schemas.agent_schemas import (
    RepoLensOutput, PlanForgeOutput, GuardRailOutput, TestPilotOutput,
    ShipRecommendation, ScoreBreakdown,
)

# Score thresholds below which we add an explanation entry
_EXPLAIN_THRESHOLD = 80


class ScoringService:
    """
    Deterministic weighted scoring formula:

    final_score = repo_score  * 0.20
               + delivery_score * 0.25
               + security_score * 0.30
               + test_score    * 0.25

    Score meaning:
      90-100  ready_to_ship
      75-89   mostly_ready
      60-74   needs_review
      40-59   risky_release
      0-39    not_ready
    """

    WEIGHTS = {
        "repo":     0.20,
        "delivery": 0.25,
        "security": 0.30,
        "test":     0.25,
    }

    @classmethod
    def calculate(
        cls,
        repo_lens: RepoLensOutput,
        plan_forge: PlanForgeOutput,
        guardrail: GuardRailOutput,
        testpilot: TestPilotOutput,
    ) -> Dict[str, Any]:
        rs = repo_lens.repo_score
        ds = plan_forge.delivery_score
        ss = guardrail.security_score
        ts = testpilot.test_score

        final = int(
            rs * cls.WEIGHTS["repo"]
            + ds * cls.WEIGHTS["delivery"]
            + ss * cls.WEIGHTS["security"]
            + ts * cls.WEIGHTS["test"]
        )
        final = max(0, min(100, final))

        return {
            "final_score": final,
            "breakdown": ScoreBreakdown(
                repo_score=rs,
                delivery_score=ds,
                security_score=ss,
                test_score=ts,
            ),
            "score_explanation": cls._explain(rs, ds, ss, ts, repo_lens, guardrail, testpilot),
        }

    @classmethod
    def _explain(
        cls,
        rs: int, ds: int, ss: int, ts: int,
        repo_lens: RepoLensOutput,
        guardrail: GuardRailOutput,
        testpilot: TestPilotOutput,
    ) -> List[str]:
        """Generate up to 6 human-readable score deduction lines, each ≤80 chars."""
        lines: List[str] = []

        # Security score (weight 0.30 — biggest lever)
        if ss < _EXPLAIN_THRESHOLD:
            deduction = int((100 - ss) * cls.WEIGHTS["security"])
            if guardrail.exposed_secrets:
                lines.append(f"-{deduction} security_score: exposed secrets detected")
            elif guardrail.cors_issues:
                lines.append(f"-{deduction} security_score: CORS misconfiguration found")
            else:
                lines.append(f"-{deduction} security_score: score {ss}/100")

        # Test score (weight 0.25)
        if ts < _EXPLAIN_THRESHOLD:
            deduction = int((100 - ts) * cls.WEIGHTS["test"])
            if not repo_lens.has_tests:
                lines.append(f"-{deduction} test_score: no test files detected")
            else:
                lines.append(f"-{deduction} test_score: score {ts}/100")

        # Delivery score (weight 0.25)
        if ds < _EXPLAIN_THRESHOLD:
            deduction = int((100 - ds) * cls.WEIGHTS["delivery"])
            lines.append(f"-{deduction} delivery_score: score {ds}/100")

        # Repo score (weight 0.20)
        if rs < _EXPLAIN_THRESHOLD:
            deduction = int((100 - rs) * cls.WEIGHTS["repo"])
            if not repo_lens.has_ci_cd:
                lines.append(f"-{deduction} repo_score: no CI/CD pipeline configured")
            elif not repo_lens.has_dockerfile:
                lines.append(f"-{deduction} repo_score: no Dockerfile found")
            else:
                lines.append(f"-{deduction} repo_score: score {rs}/100")

        # Clamp to 6, each ≤80 chars
        return [e[:80] for e in lines[:6]]

    @classmethod
    def recommendation(cls, score: int) -> ShipRecommendation:
        if score >= 90:
            return ShipRecommendation.READY
        if score >= 75:
            return ShipRecommendation.MOSTLY_READY
        if score >= 60:
            return ShipRecommendation.NEEDS_REVIEW
        if score >= 40:
            return ShipRecommendation.RISKY
        return ShipRecommendation.NOT_READY
