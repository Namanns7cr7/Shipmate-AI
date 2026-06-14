"""Tests for OpportunityService — the discover→ground→suppress→rank pipeline.

The LLM discovery call is mocked, so these run offline and deterministically.
They verify the service wires the critic correctly: ungrounded picks drop,
journal-dismissed picks are filtered, and the response metadata is accurate.
"""
import os
import tempfile

import pytest

_TMP_DB = os.path.join(tempfile.gettempdir(), "shipmate_oppservice_test.db")
os.environ["SHIPMATE_INFLIGHT_DB"] = _TMP_DB

from app.schemas.agent_schemas import Opportunity  # noqa: E402
from app.services import inflight_registry as ir  # noqa: E402
from app.services import opportunity_critic as oc  # noqa: E402
from app.services.opportunity_service import OpportunityService  # noqa: E402
from app.services.llm_service import LLMService  # noqa: E402

REPO = "octo/widget"


@pytest.fixture(autouse=True)
def _clean_db():
    ir.init_db()
    ir.reset_all()
    yield
    ir.reset_all()


def _context():
    return {
        "repo_info": {
            "owner": "octo", "name": "widget", "full_name": REPO,
            "description": "x", "language": "Python",
        },
        "file_tree": [
            "backend/app/main.py",
            "backend/app/services/repo_analysis_service.py",
            "frontend/src/lib/api.ts",
        ],
        "key_files": {"backend/app/main.py": "print('hi')\n"},
        "branch": "main",
    }


def _opp(title, **kw):
    return Opportunity(
        id="OPP-000", title=title, category=kw.get("category", "improvement"),
        description="d", impact=kw.get("impact", "better"),
        effort=kw.get("effort", "M"), estimated_days=kw.get("days", 3),
        target_files=kw.get("target_files", []), evidence=kw.get("evidence", []),
        rationale="r", source="discovery",
    )


def _patch_discovery(monkeypatch, opps, available=True):
    monkeypatch.setattr(LLMService, "discover_opportunities",
                        classmethod(lambda cls, ctx, max_opportunities=8, exclude_titles=None: list(opps)))
    monkeypatch.setattr(LLMService, "is_available", classmethod(lambda cls: available))


class TestBuildPlan:
    def test_empty_when_provider_unavailable(self, monkeypatch):
        _patch_discovery(monkeypatch, [], available=False)
        plan = OpportunityService.build_plan(_context())
        assert plan.opportunities == []
        assert plan.ai_enhanced is False
        assert plan.total_found == 0

    def test_grounded_opportunity_survives_and_ranks(self, monkeypatch):
        opps = [
            _opp("Cache file tree", category="improvement", effort="S",
                 impact="reduces GitHub API calls and latency",
                 target_files=["backend/app/services/repo_analysis_service.py"],
                 evidence=["backend/app/services/repo_analysis_service.py:_fetch_files"]),
        ]
        _patch_discovery(monkeypatch, opps)
        plan = OpportunityService.build_plan(_context())
        assert plan.total_found == 1
        assert plan.grounded_count == 1
        assert len(plan.opportunities) == 1
        assert plan.opportunities[0].id == "OPP-001"
        assert plan.opportunities[0].grounded is True
        assert plan.opportunities[0].value_score > 0

    def test_ungrounded_dropped_but_counted(self, monkeypatch):
        opps = [
            _opp("Real", target_files=["backend/app/main.py"]),
            _opp("Hallucinated", evidence=["backend/app/ghost_module.py:foo"]),
        ]
        _patch_discovery(monkeypatch, opps)
        plan = OpportunityService.build_plan(_context())
        assert plan.total_found == 2
        assert plan.grounded_count == 1
        titles = [o.title for o in plan.opportunities]
        assert titles == ["Real"]

    def test_dismissed_is_suppressed(self, monkeypatch):
        opps = [_opp("Stale idea", target_files=["backend/app/main.py"])]
        sig = oc.opportunity_signature("Stale idea", "backend/app/main.py")
        ir.journal_set_state(sig, REPO, "dismissed")
        _patch_discovery(monkeypatch, opps)
        plan = OpportunityService.build_plan(_context())
        assert plan.opportunities == []

    def test_include_ungrounded_keeps_them(self, monkeypatch):
        opps = [_opp("Hallucinated", evidence=["backend/app/ghost.py:foo"])]
        _patch_discovery(monkeypatch, opps)
        plan = OpportunityService.build_plan(_context(), include_ungrounded=True)
        assert len(plan.opportunities) == 1
        assert plan.opportunities[0].grounded is False
