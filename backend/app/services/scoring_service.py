from typing import Dict, Any

from ..schemas.agent_schemas import (
    RepoLensOutput, PlanForgeOutput, GuardRailOutput, TestPilotOutput,
    ShipRecommendation, ScoreBreakdown,
)


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
        }

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
