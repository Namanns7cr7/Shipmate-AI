"""Differential ValidationGate (A2).

The regression-only pass-count gate can't tell the loop whether a patch IMPROVED
coverage — only that it didn't regress. The differential layer adds a structured
before/after coverage measurement (overall % + passing tests) so the loop can
PRIORITIZE a patch that adds coverage over one that merely doesn't break things.

These tests pin the pure parsing + delta logic (fast, deterministic); the live
coverage run is exercised indirectly via the A1 synthesis test.
"""
import pytest

from app.services import validation_gate as vg


class TestCovTotalParsing:
    def test_parses_total_percent(self):
        out = "tests/test_x.py ....\n\nTOTAL    1200    444    63%\n\n12 passed in 3.2s"
        m = vg._COV_TOTAL_RE.search(out)
        assert m is not None
        assert int(m.group(1)) == 63

    def test_no_total_line_is_none(self):
        assert vg._COV_TOTAL_RE.search("12 passed in 1.0s") is None


class TestCoverageDelta:
    def _r(self, cov, passed, failed=0):
        return vg.CoverageResult(cov, passed, failed, "")

    def test_improved_when_coverage_rises(self):
        d = vg.CoverageDelta(self._r(60.0, 100), self._r(63.5, 100))
        assert d.coverage_delta == 3.5
        assert d.improved is True
        assert d.regressed is False

    def test_improved_when_tests_added_no_coverage_signal(self):
        # coverage unmeasured (-1) but a new passing test landed.
        d = vg.CoverageDelta(self._r(-1.0, 100), self._r(-1.0, 103))
        assert d.tests_delta == 3
        assert d.coverage_delta == 0.0  # no usable coverage numbers
        assert d.improved is True

    def test_regression_blocks_improved(self):
        # Coverage rose but a test was dropped → regressed wins, not improved.
        d = vg.CoverageDelta(self._r(60.0, 100), self._r(70.0, 98))
        assert d.regressed is True
        assert d.improved is False

    def test_flat_patch_is_not_improved(self):
        d = vg.CoverageDelta(self._r(60.0, 100), self._r(60.0, 100))
        assert d.improved is False
        assert d.regressed is False

    def test_as_dict_shape(self):
        d = vg.CoverageDelta(self._r(60.0, 100), self._r(62.0, 101))
        out = d.as_dict()
        assert out["coverage_delta"] == 2.0
        assert out["tests_delta"] == 1
        assert out["improved"] is True


class TestCoverageResultDefaults:
    def test_unmeasured_coverage_is_minus_one(self):
        r = vg.CoverageResult(-1.0, 0, 0, "no cov")
        assert r.coverage_pct == -1.0
        # An unmeasured-before delta is neutral, never falsely "improved".
        d = vg.CoverageDelta(r, vg.CoverageResult(-1.0, 0, 0, ""))
        assert d.improved is False
