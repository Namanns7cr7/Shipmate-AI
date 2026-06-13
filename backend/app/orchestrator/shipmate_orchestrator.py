from datetime import datetime, timezone
from typing import Any, Dict

from ..agents.repo_lens_agent import RepoLensAgent
from ..agents.plan_forge_agent import PlanForgeAgent
from ..agents.guardrail_agent import GuardRailAgent
from ..agents.testpilot_agent import TestPilotAgent
from ..agents.pr_risk_agent import PRRiskAgent
from ..services.scoring_service import ScoringService
from ..services.report_service import ReportService
from ..schemas.agent_schemas import (
    AgentOutputs, ShipMateReport, RepoInfo, ShipRecommendation
)


class ShipMateOrchestrator:
    """
    Runs the agent pipeline and assembles the final ShipMateReport.

    Execution order:
      1. RepoLens  — repo structure, tech stack, architecture risks (context builder)
      2. PlanForge, GuardRail, TestPilot  — run with enriched context (parallel-safe)
      3. PRRiskAgent — ONLY for a PR-scoped analysis (pr_number → pr_files present)
      4. ScoringService  — deterministic weighted score
      5. ReportService   — final report assembly
    """

    def __init__(self):
        self.repo_lens = RepoLensAgent()
        self.plan_forge = PlanForgeAgent()
        self.guardrail = GuardRailAgent()
        self.testpilot = TestPilotAgent()
        self.pr_risk = PRRiskAgent()

    @staticmethod
    def _has_pr(repo_context: Dict[str, Any]) -> bool:
        """PR risk only runs for a PR-scoped analysis (pr_number → pr_files)."""
        return bool(repo_context.get("pr_files"))

    def run(self, repo_context: Dict[str, Any]) -> ShipMateReport:
        """
        Args:
            repo_context: dict with keys:
                - repo_info: dict (from GitHub API)
                - file_tree: List[str]
                - key_files: Dict[str, str]
                - branch: str
                - feature_context: str (optional)
                - pr_info: dict (optional)
                - pr_files: List[dict] (optional — present for a PR-scoped run)
        Returns:
            ShipMateReport
        """
        # ── Step 1: RepoLens (must run first — other agents need its output) ──
        repo_lens_out = self.repo_lens.run(repo_context)

        # Enrich context with RepoLens output
        enriched = {**repo_context, "repo_lens": repo_lens_out}

        # ── Step 2: Run remaining agents (all consume enriched context) ──
        plan_forge_out = self.plan_forge.run(enriched)
        guardrail_out = self.guardrail.run(enriched)
        testpilot_out = self.testpilot.run(enriched)

        # ── Step 2b: PR Risk — only when this is a PR-scoped analysis ──
        pr_risk_out = self.pr_risk.run(enriched) if self._has_pr(repo_context) else None

        # ── Step 3: Score ──
        score_breakdown = ScoringService.calculate(
            repo_lens_out, plan_forge_out, guardrail_out, testpilot_out
        )
        final_score = score_breakdown["final_score"]
        recommendation = ScoringService.recommendation(final_score)

        # ── Step 4: Assemble report ──
        info = repo_context.get("repo_info", {})
        branch = repo_context.get("branch", "main")

        repo_info = RepoInfo(
            owner=info.get("owner", {}).get("login", "") if isinstance(info.get("owner"), dict) else info.get("owner", ""),
            name=info.get("name", ""),
            full_name=info.get("full_name", ""),
            branch=branch,
            description=info.get("description"),
            language=info.get("language"),
            stars=info.get("stargazers_count", 0),
            file_count=repo_lens_out.file_count,
            html_url=info.get("html_url", ""),
        )

        key_blockers = ReportService.extract_blockers(plan_forge_out, guardrail_out)
        next_actions = ReportService.extract_next_actions(plan_forge_out, guardrail_out, testpilot_out)

        return ShipMateReport(
            repo=repo_info,
            readiness_score=final_score,
            ship_recommendation=recommendation,
            score_breakdown=score_breakdown["breakdown"],
            agents=AgentOutputs(
                repo_lens=repo_lens_out,
                plan_forge=plan_forge_out,
                guardrail=guardrail_out,
                testpilot=testpilot_out,
            ),
            key_blockers=key_blockers,
            next_actions=next_actions,
            generated_at=datetime.now(timezone.utc).isoformat(),
            pr_risk=pr_risk_out,
        )
