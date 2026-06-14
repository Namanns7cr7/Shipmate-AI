"""Test the /actuate/stream SSE plumbing (OPP-006).

The pipeline itself is exercised elsewhere; here we only prove the route
bridges run_actuation's on_event callback into well-formed SSE frames, and that
auth failures surface as an `error` event (not a pre-stream HTTP error the
EventSource can't read)."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.coder_orchestrator import CoderOrchestrator

client = TestClient(app)

_BODY = {
    "owner": "o", "repo": "r", "branch": "main", "access_token": "t",
    "finding": {"kind": "guardrail", "id": "SEC-1", "title": "x", "description": "d"},
}


def _parse_sse(text: str):
    """Return list of (event, data-dict) from an SSE response body."""
    out = []
    for frame in text.split("\n\n"):
        if not frame.strip():
            continue
        event = None
        data = None
        for line in frame.split("\n"):
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if event:
            out.append((event, data))
    return out


def test_stream_emits_phase_events_then_done(monkeypatch):
    # Bypass GitHub auth check.
    async def ok_auth(owner, repo, token): return None
    monkeypatch.setattr("app.api.routes.actuate._verify_repo_write_access", ok_auth)

    # Fake run_actuation that drives a few events through on_event.
    async def fake_run(req, on_event=None):
        assert on_event is not None
        await on_event({"event": "actuate.start", "finding_id": req.finding.id})
        await on_event({"event": "coding.done", "files": ["a.py"]})
        await on_event({"event": "done", "status": "complete", "pr_url": "http://pr/1"})
        from app.schemas.api_schemas import ActuateResponse
        return ActuateResponse(status="complete", pr_url="http://pr/1", branch_name="b")

    monkeypatch.setattr(CoderOrchestrator, "run_actuation", classmethod(lambda cls, req, on_event=None: fake_run(req, on_event)))

    resp = client.post("/api/actuate/stream", json=_BODY)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(resp.text)
    names = [e for e, _ in events]
    assert "actuate.start" in names
    assert names[-1] == "done"
    done = events[-1][1]
    assert done["status"] == "complete"
    assert done["pr_url"] == "http://pr/1"


def test_stream_auth_failure_is_error_event(monkeypatch):
    from fastapi import HTTPException

    async def deny_auth(owner, repo, token):
        raise HTTPException(status_code=403, detail="no write access")
    monkeypatch.setattr("app.api.routes.actuate._verify_repo_write_access", deny_auth)

    resp = client.post("/api/actuate/stream", json=_BODY)
    assert resp.status_code == 200  # stream opens, error is in-band
    events = _parse_sse(resp.text)
    assert events, "expected at least one SSE frame"
    assert events[-1][0] == "error"
    assert "write access" in events[-1][1]["detail"]
