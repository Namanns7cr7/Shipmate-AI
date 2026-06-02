from fastapi import APIRouter, HTTPException
from app.schemas.api_schemas import AnalyzeRequest, AnalyzeResponse
from app.services.repo_analysis_service import RepoAnalysisService
from app.orchestrator.shipmate_orchestrator import ShipMateOrchestrator

router = APIRouter(tags=["analysis"])

_orchestrator = ShipMateOrchestrator()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Run the ShipMate 4-agent analysis pipeline on a GitHub repository.

    Flow:
      1. Fetch repo tree + key files from GitHub
      2. RepoLens  → tech stack, architecture, risks
      3. PlanForge → milestones, blockers, delivery plan
      4. GuardRail → security findings, secrets, CORS, auth
      5. TestPilot → coverage gaps, suggested tests
      6. Score → weighted readiness score (0-100)
      7. Return ShipMateReport
    """
    if not request.owner or not request.repo:
        raise HTTPException(status_code=400, detail="owner and repo are required.")

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
