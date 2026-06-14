"""
BaseAgent — the shared contract every ShipMate diagnostic agent implements.

The 4 agents (RepoLens, PlanForge, GuardRail, TestPilot) were hand-rolled
classes that each re-read the same context keys and were *assumed* to be
stateless. Nothing enforced that assumption — yet the per-request orchestrator
+ concurrent agent execution (run() fans PlanForge/GuardRail/TestPilot out onto
threads) depend on it: an agent that cached request data on `self` would
reintroduce a cross-request / cross-thread data race.

This base class turns the convention into a contract:

  • REGISTRY. Every concrete subclass auto-registers (via __init_subclass__),
    so a single parametrized test can assert the stateless invariant over ALL
    agents instead of someone remembering to hand-write one per agent.

  • STATELESS INVARIANT. `instance_state_keys()` returns the set of attributes
    an agent sets in __init__ (its "shape"). The contract is: a freshly built
    agent and an agent that has just run() should have the SAME attribute shape
    — run() must not accumulate state on self. The test enforces this; this
    class documents it.

  • SHARED CONTEXT ACCESSORS. The `_file_tree` / `_key_files` / `_repo_info` /
    `_feature_context` readers stay here so agents read context one way.

Concrete agents still own their heuristics + LLM-enhancement; this only unifies
the contract beneath them.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Type

# Registry of concrete agent classes, keyed by their `name`. Populated by
# __init_subclass__ as each agent module is imported. The stateless-contract
# test iterates this so adding a 5th agent is automatically covered.
AGENT_REGISTRY: Dict[str, Type["BaseAgent"]] = {}


class BaseAgent(ABC):
    name: str = "base"
    description: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Register only concrete agents that declare a real name (skip
        # intermediate/abstract bases that don't override `name`).
        agent_name = getattr(cls, "name", None)
        if agent_name and agent_name != "base":
            AGENT_REGISTRY[agent_name] = cls

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Any:
        """Execute agent and return structured Pydantic output.

        CONTRACT: run() must be STATELESS — it may read `context` and call out
        to services, but it MUST NOT store per-run data on `self`. Per-request
        orchestrator scoping + concurrent execution rely on this. See
        instance_state_keys()."""
        ...

    # ── Stateless-contract surface ───────────────────────────────────────────

    def instance_state_keys(self) -> Set[str]:
        """The set of attribute names currently set on this instance. Used by
        the contract test: a fresh agent and a post-run() agent must have the
        SAME shape (run() accumulated no request state)."""
        return set(vars(self).keys())

    @classmethod
    def all_agents(cls) -> Dict[str, Type["BaseAgent"]]:
        """Every registered concrete agent class (import the agent modules
        first so they've run __init_subclass__)."""
        return dict(AGENT_REGISTRY)

    # ── Shared context accessors ─────────────────────────────────────────────

    def _file_tree(self, ctx: Dict) -> List[str]:
        return ctx.get("file_tree", [])

    def _key_files(self, ctx: Dict) -> Dict[str, str]:
        return ctx.get("key_files", {})

    def _repo_info(self, ctx: Dict) -> Dict[str, Any]:
        return ctx.get("repo_info", {})

    def _feature_context(self, ctx: Dict) -> str:
        return ctx.get("feature_context", "")
