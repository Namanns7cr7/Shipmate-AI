"""Tests for finding_critic: journal suppression, the critic verifier pass,
and the fix-resolution check.
"""
import os

import pytest

from app.services import finding_critic as fc
from app.schemas.agent_schemas import SecurityFinding, Severity


def _finding(title, category="injection", file="x.py"):
    return SecurityFinding(
        id="SEC-001", title=title, severity=Severity.HIGH,
        category=category, description="d", recommendation="r", file=file,
    )


# ── Signature (must match the rest of the system) ─────────────────────────────

def test_signature_format():
    assert fc.finding_signature("guardrail", "Title Here", "a/b.py") == \
        "guardrail::title here::a/b.py"

def test_signature_caps_title_and_lowercases():
    sig = fc.finding_signature("k", "X" * 200, "F.PY")
    kind, title, file = sig.split("::")
    assert len(title) == 80 and file == "f.py"


# ── Suppression ───────────────────────────────────────────────────────────────

class TestSuppression:
    def test_dismissed_finding_is_filtered(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SHIPMATE_INFLIGHT_DB", str(tmp_path / "ir.db"))
        from app.services import inflight_registry as ir
        # fresh connection for the temp DB
        if hasattr(ir, "_local"):
            try:
                ir._local.__dict__.clear()
            except Exception:
                pass

        keep = _finding("Real secret leak", category="secrets", file="cfg.py")
        drop = _finding("Dynamic code execution detected")
        sig = fc.finding_signature("guardrail", drop.title, drop.file)
        ir.journal_set_state(sig, "acme/widget", "dismissed")

        out = fc.filter_suppressed([drop, keep], "guardrail", "acme/widget")
        titles = [f.title for f in out]
        assert "Dynamic code execution detected" not in titles
        assert "Real secret leak" in titles

    def test_no_repo_suppresses_nothing(self):
        fs = [_finding("A"), _finding("B")]
        assert fc.filter_suppressed(fs, "guardrail", "") == fs


# ── Critic verifier ───────────────────────────────────────────────────────────

class _FakeProvider:
    """Stand-in provider whose verifier refutes a fixed set of titles."""
    def __init__(self, refute_titles):
        self.refute = {t.lower() for t in refute_titles}

    def invoke_structured_sync(self, system_prompt, user_prompt, schema_class, deployment_hint="smart"):
        # Build verdicts from the finding titles present in the prompt listing.
        verdicts = []
        for line in user_prompt.splitlines():
            for title in ("False positive finding", "Genuine finding"):
                if title in line:
                    verdicts.append({"title": title, "is_real": title.lower() not in self.refute, "reason": "test"})
        return schema_class.model_validate({"verdicts": verdicts})


class TestCriticPass:
    def test_refuted_finding_dropped(self, monkeypatch):
        monkeypatch.setenv("SHIPMATE_FINDING_CRITIC", "1")
        # reload module so the env flag is re-read
        import importlib
        importlib.reload(fc)
        provider = _FakeProvider(refute_titles=["False positive finding"])
        findings = [_finding("False positive finding"), _finding("Genuine finding")]
        out = fc.verify_findings(findings, "some code blob", provider)
        titles = [f.title for f in out]
        assert "False positive finding" not in titles
        assert "Genuine finding" in titles

    def test_disabled_keeps_all(self, monkeypatch):
        monkeypatch.setenv("SHIPMATE_FINDING_CRITIC", "0")
        import importlib
        importlib.reload(fc)
        provider = _FakeProvider(refute_titles=["False positive finding"])
        findings = [_finding("False positive finding")]
        out = fc.verify_findings(findings, "code", provider)
        assert len(out) == 1  # critic off -> nothing dropped
        monkeypatch.setenv("SHIPMATE_FINDING_CRITIC", "1")
        importlib.reload(fc)

    def test_no_provider_is_failopen(self):
        findings = [_finding("anything")]
        assert fc.verify_findings(findings, "code", None) == findings


# ── Fix-resolution check ──────────────────────────────────────────────────────

class TestResolutionCheck:
    def test_injection_still_present_is_unresolved(self):
        assert fc.is_finding_resolved("injection", ["def f(x): return eval(x)"]) is False

    def test_injection_removed_is_resolved(self):
        assert fc.is_finding_resolved("injection", ["def f(x): return int(x)"]) is True

    def test_injection_in_comment_is_resolved(self):
        # a comment mentioning eval( is not a live call
        assert fc.is_finding_resolved("injection", ["# never call eval(x) here\nreturn int(x)"]) is True

    def test_secret_still_present_is_unresolved(self):
        assert fc.is_finding_resolved("secrets", ['api_key = "abcd1234efgh"']) is False

    def test_unknown_category_returns_none(self):
        assert fc.is_finding_resolved("architecture", ["whatever"]) is None
