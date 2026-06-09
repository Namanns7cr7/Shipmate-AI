"""Observability run-trace layer (D).

Records one structured row per instrumented LLM/agent operation, keyed by a
run_id that flows through a contextvar — so nested calls (incl. thread workers)
attribute to the same run with no signature plumbing. Must be a cheap no-op
when no run is active, and must never raise into the caller.
"""
import pytest

from app.services import run_trace


@pytest.fixture(autouse=True)
def _clean_traces():
    run_trace.reset_all()
    yield
    run_trace.reset_all()


class TestNoOpWhenInactive:
    def test_span_writes_nothing_without_active_run(self):
        # No run context → span is a no-op, yields a usable handle, writes 0 rows.
        with run_trace.span("llm:test", "invoke", prompt="hi") as sp:
            sp.bump_retry()
            sp.set_output("out")
        assert run_trace.recent_runs() == []

    def test_record_noop_without_run(self):
        run_trace.record("llm:test", "invoke", prompt="x")
        assert run_trace.recent_runs() == []


class TestActiveRun:
    def test_span_records_one_row(self):
        with run_trace.run(prefix="t") as rid:
            with run_trace.span("agent:guardrail", "run", prompt="abc") as sp:
                sp.set_output("a result")
        traces = run_trace.list_traces(rid)
        assert len(traces) == 1
        assert traces[0]["component"] == "agent:guardrail"
        assert traces[0]["op"] == "run"
        assert traces[0]["outcome"] == "ok"
        assert traces[0]["prompt_chars"] == 3

    def test_retry_bump_is_recorded(self):
        with run_trace.run() as rid:
            with run_trace.span("llm:bedrock:smart", "invoke", prompt="p") as sp:
                sp.bump_retry()
                sp.bump_retry()
        s = run_trace.run_summary(rid)
        assert s["total_retries"] == 2
        assert s["spans"] == 1

    def test_error_outcome_recorded_and_reraised(self):
        with run_trace.run() as rid:
            with pytest.raises(ValueError):
                with run_trace.span("llm:bedrock:fast", "invoke", prompt="p"):
                    raise ValueError("boom")
        traces = run_trace.list_traces(rid)
        assert len(traces) == 1
        assert traces[0]["outcome"] == "error"
        assert "boom" in (traces[0]["error"] or "")

    def test_run_summary_aggregates_by_component(self):
        with run_trace.run() as rid:
            with run_trace.span("agent:plan_forge", "run", prompt="x"):
                pass
            with run_trace.span("agent:plan_forge", "run", prompt="y"):
                pass
            with run_trace.span("agent:guardrail", "run", prompt="z"):
                pass
        s = run_trace.run_summary(rid)
        assert s["spans"] == 3
        assert s["by_component"]["agent:plan_forge"]["count"] == 2
        assert s["by_component"]["agent:guardrail"]["count"] == 1


class TestContextPropagation:
    def test_run_id_visible_inside_block_and_reset_after(self):
        assert run_trace.get_current_run() is None
        with run_trace.run() as rid:
            assert run_trace.get_current_run() == rid
        assert run_trace.get_current_run() is None

    def test_thread_worker_inherits_run_via_copied_context(self):
        import concurrent.futures as cf
        import contextvars

        def work():
            # A copied context preserves the active run_id into the worker.
            with run_trace.span("agent:thread", "run", prompt="t"):
                pass
            return run_trace.get_current_run()

        with run_trace.run() as rid:
            with cf.ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(contextvars.copy_context().run, work)
                seen = fut.result()
        assert seen == rid
        assert len(run_trace.list_traces(rid)) == 1
