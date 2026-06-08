"""Reports → PlanForge recurrence fix.

Pins the two mechanisms that stop milestones re-appearing every analyze run:
  • discover_plan_forge now suppresses dismissed/shipped MILESTONES (previously
    only blockers got journal suppression — milestones recurred forever).
  • _journaled_milestone_titles feeds shipped/dismissed/in_progress milestone
    titles to the discovery prompt as DO-NOT-PROPOSE.
"""
import os
import tempfile

import pytest

_TMP_DB = os.path.join(tempfile.gettempdir(), "shipmate_pf_recurrence_test.db")
os.environ["SHIPMATE_INFLIGHT_DB"] = _TMP_DB

from app.schemas.agent_schemas import (  # noqa: E402
    PlanForgeOutput, Milestone, Blocker,
)
from app.services import inflight_registry as ir  # noqa: E402
from app.services import finding_critic as fc  # noqa: E402
from app.services import llm_service  # noqa: E402
from app.services.llm_service import (  # noqa: E402
    LLMService, _journaled_milestone_titles, PlanForgeDiscovery,
    _DiscoveredMilestone, _DiscoveredBlocker,
)

REPO = "octo/widget"


@pytest.fixture(autouse=True)
def _clean_db():
    ir.init_db()
    ir.reset_all()
    yield
    ir.reset_all()


def _base():
    return PlanForgeOutput(
        milestones=[], blockers=[], dependencies=[],
        next_best_action="x", estimated_effort="1 day", delivery_score=70,
    )


def _ctx():
    return {
        "repo_info": {"owner": "octo", "name": "widget", "full_name": REPO},
        "file_tree": ["backend/app/main.py", "backend/app/services/x.py"],
        "key_files": {"backend/app/main.py": "print('hi')"},
        "branch": "main",
    }


class _FakeProvider:
    """Returns a fixed PlanForgeDiscovery; critic verify returns no refutations."""
    def __init__(self, discovery):
        self._disc = discovery

    def invoke_structured_sync(self, *, system_prompt, user_prompt, schema_class, deployment_hint="smart"):
        if schema_class is PlanForgeDiscovery:
            return self._disc
        # _CriticReport (verify_findings) — refute nothing.
        from app.services.finding_critic import _CriticReport
        return _CriticReport(verdicts=[])


def _patch_provider(monkeypatch, provider):
    monkeypatch.setattr(llm_service, "_get_provider", lambda: provider)


class TestMilestoneSuppression:
    def test_dismissed_milestone_is_suppressed(self, monkeypatch):
        # Discovery proposes a milestone the user already DISMISSED.
        disc = PlanForgeDiscovery(
            milestones=[_DiscoveredMilestone(
                title="Add a streaming endpoint", description="d",
                estimated_days=3, priority="high", category="feature",
                rationale="backend/app/main.py needs it",
            )],
            blockers=[],
        )
        # Journal it dismissed under the milestone namespace.
        sig = fc.finding_signature("milestone", "Add a streaming endpoint", None)
        ir.journal_set_state(sig, REPO, "dismissed")

        _patch_provider(monkeypatch, _FakeProvider(disc))
        out = LLMService.discover_plan_forge(_ctx(), _base())
        titles = [m.title for m in out.milestones]
        assert "Add a streaming endpoint" not in titles, "dismissed milestone must be suppressed"

    def test_fresh_milestone_survives(self, monkeypatch):
        disc = PlanForgeDiscovery(
            milestones=[_DiscoveredMilestone(
                title="Brand new milestone", description="d",
                estimated_days=2, priority="medium", category="feature",
                rationale="backend/app/main.py",
            )],
            blockers=[],
        )
        _patch_provider(monkeypatch, _FakeProvider(disc))
        out = LLMService.discover_plan_forge(_ctx(), _base())
        assert "Brand new milestone" in [m.title for m in out.milestones]


class TestJournaledMilestoneTitles:
    def test_collects_all_states_milestone_namespace(self):
        ir.journal_set_state(fc.finding_signature("milestone", "Shipped One", "a.py"), REPO, "shipped")
        ir.journal_set_state(fc.finding_signature("milestone", "Dismissed One", "b.py"), REPO, "dismissed")
        ir.journal_set_state(fc.finding_signature("milestone", "In Flight One", "c.py"), REPO, "in_progress")
        # A blocker + guardrail in the journal must NOT leak in.
        ir.journal_set_state(fc.finding_signature("blocker", "A Blocker", "d.py"), REPO, "shipped")
        ir.journal_set_state(fc.finding_signature("guardrail", "A Finding", "e.py"), REPO, "dismissed")

        titles = _journaled_milestone_titles({"repo_info": {"full_name": REPO}})
        low = [t.lower() for t in titles]
        assert "shipped one" in low
        assert "dismissed one" in low
        assert "in flight one" in low, "in_progress milestones must be excluded from re-proposal"
        assert not any("blocker" in t for t in low)
        assert not any("finding" in t for t in low)

    def test_empty_without_repo(self):
        assert _journaled_milestone_titles({}) == []
