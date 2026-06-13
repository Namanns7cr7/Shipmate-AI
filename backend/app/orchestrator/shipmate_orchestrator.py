import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict

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
      2. PlanForge, GuardRail, TestPilot  — run in parallel via asyncio.to_thread
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

    async def run(self, repo_context: Dict[str, Any]) -> ShipMateReport:
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
        # Reuse a cached RepoLens output if present (from RepoIndexService),
        # otherwise run it synchronously.
        repo_lens_out = repo_context.get("repo_lens") or self.repo_lens.run(repo_context)

        # Enrich context with RepoLens output
        enriched = {**repo_context, "repo_lens": repo_lens_out}

        # ── Step 2: PlanForge, GuardRail, TestPilot run in parallel ──────────
        plan_forge_out, guardrail_out, testpilot_out = await asyncio.gather(
            asyncio.to_thread(self.plan_forge.run, enriched),
            asyncio.to_thread(self.guardrail.run, enriched),
            asyncio.to_thread(self.testpilot.run, enriched),
        )

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
        # Anti-recurrence: strip findings that are already-resolved in the repo
        # or dismissed/shipped in the journal BEFORE scoring + assembly. The
        # analyze pipeline had no equivalent of the Build path's already_built
        # gate, so it kept re-proposing shipped work (token-in-query after the
        # routes already use the header dep, "persist results" after save_report
        # is wired in) and keyword false-positives. Done here so both run() and
        # run_stream() get it, and so the SCORE reflects the filtered findings.
        plan_forge_out, guardrail_out, testpilot_out = self._filter_findings(
            repo_context, plan_forge_out, guardrail_out, testpilot_out
        )

        # ── Step 2b: PR Risk — only when this is a PR-scoped analysis ──
        pr_risk_out = self.pr_risk.run(repo_context) if self._has_pr(repo_context) else None

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
            pr_risk=pr_risk_out,
            ai_enhanced=ai_enhanced,
            score_explanation=score_breakdown.get("score_explanation", []),
        )

    def _filter_findings(self, repo_context, plan_forge_out, guardrail_out, testpilot_out):
        """Apply the shared finding_critic gates to the analyze-side outputs so
        the diagnostic agents stop re-surfacing already-resolved / dismissed /
        false-positive findings — the same protection the Build path's
        already_built + journal gates give the Opportunity pipeline.

        Three passes per agent, all fail-open (any error keeps the findings):
          1. already-resolved prefilter — deterministic, scans the FULL corpus
             for proof the demanded control already exists.
          2. journal suppression — drop dismissed/shipped signatures.
          3. LLM critic verify (GuardRail only) — refute remaining false
             positives against the exact code blob.
        Returns the three (possibly-filtered) agent outputs."""
        try:
            from app.services import finding_critic as fc
        except Exception:
            return plan_forge_out, guardrail_out, testpilot_out

        file_tree = repo_context.get("file_tree") or []
        key_files = repo_context.get("key_files") or {}
        info = repo_context.get("repo_info") or {}
        owner = (
            info.get("owner", {}).get("login", "")
            if isinstance(info.get("owner"), dict) else info.get("owner", "")
        )
        full_name = info.get("full_name", "") or (
            f"{owner}/{info.get('name','')}" if owner and info.get("name") else ""
        )

        # GuardRail security findings — the noisiest surface.
        try:
            f = guardrail_out.findings
            f = fc.filter_already_resolved(f, file_tree, key_files, kind="guardrail")
            f = fc.filter_suppressed(f, "guardrail", full_name)
            # LLM critic verify against the real code blob (fail-open inside).
            try:
                from app.services.llm_service import LLMService
                provider = LLMService.provider()
                code_blob = LLMService.opportunity_code_blob(repo_context) if provider else ""
                if provider and code_blob:
                    f = fc.verify_findings(f, code_blob, provider)
            except Exception:
                pass
            guardrail_out.findings = f
        except Exception as e:  # pragma: no cover - defensive
            pass

        # PlanForge blockers (milestones are roadmap items, not 'findings' — left
        # to the Build/Opportunity pipeline's own already_built gate).
        try:
            b = plan_forge_out.blockers
            b = fc.filter_already_resolved(b, file_tree, key_files, kind="blocker")
            b = fc.filter_suppressed(b, "blocker", full_name)
            plan_forge_out.blockers = b
        except Exception:
            pass

        # TestPilot suggested tests — suppress dismissed/shipped. SuggestedTest
        # uses `.name`, not `.title`, so adapt to the signature scheme.
        try:
            tests = testpilot_out.suggested_tests
            tests = fc.filter_suppressed_by_name(tests, "test", full_name)
            testpilot_out.suggested_tests = tests
        except Exception:
            pass

        return plan_forge_out, guardrail_out, testpilot_out
