"""Regression test for the decompose ↔ scope-guard interaction.

Live-run finding: an SSE milestone resolved its target paths to README.md
only, then the decomposer planned edits to analysis.py / orchestrator.py.
Because those files' ORIGINAL content was never fetched, each step got an
empty original and blind-rewrote the file — silently dropping the existing
_verify_repo_write_access auth guard. The scope guard couldn't catch it
(no original to diff against); only the pytest gate did (216 → 212).

The fix: _run_decomposed fetches the current content of every step-declared
path missing from target_files, AND mutates target_files in place so the
caller's downstream scope guard sees those originals. This test pins both.
"""
import asyncio

import pytest

from app.services import coder_orchestrator as co
from app.services import scope_guard as sg
from app.services.coder_orchestrator import CoderOrchestrator
from app.agents.coder_agent import CoderAgent, CoderOutput, CoderFile
from app.agents import decomposer as dmod
from app.agents.decomposer import Plan, PlanStep
from app.schemas.api_schemas import RepoLensSummary, FindingPayload


_ORIG_ANALYSIS = (
    "def _verify_repo_write_access(token, owner, repo):\n"
    "    # SEC-005 guard — must not be dropped\n"
    "    return True\n"
    "\n"
    "def analyze(req):\n"
    "    _verify_repo_write_access(req.token, req.owner, req.repo)\n"
    "    return {}\n"
)


class _Req:
    def __init__(self):
        self.owner = "o"
        self.repo = "r"
        self.branch = "b"
        self.access_token = "tok"
        self.finding = FindingPayload(
            kind="milestone", id="M", title="Stream SSE", description="d",
        )


@pytest.fixture
def _patched(monkeypatch):
    # Decomposer: one step editing a file the finding never resolved to.
    monkeypatch.setattr(
        dmod.Decomposer, "plan",
        lambda self, *a, **k: Plan(
            steps=[PlanStep(
                name="sse", task="switch to SSE",
                target_paths=["app/api/routes/analysis.py"], depends_on=[],
            )],
            summary="SSE streaming",
        ),
    )

    # Fetch returns the real original for analysis.py.
    async def fake_fetch(token, owner, repo, paths, ref=None):
        return {
            p: (_ORIG_ANALYSIS if p.endswith("analysis.py") else "")
            for p in paths
        }
    monkeypatch.setattr(co, "_fetch_current_contents", fake_fetch)

    # Coder blind-rewrites analysis.py, dropping the auth guard.
    seen_originals = {}

    def fake_run(self, brief, hint, mode="full"):
        seen_originals["analysis"] = brief.target_files.get(
            "app/api/routes/analysis.py", "")
        return CoderOutput(
            files=[CoderFile(
                path="app/api/routes/analysis.py",
                new_content="def analyze(req):\n    return {}\n",
                rationale="switch to SSE streaming",
            )],
            summary="sse",
        )
    monkeypatch.setattr(CoderAgent, "run", fake_run)
    return seen_originals


def test_step_receives_fetched_original(_patched):
    """The step's Coder brief must contain the REAL original content, so it
    edits rather than blind-rewrites."""
    tf = {}
    asyncio.run(CoderOrchestrator._run_decomposed(
        _Req(), RepoLensSummary(primary_language="Python"), [], tf, "full",
    ))
    assert "_verify_repo_write_access" in _patched["analysis"]


def test_target_files_mutated_for_downstream_guard(_patched):
    """_run_decomposed must populate target_files in place so the caller's
    scope guard has the originals."""
    tf = {}
    asyncio.run(CoderOrchestrator._run_decomposed(
        _Req(), RepoLensSummary(primary_language="Python"), [], tf, "full",
    ))
    assert "app/api/routes/analysis.py" in tf
    assert "_verify_repo_write_access" in tf["app/api/routes/analysis.py"]


def test_scope_guard_now_catches_dropped_guard(_patched):
    """End-to-end: with the original fetched, the scope guard flags the
    dropped auth function (the regression the pytest gate caught live)."""
    tf = {}
    out = asyncio.run(CoderOrchestrator._run_decomposed(
        _Req(), RepoLensSummary(primary_language="Python"), [], tf, "full",
    ))
    serialized = [
        {"path": cf.path, "new_content": cf.new_content, "rationale": cf.rationale}
        for cf in out.files
    ]
    issues = sg.check_patch(serialized, tf, out.summary)
    assert any("_verify_repo_write_access" in i for i in issues)
