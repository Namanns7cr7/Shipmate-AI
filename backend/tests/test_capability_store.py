"""Capability posture persistence + drift detection (B3).

`_detect_security_controls` recomputed the "controls this repo already has" set
every run and threw it away, so it could suppress recurrence but never notice a
REGRESSION (a control present in run N, gone in run N+1). capability_store
persists each run's control set per (repo, version) and diffs against the prior
snapshot, so a removed control becomes a surfaced finding + a posture trend.
"""
import pytest

from app.services import capability_store as cs


@pytest.fixture(autouse=True)
def _clean():
    cs.reset_all()
    yield
    cs.reset_all()


def _ctx(full_name, files):
    return {
        "repo_info": {"full_name": full_name},
        "file_tree": list(files.keys()),
        "key_files": files,
    }


class TestFingerprint:
    def test_same_corpus_same_fingerprint(self):
        c1 = _ctx("o/r", {"a.py": "x = 1"})
        c2 = _ctx("o/r", {"a.py": "x = 1"})
        assert cs.corpus_fingerprint(c1) == cs.corpus_fingerprint(c2)

    def test_changed_corpus_changes_fingerprint(self):
        c1 = _ctx("o/r", {"a.py": "x = 1"})
        c2 = _ctx("o/r", {"a.py": "x = 2"})
        assert cs.corpus_fingerprint(c1) != cs.corpus_fingerprint(c2)

    def test_prefers_commit_sha_when_present(self):
        ctx = _ctx("o/r", {"a.py": "x"})
        ctx["repo_info"]["sha"] = "abc1234def5678"
        # Snapshot under the SHA; latest_snapshot finds it.
        cs.record_snapshot(ctx, ["control A"])
        hist = cs.history("o/r")
        assert hist[0]["version"] == "abc1234def5678"


class TestDriftDetection:
    def test_first_snapshot_has_no_regression(self):
        ctx = _ctx("o/r", {"main.py": "v1"})
        drift = cs.record_snapshot(ctx, ["CORS allowlist", "header auth"])
        assert drift["regressed"] == []
        assert drift["previous_version"] is None

    def test_removed_control_is_regression(self):
        ctx1 = _ctx("o/r", {"main.py": "v1 with cors and headers"})
        cs.record_snapshot(ctx1, ["CORS allowlist", "header auth", "HSTS headers"])
        # Next version drops "CORS allowlist".
        ctx2 = _ctx("o/r", {"main.py": "v2 wildcard cors now"})
        drift = cs.record_snapshot(ctx2, ["header auth", "HSTS headers"])
        assert "CORS allowlist" in drift["regressed"]
        assert drift["added"] == []

    def test_added_control_is_improvement(self):
        ctx1 = _ctx("o/r", {"main.py": "v1"})
        cs.record_snapshot(ctx1, ["header auth"])
        ctx2 = _ctx("o/r", {"main.py": "v2"})
        drift = cs.record_snapshot(ctx2, ["header auth", "CORS allowlist"])
        assert "CORS allowlist" in drift["added"]
        assert drift["regressed"] == []

    def test_rerun_same_version_is_not_drift(self):
        ctx = _ctx("o/r", {"main.py": "v1"})
        cs.record_snapshot(ctx, ["A", "B"])
        # Re-analyze the SAME corpus → same fingerprint → no spurious regression.
        drift = cs.record_snapshot(ctx, ["A", "B"])
        assert drift["regressed"] == []
        assert drift["added"] == []

    def test_rerun_same_version_does_not_overwrite_prior_snapshot(self):
        # Regression (adversarial review): re-recording the SAME version with a
        # DIFFERENT control set (e.g. a stale/partial re-fetch of the same SHA)
        # must NOT rewrite the authoritative first snapshot — otherwise a LATER
        # version's drift would diff against mutated history and report phantom
        # regressions.
        ctx_v1 = _ctx("o/r", {"main.py": "v1"})
        cs.record_snapshot(ctx_v1, ["A", "B", "C"])           # authoritative v1
        cs.record_snapshot(ctx_v1, ["A"])                     # stale re-run — ignored
        assert sorted(cs.latest_controls("o/r")) == ["A", "B", "C"]
        # A genuine new version dropping C should see exactly ["C"] regressed,
        # NOT ["B", "C"] (which is what the corrupted-history bug produced).
        ctx_v2 = _ctx("o/r", {"main.py": "v2"})
        drift = cs.record_snapshot(ctx_v2, ["A", "B"])
        assert drift["regressed"] == ["C"]

    def test_compute_drift_pure(self):
        d = cs.compute_drift(["A", "B", "C"], ["A", "C", "D"])
        assert d["regressed"] == ["B"]
        assert d["added"] == ["D"]


class TestRegressionFindings:
    def test_regression_becomes_finding_seed(self):
        drift = {"regressed": ["CORS allowlist"], "added": [],
                 "version": "v2", "previous_version": "v1"}
        seeds = cs.regression_findings(drift)
        assert len(seeds) == 1
        assert "CORS allowlist" in seeds[0]["description"]
        assert seeds[0]["control"] == "CORS allowlist"

    def test_no_regression_no_seeds(self):
        assert cs.regression_findings({"regressed": [], "added": ["X"]}) == []
        assert cs.regression_findings(None) == []


class TestPersistenceAndHistory:
    def test_latest_controls_round_trips(self):
        ctx = _ctx("o/r", {"main.py": "v1"})
        cs.record_snapshot(ctx, ["A", "B"])
        assert sorted(cs.latest_controls("o/r")) == ["A", "B"]

    def test_history_newest_first(self):
        cs.record_snapshot(_ctx("o/r", {"f": "1"}), ["A"])
        cs.record_snapshot(_ctx("o/r", {"f": "2"}), ["A", "B"])
        hist = cs.history("o/r")
        assert len(hist) == 2
        assert hist[0]["control_count"] == 2  # newest first

    def test_per_repo_isolation(self):
        cs.record_snapshot(_ctx("a/one", {"f": "1"}), ["A"])
        assert cs.latest_controls("b/two") == []

    def test_missing_repo_is_noop(self):
        drift = cs.record_snapshot({"repo_info": {}, "file_tree": [], "key_files": {}}, ["A"])
        assert drift is None
