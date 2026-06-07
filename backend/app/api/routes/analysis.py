import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.api_schemas import AnalyzeRequest, AnalyzeResponse
from app.services.repo_analysis_service import RepoAnalysisService
from app.services import report_store
from app.orchestrator.shipmate_orchestrator import ShipMateOrchestrator

import httpx

logger = logging.getLogger("shipmate.analysis_route")

router = APIRouter(tags=["analysis"])

_orchestrator = ShipMateOrchestrator()

# Permissions that indicate write access to a repository.
_WRITE_PERMISSIONS = {"admin", "maintain", "write", "push"}


async def _verify_repo_write_access(token: str, owner: str, repo: str) -> None:
    """
    Verify that the supplied GitHub token grants write access to owner/repo.

    Calls the GitHub Collaborator Permission API with the authenticated user's
    token.  Raises HTTP 403 if the token lacks write access, or HTTP 404 if
    the repository does not exist / is not visible to the token.

    Raises HTTPException on any access-control or network failure.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"https://api.github.com/repos/{owner}/{repo}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to reach GitHub API to verify repository access: {exc}",
        )

    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{owner}/{repo}' not found or not accessible with the provided token.",
        )

    if response.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail="GitHub token is invalid or expired.",
        )

    if response.status_code not in (200, 301):
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API returned unexpected status {response.status_code} while checking repository access.",
        )

    repo_data = response.json()
    # The /repos/{owner}/{repo} response includes a `permissions` object when
    # the token has any access.  If the object is absent the token is read-only
    # (e.g. a public-repo token with no write scope).
    permissions: dict = repo_data.get("permissions", {})
    has_write = (
        permissions.get("admin") is True
        or permissions.get("maintain") is True
        or permissions.get("push") is True
    )

    if not has_write:
        raise HTTPException(
            status_code=403,
            detail=(
                f"The authenticated token does not have write access to '{owner}/{repo}'. "
                "Only repositories where you have push, maintain, or admin permission "
                "may be analysed."
            ),
        )


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

    # --- Authorization check: token must have write access to the target repo ---
    await _verify_repo_write_access(
        token=request.access_token,
        owner=request.owner,
        repo=request.repo,
    )

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

    # Persist the run for the history/trend dashboard. Best-effort: a storage
    # failure must not fail the analysis the caller already has in hand.
    report_store.save_report(report)

    return AnalyzeResponse(status="complete", report=report)


@router.post("/analyze/stream")
async def analyze_stream(request: AnalyzeRequest):
    """Server-Sent Events variant of /analyze: emits one event per agent as it
    completes (repo_lens → plan_forge → guardrail → testpilot), then a final
    report event. Lets the frontend render incremental progress instead of a
    blank wait screen on large repos.

    Same auth + context-build prelude as /analyze; only the orchestration is
    streamed. The final report is persisted exactly like the batch route."""
    if not request.owner or not request.repo:
        raise HTTPException(status_code=400, detail="owner and repo are required.")

    await _verify_repo_write_access(
        token=request.access_token, owner=request.owner, repo=request.repo,
    )

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
            detail=f"Failed to fetch repository data from GitHub: {str(e)}",
        )

    async def _event_source():
        try:
            async for event in _orchestrator.run_stream(repo_context):
                # Persist the streamed run too, so the history dashboard sees it.
                # The report.done frame carries the assembled report as a dict;
                # rebuild a ShipMateReport from it for the store (best-effort).
                if event.get("event") == "report.done":
                    try:
                        from app.schemas.agent_schemas import ShipMateReport
                        report_store.save_report(
                            ShipMateReport.model_validate(event["report"])
                        )
                    except Exception:
                        pass
                yield f"event: {event.get('event', 'message')}\ndata: {json.dumps(event)}\n\n"
        except Exception as e:  # pragma: no cover - stream guard
            logger.exception("analyze_stream failed")
            yield f"event: error\ndata: {json.dumps({'detail': f'stream failed: {e}'})}\n\n"

    return StreamingResponse(
        _event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/repos/{owner}/{repo}/history")
async def repo_history(owner: str, repo: str, limit: int = 20):
    """Return the persisted analysis-run history for owner/repo (newest first),
    so the dashboard can chart readiness-score trends over time."""
    runs = report_store.list_reports(owner, repo, limit=limit)
    return {"owner": owner, "repo": repo, "count": len(runs), "runs": runs}


@router.get("/analysis/{report_id}")
async def get_analysis(report_id: int):
    """Return a single persisted ShipMateReport by id (full detail view)."""
    rep = report_store.get_report(report_id)
    if rep is None:
        raise HTTPException(status_code=404, detail=f"No analysis run with id {report_id}.")
    return rep
