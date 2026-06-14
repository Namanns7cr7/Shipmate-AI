"""Tests for the durable BuildRun state machine (Refactor #4).

Proves a /build/execute run is observable + survives independent of the HTTP
request: the run row records each transition (planning → critiquing →
actuating → done|failed), accumulates pr_urls, and is queryable via the
inflight_registry CRUD + the /build/runs endpoints.
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


# ── Registry CRUD ────────────────────────────────────────────────────────────

def test_create_and_get_build_run():
    from app.services import inflight_registry as ir
    ir.create_build_run("run1", "o", "r", "main", "sig::x", opportunity_title="Add X",
                        status="planning", step_count=3)
    run = ir.get_build_run("run1")
    assert run is not None
    assert run["status"] == "planning"
    assert run["step_count"] == 3
    assert run["opportunity_title"] == "Add X"
    assert run["pr_urls"] == []
    assert run["completed_at"] is None


def test_update_transitions_and_terminal_sets_completed_at():
    from app.services import inflight_registry as ir
    ir.create_build_run("run2", "o", "r", "main", "sig::y", status="planning")
    ir.update_build_run("run2", status="actuating", steps_completed=1,
                        pr_urls=["https://gh/pr/1"])
    run = ir.get_build_run("run2")
    assert run["status"] == "actuating"
    assert run["pr_urls"] == ["https://gh/pr/1"]
    assert run["completed_at"] is None

    ir.update_build_run("run2", status="done", pr_urls=["https://gh/pr/1", "https://gh/pr/2"])
    run = ir.get_build_run("run2")
    assert run["status"] == "done"
    assert run["pr_urls"] == ["https://gh/pr/1", "https://gh/pr/2"]
    assert run["completed_at"] is not None, "terminal status must stamp completed_at"


def test_list_build_runs_filters():
    from app.services import inflight_registry as ir
    ir.create_build_run("a", "o", "r", "main", "s1", status="done")
    ir.create_build_run("b", "o", "r", "main", "s2", status="failed")
    ir.create_build_run("c", "o", "other", "main", "s3", status="actuating")

    assert len(ir.list_build_runs(owner="o")) == 3
    assert len(ir.list_build_runs(owner="o", repo="r")) == 2
    assert len(ir.list_build_runs(status_in=["failed"])) == 1
    assert len(ir.list_build_runs(owner="o", repo="other")) == 1


def test_unknown_status_rejected():
    from app.services import inflight_registry as ir
    with pytest.raises(ValueError):
        ir.create_build_run("z", "o", "r", "main", "s", status="bogus")


def test_concurrent_runs_same_opportunity_keep_separate_rows():
    """A UUID PK means the SAME opportunity can run twice without clobbering."""
    from app.services import inflight_registry as ir
    ir.create_build_run("run-A", "o", "r", "main", "same::sig", status="done")
    ir.create_build_run("run-B", "o", "r", "main", "same::sig", status="actuating")
    runs = ir.list_build_runs(owner="o", repo="r")
    assert {r["run_id"] for r in runs} == {"run-A", "run-B"}


# ── Endpoints ────────────────────────────────────────────────────────────────

def test_build_runs_endpoints():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import inflight_registry as ir

    ir.create_build_run("ep1", "acme", "widget", "main", "sig::z",
                        opportunity_title="Cache things", status="actuating",
                        step_count=2)
    ir.update_build_run("ep1", steps_completed=1, pr_urls=["https://gh/pr/9"])

    client = TestClient(app)
    # List
    resp = client.get("/api/build/runs", params={"owner": "acme", "repo": "widget"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["runs"][0]["run_id"] == "ep1"

    # Single
    resp = client.get("/api/build/runs/ep1")
    assert resp.status_code == 200
    run = resp.json()
    assert run["status"] == "actuating"
    assert run["steps_completed"] == 1
    assert run["pr_urls"] == ["https://gh/pr/9"]

    # 404
    assert client.get("/api/build/runs/nope").status_code == 404


# ── Integration: execute_opportunity writes a durable run record ──────────────

def test_execute_opportunity_records_durable_run(monkeypatch):
    """A plan-only execute (execute=False) still creates a terminal run row that
    carries the plan + critique — proving the state machine is wired into the
    service, not just the table."""
    import asyncio
    from app.services.opportunity_service import OpportunityService
    from app.services import inflight_registry as ir
    from app.schemas.agent_schemas import Opportunity, ExecutionPlan, BuildStep, PlanCritique
    from app.agents import planner_agent as pa
    from app.services import plan_critic as pc

    # Stub the planner + critic so the test doesn't need an LLM.
    plan = ExecutionPlan(
        opportunity_id="OPP1", opportunity_title="Add caching", summary="overview",
        steps=[BuildStep(index=1, kind="milestone", title="step", description="d",
                         target_files=["app/x.py"])],
    )
    monkeypatch.setattr(pa.PlannerAgent, "plan", lambda self, opp, tree: plan)
    monkeypatch.setattr(
        pc, "critique_plan",
        lambda plan, opp, provider: PlanCritique(approved=True, reason="ok"),
    )

    opp = Opportunity(id="OPP1", title="Add caching", category="improvement",
                      description="s", impact="better", effort="S", estimated_days=2,
                      rationale="r", target_files=["app/x.py"])
    repo_context = {"repo_info": {"owner": {"login": "acme"}, "name": "widget",
                                  "full_name": "acme/widget"}, "branch": "main",
                    "file_tree": ["app/x.py"]}

    resp = asyncio.run(OpportunityService.execute_opportunity(
        repo_context, opp, "ghp_tok", execute=False,
    ))
    assert resp.run_id, "execute must surface a run_id"
    run = ir.get_build_run(resp.run_id)
    assert run is not None
    assert run["status"] == "done"           # plan-only preview is terminal
    assert run["opportunity_title"] == "Add caching"
    assert run["plan"] is not None
    assert run["critique"] is not None
