"""
POST /api/build/plan — Phase 1A Opportunity Planner.

Returns a ranked, grounded list of self-improvement opportunities for a repo:
new features, improvements to existing ones, code-quality tweaks, and bugs —
each cited against real files and scored by value. Plan-only: NO PRs, NO Coder,
NO journal writes. This is the surface that proves opportunity quality before
Phase 1B (planning) and Phase 2 (execution) are built on top.

Same auth + context-build prelude as /analyze (you can only plan work for repos
you have write access to). Fail-open: an LLM outage returns an empty plan with
ai_enhanced=False rather than an error.
"""
import logging

import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.api_schemas import (
    BuildPlanRequest, BuildExecuteRequest, BuildDismissRequest,
)
from app.schemas.agent_schemas import BuildPlanResponse, BuildExecuteResponse
from app.services.repo_analysis_service import RepoAnalysisService
from app.services.opportunity_service import OpportunityService
from app.api.routes.analysis import _verify_repo_write_access

router = APIRouter(tags=["build"])
logger = logging.getLogger("shipmate.build_route")


@router.post("/build/plan", response_model=BuildPlanResponse)
async def build_plan(request: BuildPlanRequest) -> BuildPlanResponse:
    if not request.owner or not request.repo:
        raise HTTPException(status_code=400, detail="owner and repo are required.")
    if not request.access_token:
        raise HTTPException(status_code=400, detail="access_token is required.")

    # Authorization: write access required, mirroring /analyze.
    await _verify_repo_write_access(
        token=request.access_token, owner=request.owner, repo=request.repo,
    )

    try:
        repo_context = await RepoAnalysisService.build_context(
            token=request.access_token,
            owner=request.owner,
            repo=request.repo,
            branch=request.branch,
        )
        # Pull route/service/agent source into the corpus so the planner can SEE
        # what already exists (otherwise it re-proposes built features every run).
        await RepoAnalysisService.enrich_build_corpus(
            request.access_token, request.owner, request.repo, repo_context,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch repository data from GitHub: {e}",
        )

    try:
        return OpportunityService.build_plan(
            repo_context,
            max_opportunities=request.max_opportunities,
            include_ungrounded=request.include_ungrounded,
        )
    except Exception as e:
        logger.exception("build_plan failed for %s/%s", request.owner, request.repo)
        raise HTTPException(status_code=500, detail=f"Opportunity planning failed: {e}")


@router.post("/build/execute", response_model=BuildExecuteResponse)
async def build_execute(request: BuildExecuteRequest) -> BuildExecuteResponse:
    """Phase 1B: plan a chosen opportunity, critique the plan, and — when
    execute=true AND the critic approves — actuate each step through the Coder.

    execute=false (default) is a safe, free plan+critique preview. execute=true
    opens real PRs, so it requires write access (verified) and each step still
    passes CoderOrchestrator's lint/scope/pytest/resolution gates."""
    if not request.owner or not request.repo:
        raise HTTPException(status_code=400, detail="owner and repo are required.")
    if not request.access_token:
        raise HTTPException(status_code=400, detail="access_token is required.")

    await _verify_repo_write_access(
        token=request.access_token, owner=request.owner, repo=request.repo,
    )

    try:
        repo_context = await RepoAnalysisService.build_context(
            token=request.access_token,
            owner=request.owner,
            repo=request.repo,
            branch=request.branch,
        )
        await RepoAnalysisService.enrich_build_corpus(
            request.access_token, request.owner, request.repo, repo_context,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch repository data from GitHub: {e}",
        )

    # RepoLens enriches the plan/execute context (entry points for the Coder).
    try:
        from app.agents.repo_lens_agent import RepoLensAgent
        repo_context["repo_lens"] = RepoLensAgent().run(repo_context)
    except Exception as e:
        logger.warning("RepoLens failed in execute path (%s); proceeding", e)

    try:
        return await OpportunityService.execute_opportunity(
            repo_context, request.opportunity, request.access_token,
            execute=request.execute,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"GitHub error: {e}")
    except Exception as e:
        logger.exception("build_execute failed for %s/%s", request.owner, request.repo)
        raise HTTPException(status_code=500, detail=f"Opportunity execution failed: {e}")


@router.post("/build/dismiss")
async def build_dismiss(request: BuildDismissRequest):
    """Hide an opportunity from future plans and exclude it from discovery.
    Journal-only (no GitHub mutation), so no write-access check needed — but the
    repo must be identifiable."""
    if not request.owner or not request.repo:
        raise HTTPException(status_code=400, detail="owner and repo are required.")
    full_name = f"{request.owner}/{request.repo}"
    return OpportunityService.dismiss_opportunity(
        full_name, request.title, request.file or "",
    )
