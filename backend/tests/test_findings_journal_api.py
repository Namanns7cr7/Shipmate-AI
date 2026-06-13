"""Tests for the finding-journal API (routes/findings.py).

Covers the CRUD endpoints AND the critical parity invariant: the route's
finding_signature() must produce byte-identical signatures to
coder_orchestrator._finding_signature, or a finding actuated from the loop
won't map to the same journal row the UI dismisses.
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Point the inflight DB at a throwaway file BEFORE importing anything that
# opens it, so these tests never touch the real /tmp/shipmate_inflight.db.
_TMP_DB = os.path.join(tempfile.gettempdir(), "shipmate_findings_test.db")
os.environ["SHIPMATE_INFLIGHT_DB"] = _TMP_DB

from app.main import app  # noqa: E402
from app.services import inflight_registry as ir  # noqa: E402
from app.api.routes.findings import finding_signature  # noqa: E402

client = TestClient(app)

REPO = "owner/repo"


@pytest.fixture(autouse=True)
def _clean_db():
    ir.init_db()
    ir.reset_all()
    yield
    ir.reset_all()


class TestSignatureParity:
    def test_matches_orchestrator_formula(self):
        from app.services.coder_orchestrator import _finding_signature
        from app.schemas.api_schemas import FindingPayload

        f = FindingPayload(
            id="x", kind="blocker", title="Some Bug In The Code", severity="high",
            description="d", file="backend/app/main.py",
        )
        assert finding_signature(f.kind, f.title, f.file) == _finding_signature(f)

    def test_matches_loop_formula(self):
        # The loop's helper takes (kind, title, file_hint) positionally — same
        # formula, different call shape. Parity is what matters.
        from scripts.coder_loop import _finding_signature as loop_sig

        assert (
            finding_signature("guardrail", "CORS Misconfiguration", "app/main.py")
            == loop_sig("guardrail", "CORS Misconfiguration", "app/main.py")
        )

    def test_title_is_lowercased_and_capped(self):
        long_title = "A" * 200
        sig = finding_signature("blocker", long_title, "f.py")
        # kind::<=80 chars::file
        middle = sig.split("::")[1]
        assert len(middle) == 80
        assert middle == "a" * 80


class TestJournalEndpoints:
    def test_dismiss_then_journal_lists_it(self):
        resp = client.post("/api/findings/dismiss", json={
            "kind": "guardrail", "title": "Eval usage", "file": "app/x.py",
            "repo_full_name": REPO,
        })
        assert resp.status_code == 200
        sig = resp.json()["signature"]
        assert resp.json()["state"] == "dismissed"

        j = client.get("/api/findings/journal", params={"repo": REPO}).json()
        assert sig in j["state_map"]
        assert j["state_map"][sig] == "dismissed"

    def test_state_filter(self):
        client.post("/api/findings/dismiss", json={
            "kind": "blocker", "title": "Bug A", "file": "a.py", "repo_full_name": REPO,
        })
        # in_progress one
        ir.journal_set_state(
            finding_signature("blocker", "Bug B", "b.py"), REPO, "in_progress",
        )
        dismissed = client.get(
            "/api/findings/journal", params={"repo": REPO, "state": "dismissed"},
        ).json()
        states = {r["state"] for r in dismissed["rows"]}
        assert states == {"dismissed"}

    def test_reopen_deletes_row(self):
        client.post("/api/findings/dismiss", json={
            "kind": "blocker", "title": "Bug C", "file": "c.py", "repo_full_name": REPO,
        })
        resp = client.post("/api/findings/reopen", json={
            "kind": "blocker", "title": "Bug C", "file": "c.py", "repo_full_name": REPO,
        })
        assert resp.status_code == 200
        assert resp.json()["state"] == "fresh"
        j = client.get("/api/findings/journal", params={"repo": REPO}).json()
        assert resp.json()["signature"] not in j["state_map"]

    def test_reopen_rejects_non_dismissed(self):
        sig = finding_signature("blocker", "In Flight", "d.py")
        ir.journal_set_state(sig, REPO, "in_progress")
        resp = client.post("/api/findings/reopen", json={
            "kind": "blocker", "title": "In Flight", "file": "d.py", "repo_full_name": REPO,
        })
        assert resp.status_code == 409

    def test_signature_endpoint(self):
        resp = client.post("/api/findings/signature", json={
            "kind": "blocker", "title": "Hi", "file": "f.py",
        })
        assert resp.json()["signature"] == "blocker::hi::f.py"
