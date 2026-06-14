"""Tests for the auto-fix SSE endpoint (routes/auto_fix.py).

We mock the two heavy collaborators — analyze (RepoAnalysisService +
ShipMateOrchestrator) and CoderOrchestrator.run_actuation — so the loop runs
deterministically with no network, Bedrock, or GitHub. The assertions are on
the SSE event sequence the AutoFixDrawer will consume.
"""
import json
import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

_TMP_DB = os.path.join(tempfile.gettempdir(), "shipmate_autofix_test.db")
os.environ["SHIPMATE_INFLIGHT_DB"] = _TMP_DB

from app.main import app  # noqa: E402
from app.services import inflight_registry as ir  # noqa: E402
from app.schemas.api_schemas import FindingPayload  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_db():
    ir.init_db()
    ir.reset_all()
    yield
    ir.reset_all()


def _parse_sse(text: str):
    """Pull the JSON objects out of an SSE response body."""
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


class _FakeResp:
    def __init__(self, status, pr_url=None):
        self.status = status
        self.pr_url = pr_url
        self.files_changed = []


def _patches(findings, actuate_status, pr_url=None):
    """Build the patch set: analyze returns a stub report, _pick_top_per_kind
    returns `findings`, run_actuation returns a fixed response."""
    fake_report = type("R", (), {"model_dump": lambda self: {"readiness_score": 77, "agents": {}}})()

    return [
        patch("app.services.repo_analysis_service.RepoAnalysisService.build_context",
              new=AsyncMock(return_value={"ctx": True})),
        patch("app.orchestrator.shipmate_orchestrator.ShipMateOrchestrator.run",
              return_value=fake_report),
        patch("scripts.coder_loop._pick_top_per_kind", side_effect=[findings, []]),
        patch("app.services.coder_orchestrator.CoderOrchestrator.run_actuation",
              new=AsyncMock(return_value=_FakeResp(actuate_status, pr_url))),
    ]


def _run(body):
    with client.stream("POST", "/api/auto-fix/start", json=body) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        return _parse_sse(resp.read().decode())


class TestAutoFixSSE:
    def test_happy_path_ships_a_pr(self):
        finding = FindingPayload(
            kind="guardrail", id="g1", title="Eval usage", description="d",
            file="app/x.py", severity="high",
        )
        ps = _patches([finding], "complete", pr_url="https://github.com/o/r/pull/1")
        for p in ps:
            p.start()
        try:
            events = _run({"owner": "o", "repo": "r", "branch": "main",
                           "access_token": "t", "rounds": 1})
        finally:
            for p in ps:
                p.stop()

        kinds = [e["event"] for e in events]
        assert kinds[0] == "loop.start"
        assert "analyze.start" in kinds
        assert "analyze.done" in kinds
        assert "finding.picked" in kinds
        assert "actuate.start" in kinds

        done = next(e for e in events if e["event"] == "actuate.done")
        assert done["status"] == "complete"
        assert done["pr_url"].endswith("/pull/1")

        loop_done = next(e for e in events if e["event"] == "loop.done")
        assert loop_done["good"] == 1
        assert loop_done["actuated"] == 1

    def test_rejected_patch_counts_as_skip(self):
        finding = FindingPayload(
            kind="blocker", id="b1", title="Some bug", description="d",
        )
        ps = _patches([finding], "pytest_rejected", pr_url=None)
        for p in ps:
            p.start()
        try:
            events = _run({"owner": "o", "repo": "r", "access_token": "t", "rounds": 1})
        finally:
            for p in ps:
                p.stop()

        done = next(e for e in events if e["event"] == "actuate.done")
        assert done["status"] == "pytest_rejected"
        assert done["pr_url"] is None
        loop_done = next(e for e in events if e["event"] == "loop.done")
        assert loop_done["good"] == 0

    def test_dry_round_stops_early(self):
        # _pick_top_per_kind returns [] immediately -> dry round.
        with patch("app.services.repo_analysis_service.RepoAnalysisService.build_context",
                   new=AsyncMock(return_value={})), \
             patch("app.orchestrator.shipmate_orchestrator.ShipMateOrchestrator.run",
                   return_value=type("R", (), {"model_dump": lambda s: {"readiness_score": 90, "agents": {}}})()), \
             patch("scripts.coder_loop._pick_top_per_kind", return_value=[]):
            events = _run({"owner": "o", "repo": "r", "access_token": "t", "rounds": 3})

        loop_done = next(e for e in events if e["event"] == "loop.done")
        assert "dry round" in loop_done.get("note", "")

    def test_missing_token_errors(self):
        events = _run({"owner": "o", "repo": "r", "access_token": "", "rounds": 1})
        assert any(e["event"] == "error" for e in events)
