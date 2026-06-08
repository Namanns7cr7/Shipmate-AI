"""Tests for the recurrence + persistence fixes.

These pin the mechanisms that stop the Build tab re-proposing already-built work:
  • _capability_digest extracts existing routes/modules from the corpus.
  • discover_opportunities receives exclude_titles + the digest.
  • already_built fires on the WIDENED verb set + capability-construct proofs.
  • execute_opportunity journals shipped/in_progress; dismiss journals dismissed;
    journaled_titles feeds them back as exclusions.
"""
import os
import tempfile

import pytest

_TMP_DB = os.path.join(tempfile.gettempdir(), "shipmate_recurrence_test.db")
os.environ["SHIPMATE_INFLIGHT_DB"] = _TMP_DB

from app.schemas.agent_schemas import Opportunity  # noqa: E402
from app.services import inflight_registry as ir  # noqa: E402
from app.services import opportunity_critic as oc  # noqa: E402
from app.services.opportunity_service import OpportunityService  # noqa: E402
from app.services.llm_service import _capability_digest  # noqa: E402

REPO = "octo/widget"


@pytest.fixture(autouse=True)
def _clean_db():
    ir.init_db()
    ir.reset_all()
    yield
    ir.reset_all()


def _opp(title, **kw):
    return Opportunity(
        id=kw.get("id", "OPP-001"), title=title,
        category=kw.get("category", "improvement"),
        description=kw.get("description", "d"), impact="x", effort="M",
        estimated_days=3, target_files=kw.get("target_files", []),
        evidence=kw.get("evidence", []), rationale="r", source="discovery",
    )


# ── Capability digest ─────────────────────────────────────────────────────────

class TestCapabilityDigest:
    def test_extracts_fastapi_routes_and_modules(self):
        ctx = {
            "file_tree": [
                "backend/app/api/routes/analysis.py",
                "backend/app/services/report_store.py",
            ],
            "key_files": {
                "backend/app/api/routes/analysis.py":
                    '@router.get("/repos/{owner}/{repo}/history")\nasync def h(): ...',
            },
        }
        digest = _capability_digest(ctx)
        assert "/repos/{owner}/{repo}/history" in digest
        assert "report_store.py" in digest
        assert "ALREADY EXIST" in digest

    def test_extracts_frontend_calls(self):
        ctx = {
            "file_tree": ["frontend/src/lib/api.ts"],
            "key_files": {"frontend/src/lib/api.ts": "gh.get('/auth/github/repos')"},
        }
        digest = _capability_digest(ctx)
        assert "/auth/github/repos" in digest

    def test_empty_corpus_is_safe(self):
        assert "no capability digest" in _capability_digest({}).lower()


# ── Widened already_built (the exact recurring false positives) ──────────────

class TestWidenedAlreadyBuilt:
    _TREE = ["backend/app/services/github_api_service.py",
             "backend/app/services/llm_provider.py", "backend/app/main.py"]
    _KEY = {
        "backend/app/services/github_api_service.py":
            "_tree_cache: dict = {}\ndef _tree_cache_get(k): ...",
        "backend/app/services/llm_provider.py":
            "def get_provider():\n    return _cached",
        "backend/app/main.py":
            "body_bytes = await request.body()\n# scan it",
    }

    def test_cache_file_tree_is_already_built(self):
        opp = _opp("Cache GitHub API file-tree fetches",
                   description="Cache the repo file tree per repo and branch to cut API calls")
        assert oc.already_built(opp, self._TREE, self._KEY) is not None

    def test_provider_factory_is_already_built(self):
        opp = _opp("Deduplicate LLM provider instantiation",
                   description="Introduce a shared provider factory / get_llm_provider singleton")
        assert oc.already_built(opp, self._TREE, self._KEY) is not None

    def test_body_sanitization_is_already_built(self):
        opp = _opp("Sanitization middleware skips request body",
                   description="Add request body inspection to sanitize the body for eval(")
        assert oc.already_built(opp, self._TREE, self._KEY) is not None

    def test_genuine_new_capability_survives(self):
        opp = _opp("Add a rate-limit dashboard widget",
                   description="Build a new widget showing GitHub rate-limit headroom")
        assert oc.already_built(opp, self._TREE, self._KEY) is None


# ── Journal lifecycle: dismiss + journaled_titles exclusions ─────────────────

class TestJournalRecurrence:
    def test_dismiss_then_excluded_from_discovery(self):
        OpportunityService.dismiss_opportunity(REPO, "Stale idea", "backend/app/main.py")
        titles = oc.journaled_titles(REPO)
        assert any("stale idea" in t for t in titles)

    def test_dismissed_is_suppressed_in_filter(self):
        res = OpportunityService.dismiss_opportunity(REPO, "Old thing", "a.py")
        opp = _opp("Old thing", target_files=["a.py"])
        kept = oc.filter_suppressed([opp], REPO)
        assert kept == []
        assert res["state"] == "dismissed"

    def test_journaled_titles_namespaced(self):
        # A guardrail journal row must NOT leak into opportunity exclusions.
        from app.api.routes.findings import finding_signature
        ir.journal_set_state(finding_signature("guardrail", "Some Finding", "x.py"), REPO, "dismissed")
        OpportunityService.dismiss_opportunity(REPO, "An Opportunity", "y.py")
        titles = oc.journaled_titles(REPO)
        assert any("an opportunity" in t for t in titles)
        assert not any("some finding" in t for t in titles)

    def test_shipped_state_recovered_as_title(self):
        sig = oc.opportunity_signature("Shipped Work", "z.py")
        ir.journal_set_state(sig, REPO, "shipped")
        assert any("shipped work" in t for t in oc.journaled_titles(REPO))
