"""TestPilot → Coder → ValidationGate synthesis loop (A1).

Turns a TestPilot suggestion (prose) into a REAL test file and verifies it is a
genuine artifact: collectable + passing + coverage-adding. Only a verified test
becomes accepted (PR-able). These tests inject a stub Coder and stub the
coverage measurement so the orchestration logic is exercised hermetically — no
Bedrock, no live pytest run.
"""
import pytest

from app.schemas.agent_schemas import SuggestedTest
from app.services import test_synthesizer as ts
from app.services import validation_gate as vg


def _suggestion(name="test_analyze_rejects_blank_owner", target="backend/app/api/routes/analysis.py"):
    return SuggestedTest(
        name=name, type="unit", priority="high",
        description="Verify /analyze returns 400 when owner is blank.",
        target_file=target, source="discovery",
        rationale="analysis.py:45 raises 400 on missing owner; the branch is untested.",
    )


def _coder_returns(path, content="def test_x():\n    assert 1 == 1\n"):
    def fn(finding):
        return [{"path": path, "new_content": content, "rationale": "covers the gap"}]
    return fn


def _stub_delta(monkeypatch, *, before_pass, after_pass, cov_before, cov_after):
    """Make measure_coverage_delta return a controlled CoverageDelta + a no-op
    snapshot, so we test the accept/reject logic without running pytest."""
    before = vg.CoverageResult(cov_before, before_pass, 0, "")
    after = vg.CoverageResult(cov_after, after_pass, 0, "")
    delta = vg.CoverageDelta(before, after)
    monkeypatch.setattr(vg, "measure_coverage_delta", lambda files, **kw: (delta, {}))
    # restore_snapshot is a no-op here (empty snapshot), but stub it to be safe.
    monkeypatch.setattr(vg, "restore_snapshot", lambda snap: None)


class TestSuggestionToFinding:
    def test_maps_to_test_kind_finding(self):
        f = ts.suggestion_to_finding(_suggestion())
        assert f.kind == "test"
        assert f.category == "testing"
        assert f.file == "backend/app/api/routes/analysis.py"
        assert "REAL, executable test" in f.description
        assert f.title == "test_analyze_rejects_blank_owner"


class TestVerificationBranches:
    def test_accepts_passing_coverage_adding_test(self, monkeypatch):
        _stub_delta(monkeypatch, before_pass=100, after_pass=101,
                    cov_before=60.0, cov_after=61.5)
        res = ts.synthesize_and_verify(
            _suggestion(), _coder_returns("backend/tests/test_analysis_blank.py"),
        )
        assert res.accepted is True
        assert res.test_path == "backend/tests/test_analysis_blank.py"
        assert res.coverage_delta["coverage_delta"] == 1.5

    def test_rejects_when_no_test_file_produced(self, monkeypatch):
        # Coder returned a non-test file only.
        res = ts.synthesize_and_verify(
            _suggestion(), _coder_returns("backend/app/main.py"),
        )
        assert res.accepted is False
        assert "no test file" in res.reason

    def test_rejects_regression(self, monkeypatch):
        _stub_delta(monkeypatch, before_pass=100, after_pass=98,
                    cov_before=60.0, cov_after=60.0)
        res = ts.synthesize_and_verify(
            _suggestion(), _coder_returns("backend/tests/test_x.py"),
        )
        assert res.accepted is False
        assert "regressed" in res.reason

    def test_rejects_when_test_did_not_run(self, monkeypatch):
        # Passing count unchanged → the test errored on collection / was skipped.
        _stub_delta(monkeypatch, before_pass=100, after_pass=100,
                    cov_before=60.0, cov_after=60.0)
        res = ts.synthesize_and_verify(
            _suggestion(), _coder_returns("backend/tests/test_x.py"),
        )
        assert res.accepted is False
        assert "did not add a passing test" in res.reason

    def test_rejects_passing_but_no_coverage_gain(self, monkeypatch):
        # New passing test but coverage flat AND measurable → retests covered code.
        _stub_delta(monkeypatch, before_pass=100, after_pass=101,
                    cov_before=60.0, cov_after=60.0)
        res = ts.synthesize_and_verify(
            _suggestion(), _coder_returns("backend/tests/test_x.py"),
        )
        assert res.accepted is False
        assert "no coverage" in res.reason

    def test_accepts_when_coverage_unmeasurable_but_test_added(self, monkeypatch):
        # cov=-1 (couldn't measure) must NOT be treated as "no value".
        _stub_delta(monkeypatch, before_pass=100, after_pass=101,
                    cov_before=-1.0, cov_after=-1.0)
        res = ts.synthesize_and_verify(
            _suggestion(), _coder_returns("backend/tests/test_x.py"),
        )
        assert res.accepted is True

    def test_require_coverage_gain_false_accepts_flat(self, monkeypatch):
        _stub_delta(monkeypatch, before_pass=100, after_pass=101,
                    cov_before=60.0, cov_after=60.0)
        res = ts.synthesize_and_verify(
            _suggestion(), _coder_returns("backend/tests/test_x.py"),
            require_coverage_gain=False,
        )
        assert res.accepted is True

    def test_coder_exception_is_reported(self, monkeypatch):
        def boom(finding):
            raise RuntimeError("bedrock down")
        res = ts.synthesize_and_verify(_suggestion(), boom)
        assert res.accepted is False
        assert "coder failed" in res.reason


class TestSynthesizeTop:
    def test_stops_at_first_accepted(self, monkeypatch):
        _stub_delta(monkeypatch, before_pass=100, after_pass=101,
                    cov_before=60.0, cov_after=62.0)
        suggestions = [_suggestion(name=f"test_case_{i}") for i in range(3)]
        results = ts.synthesize_top(
            suggestions, _coder_returns("backend/tests/test_case.py"),
        )
        # First one accepted → stop; only one result.
        assert len(results) == 1
        assert results[0].accepted is True

    def test_tries_all_when_none_accepted(self, monkeypatch):
        _stub_delta(monkeypatch, before_pass=100, after_pass=100,
                    cov_before=60.0, cov_after=60.0)  # never adds a test
        suggestions = [_suggestion(name=f"test_case_{i}") for i in range(3)]
        results = ts.synthesize_top(
            suggestions, _coder_returns("backend/tests/test_case.py"),
            max_attempts=3,
        )
        assert len(results) == 3
        assert all(not r.accepted for r in results)
