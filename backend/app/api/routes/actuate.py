"""
POST /api/actuate — runs the Coder agent on a single finding and (optionally)
opens a PR back to the user's repo.

Stateless: the client passes the finding payload + minimal repo context
inline. No report cache lookup needed.
"""

import asyncio
import json
import logging

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.api_schemas import ActuateRequest, ActuateResponse
from app.services.coder_orchestrator import CoderOrchestrator
from app.api.deps import verify_repo_write_access as _verify_repo_write_access

router = APIRouter(tags=["actuate"])
logger = logging.getLogger("shipmate.actuate_route")


@router.post("/actuate", response_model=ActuateResponse)
async def actuate(req: ActuateRequest) -> ActuateResponse:
    if not req.owner or not req.repo:
        raise HTTPException(status_code=400, detail="owner and repo are required")
    if not req.access_token:
        raise HTTPException(status_code=400, detail="access_token is required")

    await _verify_repo_write_access(req.owner, req.repo, req.access_token)

    try:
        return await CoderOrchestrator.run_actuation(req)
    except httpx.HTTPStatusError as e:
        logger.warning("Actuate GitHub error: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        logger.exception("Actuate failed for %s/%s finding=%s",
                         req.owner, req.repo, req.finding.id)
        raise HTTPException(status_code=500, detail=f"Actuation failed: {e}") from e


@router.post("/actuate/stream")
async def actuate_stream(req: ActuateRequest):
    """SSE variant of /actuate (OPP-006). Streams per-phase progress events
    (resolve → coding → gate → branch → commit → pr → done) as the SAME
    run_actuation pipeline executes — no second code path, all gates intact.
    The terminal `done` event carries the final status + pr_url.

    Auth + the run itself happen inside the stream so a failure surfaces as an
    `error` event rather than a pre-stream HTTP error the EventSource can't read.
    """
    queue: asyncio.Queue = asyncio.Queue()
    _SENTINEL = object()

    async def on_event(evt: dict) -> None:
        await queue.put(evt)

    async def _drive() -> None:
        try:
            if not req.owner or not req.repo or not req.access_token:
                await queue.put({"event": "error", "detail": "owner, repo, access_token required"})
                return
            await _verify_repo_write_access(req.owner, req.repo, req.access_token)
            await CoderOrchestrator.run_actuation(req, on_event=on_event)
        except HTTPException as e:
            await queue.put({"event": "error", "detail": str(e.detail), "status_code": e.status_code})
        except httpx.HTTPStatusError as e:
            await queue.put({"event": "error", "detail": f"GitHub error: {e}"})
        except Exception as e:
            logger.exception("actuate_stream failed for %s/%s", req.owner, req.repo)
            await queue.put({"event": "error", "detail": f"Actuation failed: {e}"})
        finally:
            await queue.put(_SENTINEL)

    async def _event_source():
        task = asyncio.create_task(_drive())
        try:
            while True:
                item = await queue.get()
                if item is _SENTINEL:
                    break
                yield f"event: {item.get('event', 'message')}\ndata: {json.dumps(item)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        _event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
