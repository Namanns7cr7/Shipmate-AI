"""Tests for the Decomposer — the planning agent that splits multi-file
features into ordered Coder steps. Provider is mocked (offline). We test the
deterministic post-processing: topo ordering, single-step synthesis, cap.
"""
from app.agents.decomposer import Decomposer, Plan, PlanStep, _topo_order


class _StubProvider:
    def __init__(self, plan):
        self._plan = plan
        self.calls = 0

    def invoke_structured_sync(self, *, system_prompt, user_prompt, schema_class, deployment_hint="smart"):
        self.calls += 1
        return self._plan


class TestTopoOrder:
    def test_already_ordered(self):
        steps = [
            PlanStep(name="a", task="t", depends_on=[]),
            PlanStep(name="b", task="t", depends_on=[0]),
            PlanStep(name="c", task="t", depends_on=[1]),
        ]
        assert _topo_order(steps) == [0, 1, 2]

    def test_reorders_out_of_order_deps(self):
        # Step 0 depends on step 1 — must come after it.
        steps = [
            PlanStep(name="route", task="t", depends_on=[1]),
            PlanStep(name="model", task="t", depends_on=[]),
        ]
        order = _topo_order(steps)
        assert order.index(1) < order.index(0)

    def test_cycle_falls_back_to_input_order(self):
        steps = [
            PlanStep(name="a", task="t", depends_on=[1]),
            PlanStep(name="b", task="t", depends_on=[0]),
        ]
        assert _topo_order(steps) == [0, 1]

    def test_out_of_range_dep_ignored(self):
        steps = [PlanStep(name="a", task="t", depends_on=[99])]
        assert _topo_order(steps) == [0]


class TestDecomposerPlan:
    def test_returns_topologically_ordered_plan(self):
        raw = Plan(
            steps=[
                PlanStep(name="wire route", task="add route", target_paths=["app/api/routes/reports.py"], depends_on=[1]),
                PlanStep(name="add model", task="add model", target_paths=["app/models/report.py"], depends_on=[]),
            ],
            summary="persist reports",
        )
        dec = Decomposer(provider=_StubProvider(raw))
        plan = dec.plan("Persist reports to DB", "o/r")
        # 'add model' (originally index 1) must come before 'wire route'.
        assert plan.steps[0].name == "add model"
        assert plan.steps[1].name == "wire route"

    def test_empty_steps_synthesizes_single_step(self):
        raw = Plan(steps=[], summary="")
        dec = Decomposer(provider=_StubProvider(raw))
        plan = dec.plan("Do the thing", "o/r")
        assert len(plan.steps) == 1
        assert plan.steps[0].task == "Do the thing"

    def test_step_cap_enforced(self):
        raw = Plan(
            steps=[PlanStep(name=f"s{i}", task="t", depends_on=[]) for i in range(20)],
            summary="huge",
        )
        dec = Decomposer(provider=_StubProvider(raw))
        plan = dec.plan("big feature", "o/r")
        assert len(plan.steps) <= 8

    def test_single_step_passthrough(self):
        raw = Plan(
            steps=[PlanStep(name="fix", task="one-file fix", target_paths=["app/main.py"], depends_on=[])],
            summary="single",
        )
        dec = Decomposer(provider=_StubProvider(raw))
        plan = dec.plan("one file fix", "o/r")
        assert len(plan.steps) == 1
        assert plan.steps[0].target_paths == ["app/main.py"]
