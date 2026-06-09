"""Coder failure-memory (B2 / C4).

The journal records WHAT happened to a finding, never WHY a Coder patch failed,
so the Coder re-hallucinates the same import / re-commits the same scope creep
every few runs. coder_lessons distills each gate rejection into a durable,
per-repo lesson and injects the recurring ones into the next Coder brief.

These tests pin: distillation maps raw issues to canonical lessons, re-failures
aggregate (hit_count), and the digest surfaces the worst offenders.
"""
import pytest

from app.services import coder_lessons as cl

REPO = "octo/example"


@pytest.fixture(autouse=True)
def _clean():
    cl.reset_all()
    yield
    cl.reset_all()


class TestDistill:
    def test_hallucinated_import_extracts_symbol(self):
        key, lesson = cl.distill(
            "lint",
            "app/main.py: hallucinated first-party imports not in repo or "
            "original file: ['app.services.auth']",
        )
        assert key.startswith("hallucinated-import")
        assert "app.services.auth" in lesson
        assert "IMPORT FIDELITY" in lesson

    def test_stale_symbol(self):
        key, lesson = cl.distill(
            "lint",
            "x.py: imports symbols that don't exist in the target module(s): "
            "['resolve_token']",
        )
        assert key.startswith("stale-symbol")
        assert "SYMBOL FIDELITY" in lesson

    def test_scope_gate(self):
        key, lesson = cl.distill("scope", "dropped unrelated router include")
        assert key == "scope-drift"
        assert "SCOPE DISCIPLINE" in lesson

    def test_pytest_gate(self):
        key, lesson = cl.distill("pytest", "pytest regression: 120 → 118 passing")
        assert key == "pytest-regression"
        assert "TEST SAFETY" in lesson

    def test_resolution_gate(self):
        key, lesson = cl.distill("resolution", "injection: offending pattern still present")
        assert key == "unresolved-finding"
        assert "ACTUALLY FIX IT" in lesson

    def test_syntax(self):
        key, lesson = cl.distill("lint", "main.py: invalid syntax at line 4")
        assert key == "python-syntax"


class TestRecordAndAggregate:
    def test_repeat_failure_bumps_hit_count(self):
        issue = ("app/main.py: hallucinated first-party imports not in repo or "
                 "original file: ['app.services.auth']")
        cl.record_failure(REPO, "lint", [issue])
        cl.record_failure(REPO, "lint", [issue])
        cl.record_failure(REPO, "lint", [issue])
        lessons = cl.top_lessons(REPO)
        # Same class of failure aggregates to ONE lesson with hit_count 3.
        hallucination = [l for l in lessons if "IMPORT FIDELITY" in l["lesson"]]
        assert len(hallucination) == 1
        assert hallucination[0]["hit_count"] == 3

    def test_distinct_gates_are_separate_lessons(self):
        cl.record_failure(REPO, "scope", ["dropped a router"])
        cl.record_failure(REPO, "pytest", "pytest regression: 10 → 8 passing")
        lessons = cl.top_lessons(REPO)
        assert len(lessons) == 2

    def test_record_with_string_issue(self):
        cl.record_failure(REPO, "pytest", "pytest regression: 5 → 3 passing")
        assert cl.count(REPO) == 1

    def test_record_empty_issues_still_logs_gate(self):
        cl.record_failure(REPO, "lint", [])
        assert cl.count(REPO) >= 1


class TestDigest:
    def test_digest_orders_by_recurrence(self):
        cl.record_failure(REPO, "scope", ["dropped a router"])
        # hallucination fails 3×, scope once → hallucination ranks first.
        for _ in range(3):
            cl.record_failure(
                REPO, "lint",
                ["x.py: hallucinated first-party imports: ['app.services.auth']"],
            )
        digest = cl.lessons_digest(REPO)
        assert "LESSONS FROM PRIOR PATCHES" in digest
        assert "IMPORT FIDELITY" in digest
        # The 3× one shows its recurrence count.
        assert "seen 3×" in digest
        # Ordering: import-fidelity line appears before the scope line.
        assert digest.index("IMPORT FIDELITY") < digest.index("SCOPE DISCIPLINE")

    def test_empty_digest_when_no_lessons(self):
        assert cl.lessons_digest(REPO) == ""

    def test_digest_is_per_repo(self):
        cl.record_failure("a/one", "scope", ["dropped a router"])
        assert cl.lessons_digest("b/two") == ""

    def test_no_repo_is_noop(self):
        cl.record_failure("", "lint", ["x"])
        assert cl.count() == 0
