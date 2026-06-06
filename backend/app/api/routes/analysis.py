from fastapi import APIRouter, HTTPException
from app.schemas.api_schemas import AnalyzeRequest, AnalyzeResponse
from app.services.repo_analysis_service import RepoAnalysisService
from app.orchestrator.shipmate_orchestrator import ShipMateOrchestrator
from app.utils.github_auth import verify_repo_write_access

router = APIRouter(tags=["analysis"])

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
        report = _orchestrator.run(repo_context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {str(e)}")

    return AnalyzeResponse(status="complete", report=report)
