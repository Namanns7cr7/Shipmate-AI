"""Analyze-side anti-recurrence: the diagnostic pipeline (GuardRail/PlanForge/
TestPilot) must stop re-surfacing already-resolved, dismissed, and keyword-
false-positive findings — the same protection the Build path's already_built +
journal gates give the Opportunity pipeline.

Covers:
  • finding_critic.filter_already_resolved — drops a finding whose demanded
    control already exists in the FULL corpus (e.g. token-in-query after the
    routes use resolve_access_token; "persist results" after save_report).
  • finding_critic.filter_suppressed_by_name — TestPilot's .name-keyed findings.
  • guardrail_agent._has_real_jwt_secret_issue — no JWT in the repo → no finding.
  • orchestrator._filter_findings — the wiring that applies all three.
"""
import os

import pytest

from app.services import sqlite_store


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMATE_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("SHIPMATE_INFLIGHT_DB", raising=False)
    sqlite_store.close_all()
    from app.services import inflight_registry as ir
    ir.reset_all()
    yield
    sqlite_store.close_all()


class _F:
    """Minimal finding stand-in with title/description/file."""
    def __init__(self, title, description="", file=None):
        self.title = title
        self.description = description
        self.file = file


# ── already-resolved prefilter ───────────────────────────────────────────────

def test_already_resolved_drops_token_in_query_when_dep_present():
    from app.services import finding_critic as fc
    findings = [_F("Access Token Leaked in Query Parameter on /auth/github/me")]
    # Corpus proves the control exists: routes use resolve_access_token.
    key_files = {"auth.py": "access_token: str = Depends(resolve_access_token)"}
    kept = fc.filter_already_resolved(findings, [], key_files)
    assert kept == [], "token-in-query finding must be dropped — control present"


def test_already_resolved_drops_persist_results_when_save_report_present():
    from app.services import finding_critic as fc
    findings = [_F("Persist Analysis Results to SQLite Store")]
    key_files = {"analysis.py": "report_store.save_report(report)"}
    kept = fc.filter_already_resolved(findings, [], key_files)
    assert kept == []


def test_already_resolved_keeps_finding_when_control_absent():
    from app.services import finding_critic as fc
    findings = [_F("Access Token Leaked in Query Parameter on /foo")]
    # Corpus does NOT contain the dependency — finding is genuine, keep it.
    key_files = {"other.py": "def unrelated(): pass"}
    kept = fc.filter_already_resolved(findings, [], key_files)
    assert len(kept) == 1, "must NOT drop when the control isn't present (fail-open)"


def test_already_resolved_keeps_unrelated_finding():
    from app.services import finding_critic as fc
    findings = [_F("Some novel issue with no known proof pattern")]
    key_files = {"a.py": "resolve_access_token"}
    kept = fc.filter_already_resolved(findings, [], key_files)
    assert len(kept) == 1


# ── name-keyed suppression (TestPilot) ───────────────────────────────────────

def test_filter_suppressed_by_name():
    from app.services import finding_critic as fc
    from app.services import inflight_registry as ir

    class _T:
        def __init__(self, name, target_file=None):
            self.name = name
            self.target_file = target_file

    # Journal a dismissed test signature (kind=test, name→title slot).
    sig = fc.finding_signature("test", "test_foo_bar", "tests/test_x.py")
    ir.journal_set_state(sig, "o/r", "dismissed")

    tests = [_T("test_foo_bar", "tests/test_x.py"), _T("test_keep_me", "tests/test_y.py")]
    kept = fc.filter_suppressed_by_name(tests, "test", "o/r")
    names = [t.name for t in kept]
    assert names == ["test_keep_me"], "dismissed test must be suppressed"


# ── JWT false-positive fix ───────────────────────────────────────────────────

# GuardRailAgent.run() makes a real LLM discovery call (slow / network), so the
# JWT-heuristic behavior is tested at the detector level — hermetic + fast — and
# the run()-level wiring is covered by the heuristic feeding the finding.

def test_jwt_detector_false_for_repo_without_real_signing():
    """The recurring FP: a file that only MENTIONS jwt/secret in prose, a finding
    string, or with an env-loaded secret must NOT trip the detector."""
    from app.agents.guardrail_agent import _has_real_jwt_secret_issue as j
    assert j("# note: we do not use jwt here, GitHub OAuth only") is False
    assert j("DESC = 'JWT secret appears hardcoded'  # finding text") is False
    assert j("import jwt\ntoken = jwt.encode(p, os.environ['SECRET'])") is False, \
        "env-loaded secret is the CORRECT pattern — must not flag"


def test_jwt_detector_true_for_real_hardcoded_secret():
    from app.agents.guardrail_agent import _has_real_jwt_secret_issue as j
    assert j("import jwt\nreturn jwt.encode(p, secret='hardcoded-shh-12345')") is True


# ── orchestrator wiring (end-to-end through _filter_findings) ────────────────

def test_orchestrator_filter_drops_resolved_guardrail_finding(monkeypatch):
    from app.orchestrator.shipmate_orchestrator import ShipMateOrchestrator
    from app.schemas.agent_schemas import (
        GuardRailOutput, SecurityFinding, PlanForgeOutput, TestPilotOutput,
        ExistingTests, Severity,
    )

    # Disable the LLM critic so we test the deterministic path in isolation.
    monkeypatch.setenv("SHIPMATE_FINDING_CRITIC", "0")

    guardrail = GuardRailOutput(
        findings=[
            SecurityFinding(
                id="SEC-001",
                title="Access Token Leaked in Query Parameter on /auth/github/me",
                severity=Severity.CRITICAL, category="auth",
                description="token passed as query param", recommendation="use header",
            ),
            SecurityFinding(
                id="SEC-002", title="Real novel finding", severity=Severity.HIGH,
                category="config", description="something genuinely wrong",
                recommendation="fix it",
            ),
        ],
        exposed_secrets=[], cors_issues=[], auth_risks=[],
        dependency_vulnerabilities=[], security_score=50,
    )
    plan_forge = PlanForgeOutput(milestones=[], blockers=[], dependencies=[],
                                 next_best_action="", estimated_effort="", delivery_score=80)
    testpilot = TestPilotOutput(
        existing_tests=ExistingTests(count=0, coverage_estimate=0, frameworks=[], test_files=[]),
        missing_coverage_areas=[], suggested_tests=[], qa_readiness="partial", test_score=60,
    )

    repo_context = {
        "file_tree": ["app/api/routes/auth.py"],
        "key_files": {"auth.py": "access_token: str = Depends(resolve_access_token)"},
        "repo_info": {"owner": {"login": "o"}, "name": "r", "full_name": "o/r"},
    }

    pf, gr, tp = ShipMateOrchestrator()._filter_findings(
        repo_context, plan_forge, guardrail, testpilot
    )
    titles = [f.title for f in gr.findings]
    assert "Access Token Leaked in Query Parameter on /auth/github/me" not in titles, \
        "resolved finding must be dropped by the orchestrator filter"
    assert "Real novel finding" in titles, "genuine finding must survive"
