import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict

from ..agents.repo_lens_agent import RepoLensAgent
from ..agents.plan_forge_agent import PlanForgeAgent
from ..agents.guardrail_agent import GuardRailAgent
from ..agents.testpilot_agent import TestPilotAgent
from ..services.scoring_service import ScoringService
from ..services.report_service import ReportService
from ..schemas.agent_schemas import (
    AgentOutputs, ShipMateReport, RepoInfo, ShipRecommendation
)


class ShipMateOrchestrator:
    """
    Runs the 4-agent pipeline and assembles the final ShipMateReport.

    Execution order:
      1. RepoLens  — repo structure, tech stack, architecture risks (context builder)
      2. PlanForge, GuardRail, TestPilot  — run with enriched context (parallel-safe)
      3. ScoringService  — deterministic weighted score
      4. ReportService   — final report assembly
    """

    def __init__(self):
        self.repo_lens = RepoLensAgent()
        self.plan_forge = PlanForgeAgent()
        self.guardrail = GuardRailAgent()
        self.testpilot = TestPilotAgent()

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
        Returns:
            ShipMateReport
        """
        # ── Step 1: RepoLens (must run first — other agents need its output) ──
        # Reuse a RepoLens output already attached to the context (e.g. by
        # RepoIndexService, which analyzes the repo once and shares the result)
        # instead of re-running the pass. Falls back to running it when absent.
        repo_lens_out = repo_context.get("repo_lens") or self.repo_lens.run(repo_context)

        # Enrich context with RepoLens output
        enriched = {**repo_context, "repo_lens": repo_lens_out}

        # ── Step 2: Run remaining agents (all consume enriched context) ──
        plan_forge_out = self.plan_forge.run(enriched)
        guardrail_out = self.guardrail.run(enriched)
        testpilot_out = self.testpilot.run(enriched)

        # ── Steps 3+4: Score + assemble (shared with run_stream) ──
        return self._assemble_report(
            repo_context, repo_lens_out, plan_forge_out, guardrail_out, testpilot_out
        )

    async def run_stream(
        self, repo_context: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Async generator that yields one event per agent as it completes, then
        a final assembled report. Powers the SSE endpoint so the frontend renders
        each agent's result incrementally instead of waiting for the whole batch.

        Event shapes:
          {"event": "agent.done", "agent": "<name>", "output": {...}}
          {"event": "report.done", "report": {...}}
          {"event": "error", "detail": "..."}

        The agents' .run() methods are blocking (heuristics + one LLM call each),
        so each is dispatched via asyncio.to_thread to keep the event loop free
        while the SSE connection streams. run() stays the synchronous source of
        truth used by auto_fix and the non-streaming /analyze route."""
        try:
            # Reuse a context-supplied RepoLens (RepoIndexService) if present.
            repo_lens_out = repo_context.get("repo_lens") or \
                await asyncio.to_thread(self.repo_lens.run, repo_context)
            yield {"event": "agent.done", "agent": "repo_lens",
                   "output": repo_lens_out.model_dump()}

            enriched = {**repo_context, "repo_lens": repo_lens_out}

            plan_forge_out = await asyncio.to_thread(self.plan_forge.run, enriched)
            yield {"event": "agent.done", "agent": "plan_forge",
                   "output": plan_forge_out.model_dump()}

            guardrail_out = await asyncio.to_thread(self.guardrail.run, enriched)
            yield {"event": "agent.done", "agent": "guardrail",
                   "output": guardrail_out.model_dump()}

            testpilot_out = await asyncio.to_thread(self.testpilot.run, enriched)
            yield {"event": "agent.done", "agent": "testpilot",
                   "output": testpilot_out.model_dump()}

            report = self._assemble_report(
                repo_context, repo_lens_out, plan_forge_out, guardrail_out, testpilot_out
            )
            yield {"event": "report.done", "report": report.model_dump()}
        except Exception as e:  # pragma: no cover - defensive stream guard
            yield {"event": "error", "detail": f"Analysis failed: {e}"}

    def _assemble_report(
        self, repo_context, repo_lens_out, plan_forge_out, guardrail_out, testpilot_out
    ) -> ShipMateReport:
        """Score + assemble the final ShipMateReport from the four agent outputs.
        Shared by run() (sync) and run_stream() (SSE) so the assembly logic lives
        in exactly one place."""
        score_breakdown = ScoringService.calculate(
            repo_lens_out, plan_forge_out, guardrail_out, testpilot_out
        )
        final_score = score_breakdown["final_score"]
        recommendation = ScoringService.recommendation(final_score)

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

        # Was the LLM discovery/enhancement path live this run? If not, the
        # outputs are pure heuristics (generic milestones, template tests) and
        # the UI should say so rather than present them as AI findings.
        try:
            from app.services.llm_service import LLMService
            ai_enhanced = LLMService.is_available()
        except Exception:
            ai_enhanced = False

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
            ai_enhanced=ai_enhanced,
        )
