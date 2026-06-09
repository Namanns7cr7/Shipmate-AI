"""Agent contract enforcement (C1 / A3).

The per-request orchestrator + concurrent agent execution rely on every
diagnostic agent being STATELESS across run(). Previously that was a convention
backed by ONE hand-written test for GuardRail. Now BaseAgent maintains a
registry of all concrete agents, and these parametrized tests enforce the
invariant over EVERY agent — adding a 5th agent is automatically covered, no
new test required.

The contract:
  1. Every agent subclasses BaseAgent and is registered by `name`.
  2. run() does not accumulate per-request state on self — a fresh instance and
     a post-run() instance have the SAME attribute shape.
  3. Two fresh instances are independent objects (no shared mutable default).

Agents run with the LLM provider forced unavailable, so they exercise the pure
heuristic path with no network — fast + deterministic.
"""
import pytest

# Import the agent package so every agent module executes __init_subclass__ and
# registers. Importing the orchestrator pulls all four in.
import app.orchestrator.shipmate_orchestrator  # noqa: F401
from app.agents.base_agent import AGENT_REGISTRY, BaseAgent


# A minimal-but-realistic context the heuristic path of every agent tolerates.
def _fixture_context():
    return {
        "repo_info": {
            "full_name": "octo/example", "name": "example",
            "owner": {"login": "octo"}, "description": "demo",
            "language": "Python", "html_url": "https://github.com/octo/example",
        },
        "branch": "main",
        "feature_context": "",
        "file_tree": [
            "backend/app/main.py",
            "backend/app/api/routes/analysis.py",
            "backend/tests/test_main.py",
            "frontend/src/App.tsx",
            "requirements.txt",
            "package.json",
        ],
        "key_files": {
            "backend/app/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "requirements.txt": "fastapi\npytest\nboto3\n",
            "package.json": '{"dependencies": {"react": "^18"}, "devDependencies": {"vitest": "^1"}}',
        },
    }


@pytest.fixture(autouse=True)
def _force_llm_unavailable(monkeypatch):
    """Make every agent take the deterministic heuristic path (no Bedrock /
    Azure call). enhance()/discover_*() all short-circuit when the provider is
    None, so patching the getter to None is the single chokepoint."""
    import app.services.llm_service as llm
    monkeypatch.setattr(llm, "_get_provider", lambda: None)


def test_registry_has_all_four_agents():
    # Sanity: the four shipped agents registered themselves on import.
    assert set(AGENT_REGISTRY) >= {"repo_lens", "plan_forge", "guardrail", "testpilot"}
    for cls in AGENT_REGISTRY.values():
        assert issubclass(cls, BaseAgent)


@pytest.mark.parametrize("agent_name", sorted(AGENT_REGISTRY))
def test_agent_is_stateless_across_run(agent_name):
    """run() must not accumulate per-request state on self: a fresh instance and
    a post-run() instance must have the SAME attribute shape."""
    cls = AGENT_REGISTRY[agent_name]
    fresh = cls()
    fresh_shape = fresh.instance_state_keys()

    ran = cls()
    ctx = _fixture_context()
    # RepoLens populates repo_lens for the others; run it first and feed result.
    if agent_name != "repo_lens":
        from app.agents.repo_lens_agent import RepoLensAgent
        ctx["repo_lens"] = RepoLensAgent().run(_fixture_context())
    ran.run(ctx)

    assert ran.instance_state_keys() == fresh_shape, (
        f"{agent_name}.run() mutated instance attribute shape "
        f"(added {ran.instance_state_keys() - fresh_shape}) — violates the "
        f"stateless invariant the per-request/concurrent orchestrator relies on."
    )


@pytest.mark.parametrize("agent_name", sorted(AGENT_REGISTRY))
def test_two_instances_are_independent(agent_name):
    """Two fresh agents must be distinct objects with independent attributes —
    no shared mutable default that one request could mutate for another."""
    cls = AGENT_REGISTRY[agent_name]
    a, b = cls(), cls()
    assert a is not b
    # Any sub-agent/service attributes must also be distinct instances.
    for key in a.instance_state_keys():
        va, vb = getattr(a, key, None), getattr(b, key, None)
        if va is not None and not isinstance(va, (str, int, float, bool, tuple, frozenset)):
            assert va is not vb, (
                f"{agent_name}.{key} is SHARED across instances ({va!r}); each "
                f"agent must own its collaborators so concurrent runs can't alias."
            )


@pytest.mark.parametrize("agent_name", sorted(AGENT_REGISTRY))
def test_agent_run_returns_pydantic_output(agent_name):
    """Each agent returns a Pydantic model (the structured-output contract)."""
    from pydantic import BaseModel
    cls = AGENT_REGISTRY[agent_name]
    ctx = _fixture_context()
    if agent_name != "repo_lens":
        from app.agents.repo_lens_agent import RepoLensAgent
        ctx["repo_lens"] = RepoLensAgent().run(_fixture_context())
    out = cls().run(ctx)
    assert isinstance(out, BaseModel)
