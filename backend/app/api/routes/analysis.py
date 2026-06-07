import asyncio
import logging

from fastapi import APIRouter, HTTPException
from app.schemas.api_schemas import AnalyzeRequest, AnalyzeResponse
from app.services.repo_analysis_service import RepoAnalysisService
from app.orchestrator.shipmate_orchestrator import ShipMateOrchestrator
from app.utils.github_auth import verify_repo_write_access
from app.services.github_comment_service import post_pr_comment
from app.services.score_history_service import record_score

router = APIRouter(tags=["analysis"])
logger = logging.getLogger("shipmate.analysis_route")

_orchestrator = ShipMateOrchestrator()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Run the ShipMate 4-agent analysis pipeline on a GitHub repository.

    Flow:
      1. Verify the token has write access to owner/repo
      2. Fetch repo tree + key files from GitHub
      3. RepoLens  → tech stack, architecture, risks
      4. PlanForge → milestones, blockers, delivery plan
      5. GuardRail → security findings, secrets, CORS, auth
      6. TestPilot → coverage gaps, suggested tests
      7. Score → weighted readiness score (0-100)
      8. Return ShipMateReport
    """
    if not request.owner or not request.repo:
        raise HTTPException(status_code=400, detail="owner and repo are required.")

    await verify_repo_write_access(request.access_token, request.owner, request.repo)

    try:
        repo_context = await RepoAnalysisService.build_context(
            token=request.access_token,
            owner=request.owner,
            repo=request.repo,
            branch=request.branch,
            pr_number=request.pr_number,
            feature_context=request.feature_context or "",
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch repository data from GitHub: {str(e)}"
        )

    try:
        report = await _orchestrator.run(repo_context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {str(e)}")

    # Persist score history (non-fatal)
    try:
        record_score(
            owner=request.owner,
            repo=request.repo,
            branch=request.branch,
            score=report.readiness_score,
            breakdown={
                "repo": report.score_breakdown.repo_score,
                "delivery": report.score_breakdown.delivery_score,
                "security": report.score_breakdown.security_score,
                "test": report.score_breakdown.test_score,
            },
        )
    except Exception as e:
        logger.warning("score_history record failed: %s", e)

    # Post PR comment (non-fatal, fire-and-forget)
    if request.pr_number:
        asyncio.create_task(post_pr_comment(
            token=request.access_token,
            owner=request.owner,
            repo=request.repo,
            pr_number=request.pr_number,
            report=report,
        ))

    return AnalyzeResponse(status="complete", report=report)
