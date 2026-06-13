"""PRRiskAgent — diff-grounded pull-request risk scoring.

These tests run the agent against synthetic PR diffs (no GitHub, no LLM) so they
prove the DETERMINISTIC heuristic: surface detection, secret/danger introduction,
changed-source-without-tests, size, score → level mapping, and graceful empties.
The optional LLM prose pass is forced off via the provider patch so the suite is
hermetic and fast.
"""
import pytest

from app.agents.pr_risk_agent import PRRiskAgent
from app.schemas.agent_schemas import PRRiskOutput, ShipMateReport
from app.services.llm_service import LLMService


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    """Force the optional LLM prose pass off — deterministic output only, no
    network. Without this the agent would try to build a provider on the
    default bedrock path."""
    # raising=False: on branches where LLMService has no `provider` accessor the
    # agent's prose pass fails open anyway; we just guarantee it stays off here.
    monkeypatch.setattr(LLMService, "provider", staticmethod(lambda: None), raising=False)


def _ctx(pr_files, number=7, title="Test PR"):
    return {"pr_info": {"number": number, "title": title}, "pr_files": pr_files}


def _f(filename, status="modified", additions=10, deletions=0, patch=None):
    return {
        "filename": filename, "status": status,
        "additions": additions, "deletions": deletions,
        "changes": additions + deletions, "patch": patch,
    }


# ── Graceful / low-risk ──────────────────────────────────────────────────────

def test_no_pr_files_is_graceful():
    out = PRRiskAgent().run(_ctx([]))
    assert isinstance(out, PRRiskOutput)
    assert out.pr_number == 7
    assert out.risk_level == "low"
    assert out.risk_score == 0
    assert "no risk" in out.summary.lower() or "no changed" in out.summary.lower()


def test_docs_only_pr_is_low_risk():
    out = PRRiskAgent().run(_ctx([
        _f("README.md", additions=20, deletions=2, patch="+Some new documentation\n+More docs"),
        _f("docs/guide.md", additions=8),
    ]))
    assert out.files_changed == 2
    assert out.additions == 28
    assert out.risk_level == "low"
    # Markdown isn't a "source" file, so it must NOT be flagged as untested.
    assert out.changed_files_without_tests == []
    assert not any(fc.severity.value in ("critical", "high") for fc in out.risk_factors)


# ── Sensitive surfaces ───────────────────────────────────────────────────────

def test_auth_change_without_tests_is_elevated():
    out = PRRiskAgent().run(_ctx([
        _f("backend/app/api/routes/auth.py", additions=120, deletions=30,
           patch="+def login(...):\n+    return token"),
    ]))
    cats = {fc.category for fc in out.risk_factors}
    assert "auth" in cats                       # auth surface detected
    assert "tests" in cats                       # changed source, no test change
    assert "backend/app/api/routes/auth.py" in out.changed_files_without_tests
    assert out.risk_level in ("medium", "high", "critical")
    assert any("auth" in s.lower() for s in out.risky_surfaces)


def test_source_with_matching_test_change_not_flagged():
    out = PRRiskAgent().run(_ctx([
        _f("backend/app/services/scoring_service.py", additions=15),
        _f("backend/tests/test_scoring_service.py", additions=40),
    ]))
    # scoring_service.py has a sibling test change in the same PR → not "untested".
    assert out.changed_files_without_tests == []
    assert not any(fc.category == "tests" for fc in out.risk_factors)


def test_dependency_manifest_change_flagged():
    out = PRRiskAgent().run(_ctx([
        _f("requirements.txt", additions=3, patch="+requests==2.0.0"),
    ]))
    assert any(fc.category == "deps" for fc in out.risk_factors)


# ── Introduced secrets / dangerous constructs ────────────────────────────────

def test_secret_introduced_in_diff_is_critical():
    token_line = "+GITHUB_TOKEN = \"ghp_" + "a" * 36 + "\""
    out = PRRiskAgent().run(_ctx([
        _f("backend/app/config.py", additions=2, patch="+import os\n" + token_line),
    ]))
    assert out.risk_level == "critical"
    assert any(fc.category == "secrets" and fc.severity.value == "critical"
               for fc in out.risk_factors)


def test_eval_introduced_in_diff_flagged_injection():
    out = PRRiskAgent().run(_ctx([
        _f("backend/app/util.py", additions=2, patch="+def f(x):\n+    return eval(x)"),
    ]))
    assert any(fc.category == "injection" for fc in out.risk_factors)


def test_secret_in_test_file_is_ignored():
    token_line = "+API_KEY = \"ghp_" + "b" * 36 + "\""
    out = PRRiskAgent().run(_ctx([
        _f("backend/tests/test_fixtures.py", additions=2, patch="+mock\n" + token_line),
    ]))
    # Fixture/mock credentials in a test file must not raise a secrets factor.
    assert not any(fc.category == "secrets" for fc in out.risk_factors)


# ── Size / blast radius ──────────────────────────────────────────────────────

def test_large_pr_flagged_for_size():
    files = [_f(f"src/module_{i}.py", additions=10) for i in range(30)]
    out = PRRiskAgent().run(_ctx(files))
    assert out.files_changed == 30
    assert any(fc.category == "size" for fc in out.risk_factors)


def test_score_monotonic_with_severity():
    low = PRRiskAgent().run(_ctx([_f("README.md", patch="+docs")]))
    high = PRRiskAgent().run(_ctx([
        _f("backend/app/api/routes/auth.py", additions=2000,
           patch="+x\n+API_KEY = \"ghp_" + "c" * 36 + "\""),
    ]))
    assert high.risk_score > low.risk_score
    assert 0 <= low.risk_score <= 100 and 0 <= high.risk_score <= 100


# ── Schema back-compat ───────────────────────────────────────────────────────

def test_report_without_pr_risk_validates_to_none():
    """An older stored report (no pr_risk key) must still validate, defaulting
    pr_risk to None — proves the new optional field is back-compatible."""
    rl = {
        "tech_stack": [], "primary_language": "Python", "architecture_pattern": "backend",
        "key_modules": [], "entry_points": [], "config_files": [],
        "has_ci_cd": True, "has_dockerfile": True, "has_tests": True,
        "architecture_risks": [], "dependency_summary": {}, "file_count": 10, "repo_score": 80,
    }
    report = {
        "repo": {"owner": "o", "name": "r", "full_name": "o/r", "branch": "main"},
        "readiness_score": 80, "ship_recommendation": "mostly_ready",
        "score_breakdown": {"repo_score": 80, "delivery_score": 80, "security_score": 80, "test_score": 80},
        "agents": {
            "repo_lens": rl,
            "plan_forge": {"milestones": [], "blockers": [], "dependencies": [],
                           "next_best_action": "ship", "estimated_effort": "1 day", "delivery_score": 80},
            "guardrail": {"findings": [], "exposed_secrets": [], "cors_issues": [],
                          "auth_risks": [], "dependency_vulnerabilities": [], "security_score": 80},
            "testpilot": {"existing_tests": {"count": 1, "coverage_estimate": 60, "frameworks": [], "test_files": []},
                          "missing_coverage_areas": [], "suggested_tests": [], "qa_readiness": "ready", "test_score": 80},
        },
        "key_blockers": [], "next_actions": [], "generated_at": "2026-01-01T00:00:00Z",
    }
    parsed = ShipMateReport.model_validate(report)
    assert parsed.pr_risk is None


def test_report_round_trips_with_pr_risk():
    out = PRRiskAgent().run(_ctx([_f("backend/app/api/routes/auth.py", additions=50)]))
    dumped = out.model_dump()
    assert PRRiskOutput.model_validate(dumped).pr_number == out.pr_number


# ── Orchestrator assembly wiring ─────────────────────────────────────────────

def _min_agent_outputs():
    """Minimal valid outputs for the four repo-level agents, so the orchestrator
    can assemble a report without running heuristics/LLM/network."""
    from app.schemas.agent_schemas import (
        RepoLensOutput, PlanForgeOutput, GuardRailOutput, TestPilotOutput, ExistingTests,
    )
    rl = RepoLensOutput(
        tech_stack=["Python"], primary_language="Python", architecture_pattern="backend",
        key_modules=[], entry_points=["main.py"], config_files=[], has_ci_cd=True,
        has_dockerfile=True, has_tests=True, architecture_risks=[], dependency_summary={},
        file_count=10, repo_score=80,
    )
    pf = PlanForgeOutput(milestones=[], blockers=[], dependencies=[],
                         next_best_action="ship", estimated_effort="1 day", delivery_score=80)
    gr = GuardRailOutput(findings=[], exposed_secrets=[], cors_issues=[], auth_risks=[],
                         dependency_vulnerabilities=[], security_score=80)
    tp = TestPilotOutput(
        existing_tests=ExistingTests(count=1, coverage_estimate=60, frameworks=[], test_files=[]),
        missing_coverage_areas=[], suggested_tests=[], qa_readiness="ready", test_score=80,
    )
    return rl, pf, gr, tp


def _stub_repo_agents(monkeypatch, orch):
    """Stub the four repo-level agents so the orchestrator integration test
    exercises ONLY the PR-risk wiring (the real pr_risk agent still runs),
    with no LLM/network from the diagnostic agents."""
    rl, pf, gr, tp = _min_agent_outputs()
    monkeypatch.setattr(orch.repo_lens, "run", lambda ctx: rl)
    monkeypatch.setattr(orch.plan_forge, "run", lambda ctx: pf)
    monkeypatch.setattr(orch.guardrail, "run", lambda ctx: gr)
    monkeypatch.setattr(orch.testpilot, "run", lambda ctx: tp)


def _run_ctx(pr_files):
    return {
        "repo_info": {"owner": {"login": "o"}, "name": "r", "full_name": "o/r"},
        "branch": "main", "file_tree": [], "key_files": {},
        "pr_info": {"number": 7, "title": "x"} if pr_files else None,
        "pr_files": pr_files,
    }


def test_orchestrator_attaches_pr_risk_when_present(monkeypatch):
    from app.orchestrator.shipmate_orchestrator import ShipMateOrchestrator
    orch = ShipMateOrchestrator()
    _stub_repo_agents(monkeypatch, orch)
    report = orch.run(_run_ctx([_f("backend/app/api/routes/auth.py", additions=50)]))
    assert report.pr_risk is not None
    assert report.pr_risk.pr_number == 7
    # Survives a full serialize/validate round-trip (the report_store path).
    from app.schemas.agent_schemas import ShipMateReport
    assert ShipMateReport.model_validate(report.model_dump()).pr_risk is not None


def test_orchestrator_omits_pr_risk_for_branch_analysis(monkeypatch):
    from app.orchestrator.shipmate_orchestrator import ShipMateOrchestrator
    orch = ShipMateOrchestrator()
    _stub_repo_agents(monkeypatch, orch)
    report = orch.run(_run_ctx([]))  # no PR files → no PR-risk card
    assert report.pr_risk is None
    assert orch._has_pr({"pr_files": []}) is False
    assert orch._has_pr({"pr_files": [{"filename": "x"}]}) is True
