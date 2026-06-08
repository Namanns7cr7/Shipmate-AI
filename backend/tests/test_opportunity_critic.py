"""Tests for opportunity_critic — the Phase-1A quality gate.

Covers the three deterministic responsibilities:
  1. GROUND — evidence/target_files must cite real repo paths.
  2. SUPPRESS — dismissed/shipped opportunities are filtered, and the
     `opportunity::` namespace does NOT cross-suppress guardrail/blocker sigs
     (the signature-prefix concern from the design review).
  3. RANK — value scoring, in_progress downranking, ungrounded drop.
"""
import os
import tempfile

import pytest

# Throwaway inflight DB before importing anything that opens it.
_TMP_DB = os.path.join(tempfile.gettempdir(), "shipmate_oppcritic_test.db")
os.environ["SHIPMATE_INFLIGHT_DB"] = _TMP_DB

from app.schemas.agent_schemas import Opportunity  # noqa: E402
from app.services import inflight_registry as ir  # noqa: E402
from app.services import opportunity_critic as oc  # noqa: E402
from app.api.routes.findings import finding_signature  # noqa: E402

REPO = "owner/repo"

FILE_TREE = [
    "backend/app/main.py",
    "backend/app/services/repo_analysis_service.py",
    "frontend/src/lib/api.ts",
    "frontend/src/App.tsx",
]


@pytest.fixture(autouse=True)
def _clean_db():
    ir.init_db()
    ir.reset_all()
    yield
    ir.reset_all()


def _opp(title, *, category="improvement", effort="M", evidence=None,
         target_files=None, impact="makes things better", days=3):
    return Opportunity(
        id="OPP-000", title=title, category=category,
        description="d", impact=impact, effort=effort, estimated_days=days,
        target_files=target_files or [], evidence=evidence or [],
        rationale="because", source="discovery",
    )


# ── Grounding ────────────────────────────────────────────────────────────────

class TestGrounding:
    def test_real_evidence_path_is_grounded(self):
        o = _opp("Cache file tree",
                 evidence=["backend/app/services/repo_analysis_service.py:_fetch_files — no cache"])
        oc.ground_opportunities([o], FILE_TREE, {})
        assert o.grounded is True

    def test_basename_suffix_match_is_grounded(self):
        # Evidence cites just the filename; tree has the full path.
        o = _opp("Extract axios client", evidence=["api.ts duplicates headers"])
        oc.ground_opportunities([o], FILE_TREE, {})
        assert o.grounded is True

    def test_fake_path_is_not_grounded(self):
        o = _opp("Rewrite the universe",
                 evidence=["backend/app/services/does_not_exist.py:foo"])
        oc.ground_opportunities([o], FILE_TREE, {})
        assert o.grounded is False

    def test_bare_function_name_not_grounded(self):
        # Not path-shaped -> can't verify -> not grounded.
        o = _opp("Vague thing", evidence=["some_function"])
        oc.ground_opportunities([o], FILE_TREE, {})
        assert o.grounded is False

    def test_target_files_count_as_evidence(self):
        o = _opp("Touch main", evidence=[], target_files=["backend/app/main.py"])
        oc.ground_opportunities([o], FILE_TREE, {})
        assert o.grounded is True

    def test_failopen_when_no_tree(self):
        o = _opp("anything", evidence=["whatever/fake.py"])
        oc.ground_opportunities([o], [], {})
        assert o.grounded is True  # can't disprove -> keep


# ── Suppression (namespaced) ─────────────────────────────────────────────────

class TestSuppression:
    def test_dismissed_opportunity_is_filtered(self):
        o = _opp("Cache file tree", target_files=["backend/app/main.py"])
        sig = oc.opportunity_signature(o.title, "backend/app/main.py")
        ir.journal_set_state(sig, REPO, "dismissed")
        kept = oc.filter_suppressed([o], REPO)
        assert kept == []

    def test_fresh_opportunity_survives(self):
        o = _opp("Brand new idea", target_files=["frontend/src/App.tsx"])
        kept = oc.filter_suppressed([o], REPO)
        assert len(kept) == 1

    def test_guardrail_sig_does_not_cross_suppress_opportunity(self):
        """THE design-review concern: a dismissed guardrail finding whose
        title/file collide with an opportunity must NOT suppress it, because
        the namespaces differ (`guardrail::` vs `opportunity::`)."""
        title = "Eval usage"
        file = "backend/app/main.py"
        # Dismiss a GUARDRAIL finding with the same title+file.
        ir.journal_set_state(finding_signature("guardrail", title, file), REPO, "dismissed")
        # The opportunity with identical title+file must survive.
        o = _opp(title, target_files=[file])
        kept = oc.filter_suppressed([o], REPO)
        assert len(kept) == 1, "guardrail dismissal leaked into opportunity namespace"

    def test_suppressed_set_is_opportunity_namespaced(self):
        ir.journal_set_state(finding_signature("blocker", "X", "y.py"), REPO, "shipped")
        ir.journal_set_state(oc.opportunity_signature("Z", "y.py"), REPO, "shipped")
        sigs = oc.suppressed_opportunity_signatures(REPO)
        assert all(s.startswith("opportunity::") for s in sigs)
        assert oc.opportunity_signature("Z", "y.py") in sigs


# ── Ranking ──────────────────────────────────────────────────────────────────

class TestRanking:
    def test_drops_ungrounded_by_default(self):
        good = _opp("Real", target_files=["backend/app/main.py"])
        bad = _opp("Fake", evidence=["nope/ghost.py"])
        oc.ground_opportunities([good, bad], FILE_TREE, {})
        ranked = oc.rank_opportunities([good, bad], REPO)
        titles = [o.title for o in ranked]
        assert "Real" in titles and "Fake" not in titles

    def test_keeps_ungrounded_when_flagged(self):
        bad = _opp("Fake", evidence=["nope/ghost.py"])
        oc.ground_opportunities([bad], FILE_TREE, {})
        ranked = oc.rank_opportunities([bad], REPO, drop_ungrounded=False)
        assert len(ranked) == 1

    def test_small_effort_outranks_large_same_category(self):
        small = _opp("Small win", category="improvement", effort="S",
                     target_files=["backend/app/main.py"])
        large = _opp("Big win", category="improvement", effort="L",
                     target_files=["backend/app/main.py"])
        oc.ground_opportunities([small, large], FILE_TREE, {})
        ranked = oc.rank_opportunities([small, large], REPO)
        assert ranked[0].title == "Small win"

    def test_inprogress_is_downranked(self):
        # Two equal opportunities; mark one in_progress -> it should rank lower.
        a = _opp("Idea A", category="improvement", effort="S",
                 target_files=["backend/app/main.py"])
        b = _opp("Idea B", category="improvement", effort="S",
                 target_files=["frontend/src/App.tsx"])
        oc.ground_opportunities([a, b], FILE_TREE, {})
        sig_a = oc.opportunity_signature("Idea A", "backend/app/main.py")
        ir.journal_set_state(sig_a, REPO, "in_progress")
        ranked = oc.rank_opportunities([a, b], REPO)
        # B (fresh) should now outrank A (in_progress) despite equal base value.
        assert ranked[0].title == "Idea B"
        a_ranked = next(o for o in ranked if o.title == "Idea A")
        assert a_ranked.journal_state == "in_progress"

    def test_priority_derived_from_score(self):
        o = _opp("Grounded bug", category="bug", effort="S",
                 impact="fixes a crash and data loss",
                 evidence=["backend/app/main.py", "frontend/src/api.ts"],
                 target_files=["backend/app/main.py"])
        oc.ground_opportunities([o], FILE_TREE, {})
        ranked = oc.rank_opportunities([o], REPO)
        assert ranked[0].value_score >= 55
        assert ranked[0].priority in ("high", "critical")

    def test_ids_reassigned_in_rank_order(self):
        small = _opp("Small", category="bug", effort="S",
                     target_files=["backend/app/main.py"])
        large = _opp("Large", category="tweak", effort="L",
                     target_files=["frontend/src/App.tsx"])
        oc.ground_opportunities([small, large], FILE_TREE, {})
        ranked = oc.rank_opportunities([small, large], REPO)
        assert ranked[0].id == "OPP-001"
        assert ranked[1].id == "OPP-002"
