"""
OpportunityService — orchestrates the Phase-1A opportunity pipeline.

This is the thin coordinator the /api/build/plan route calls. It does NOT
re-fetch the repo or re-run the whole 4-agent pipeline — it reuses the same
context dict RepoAnalysisService already builds, runs RepoLens (cheap,
deterministic, needed for the code-blob's entry-point scoring), then:

    discover (LLM)  →  ground (deterministic)  →  suppress (journal)  →  rank

and returns a BuildPlanResponse. Plan-only: no Coder, no PRs, no journal writes
on the read path (selecting/building an opportunity is a separate Phase-1B/2
action that will mark it in_progress).

Everything is fail-open: an LLM outage yields an empty, ai_enhanced=False plan
rather than an error, exactly like the discovery passes elsewhere.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.agents.repo_lens_agent import RepoLensAgent
from app.schemas.agent_schemas import BuildPlanResponse, Opportunity
from app.services import opportunity_critic as critic
from app.services.llm_service import LLMService

logger = logging.getLogger("shipmate.opportunity_service")


class OpportunityService:
    """Stateless coordinator. Mirrors ShipMateOrchestrator's role but for the
    single-purpose opportunity pipeline."""

    _repo_lens = RepoLensAgent()

    @classmethod
    def build_plan(
        cls,
        repo_context: Dict[str, Any],
        *,
        max_opportunities: int = 8,
        include_ungrounded: bool = False,
    ) -> BuildPlanResponse:
        """Run discover → ground → suppress → rank against an already-built
        repo context and return a ranked, grounded BuildPlanResponse.

        `repo_context` is the same dict RepoAnalysisService.build_context()
        produces (repo_info, file_tree, key_files, branch, …)."""
        info = repo_context.get("repo_info") or {}
        owner = (
            info.get("owner", {}).get("login", "")
            if isinstance(info.get("owner"), dict)
            else info.get("owner", "")
        )
        name = info.get("name", "")
        full_name = info.get("full_name", "") or (f"{owner}/{name}" if owner and name else "")
        branch = repo_context.get("branch", "main")
        generated_at = datetime.now(timezone.utc).isoformat()

        # RepoLens output enriches the code-blob's entry-point scoring (same as
        # the other discovery passes, which run after RepoLens in the pipeline).
        try:
            repo_lens_out = cls._repo_lens.run(repo_context)
            enriched = {**repo_context, "repo_lens": repo_lens_out}
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("RepoLens failed in opportunity pipeline (%s); proceeding without it", e)
            enriched = repo_context

        # 1. DISCOVER (LLM) — raw candidates, or [] if the provider is down.
        raw: List[Opportunity] = LLMService.discover_opportunities(
            enriched, max_opportunities=max_opportunities
        )
        ai_enhanced = LLMService.is_available()
        total_found = len(raw)

        if not raw:
            return BuildPlanResponse(
                owner=owner, repo=name, branch=branch,
                opportunities=[], total_found=0, grounded_count=0,
                ai_enhanced=ai_enhanced, generated_at=generated_at,
            )

        # 2. GROUND (deterministic) — verify cited evidence points at real files.
        file_tree = repo_context.get("file_tree") or []
        key_files = repo_context.get("key_files") or {}
        grounded = critic.ground_opportunities(raw, file_tree, key_files)
        grounded_count = sum(1 for o in grounded if getattr(o, "grounded", False))

        # 3. SUPPRESS (journal) — drop dismissed/shipped (opportunity namespace).
        kept = critic.filter_suppressed(grounded, full_name)

        # 4. RANK (fold-in) — score, downrank in_progress, sort, derive priority.
        ranked = critic.rank_opportunities(
            kept, full_name, drop_ungrounded=not include_ungrounded
        )

        return BuildPlanResponse(
            owner=owner, repo=name, branch=branch,
            opportunities=ranked,
            total_found=total_found,
            grounded_count=grounded_count,
            ai_enhanced=ai_enhanced,
            generated_at=generated_at,
        )
