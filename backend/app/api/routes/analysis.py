from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import json
from app.db.database import get_db
from app.models.user import User
from app.api.dependencies import get_current_user
from app.orchestrator.shipmate_orchestrator import ShipMateOrchestrator

router = APIRouter()


@router.post("/analyze")
async def analyze(
    repo_owner: str,
    repo_name: str,
    branch: str = "main",
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Stream per-agent analysis results via Server-Sent Events (SSE).
    Each agent's output is sent as it completes, allowing the frontend
    to render progress in real-time.
    """
    orchestrator = ShipMateOrchestrator(
        repo_owner=repo_owner,
        repo_name=repo_name,
        branch=branch,
        github_token=current_user.github_token,
    )

    async def event_generator():
        try:
            # Run orchestrator and stream results as they complete
            async for agent_result in orchestrator.run_agents_streaming():
                # Format as SSE
                event_data = json.dumps(agent_result)
                yield f"data: {event_data}\n\n"
        except Exception as e:
            # Send error event
            error_event = json.dumps({
                "type": "error",
                "message": str(e),
            })
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
