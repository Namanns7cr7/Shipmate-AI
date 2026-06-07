"""
Decomposer — splits a multi-file feature/milestone into ordered Coder steps.

Why: the autonomous loop keeps SKIPPING "milestone" findings like "Persist
Analysis Reports to DB" because a single Coder call returns 0 files — the
task is too big to land as one focused patch (it needs a model + a service +
a route + a migration, in dependency order). The Decomposer makes one small
planning call (smart model) that returns a Plan: a topologically-ordered list
of steps, each scoped to a few files. The orchestrator then dispatches each
step to CoderAgent, feeding the PREVIOUS step's output into the next step's
target_files so step N sees step N-1's new symbols as ground truth.

This is a PLANNING agent only — it writes no code. It returns structure; the
existing CoderAgent + gates do the actual work, once per step, all committed
to one branch before the PR opens.

Off by default — gated behind the `--decompose` CLI flag / `decompose=True`
request field. Single-step plans (the common case) are indistinguishable from
today's behaviour.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from app.services.bedrock_provider import BedrockProvider

logger = logging.getLogger("shipmate.decomposer")

_SYSTEM_PROMPT = (
    "You are a senior engineer breaking a multi-file feature into an ordered "
    "sequence of small, independently-implementable steps for a code-writing "
    "agent. Each step should touch 1-3 files and represent one coherent unit "
    "(e.g. 'add the SQLAlchemy model', then 'add the persistence service', "
    "then 'wire the route'). \n\n"
    "HARD RULES:\n"
    "  • Order steps so that a step only depends on EARLIER steps "
    "(topological). Express dependencies via `depends_on` (0-based indices of "
    "earlier steps).\n"
    "  • Every path in `target_paths` must be a real, plausible repo path. "
    "Prefer paths that already exist; for new files, follow the repo's "
    "existing directory conventions (shown in the file tree).\n"
    "  • Keep the plan MINIMAL — the fewest steps that actually deliver the "
    "feature. Do not invent scope. 2-5 steps is typical; 1 step is fine if "
    "the feature really is single-file.\n"
    "  • Do NOT write code. Only describe what each step must accomplish in "
    "its `task` (one short paragraph the code agent will act on).\n"
    "  • If the finding is NOT actually multi-file (it's a one-file fix), "
    "return a single step.\n"
    "Return ONLY the structured Plan object."
)


class PlanStep(BaseModel):
    name: str = Field(..., description="Short imperative label, e.g. 'Add Report SQLAlchemy model'.")
    task: str = Field(..., description="What the code agent must accomplish in this step (1 paragraph).")
    target_paths: List[str] = Field(
        default_factory=list,
        description="Repo paths this step creates or edits (1-3).",
    )
    depends_on: List[int] = Field(
        default_factory=list,
        description="0-based indices of EARLIER steps this step depends on.",
    )


class Plan(BaseModel):
    steps: List[PlanStep] = Field(default_factory=list)
    summary: str = Field(..., description="1-2 sentence description of the overall feature.")


# Sanity cap — a single finding shouldn't legitimately need more steps than
# this; anything larger is a runaway plan we trim and log.
_MAX_STEPS = 8


def _build_user_prompt(
    task: str,
    repo_full_name: str,
    primary_language: str,
    tech_stack: List[str],
    file_tree: List[str],
) -> str:
    stack = ", ".join(tech_stack) or "unknown"
    # Cap the tree so a huge repo doesn't blow the prompt; the model only
    # needs directory shape to pick plausible paths.
    tree_sample = "\n".join(sorted(file_tree)[:400])
    return (
        f"# Feature to decompose\n{task}\n\n"
        f"# Repo\n- Name: {repo_full_name}\n- Language: {primary_language}\n"
        f"- Stack: {stack}\n\n"
        f"# Repo file tree (sample)\n{tree_sample}\n\n"
        f"Produce the ordered Plan. Return ONLY the structured Plan object."
    )


def _topo_order(steps: List[PlanStep]) -> List[int]:
    """Return step indices in dependency-respecting order. Falls back to the
    given order on any cycle / out-of-range dependency (defensive — the model
    is told to emit topological order already)."""
    n = len(steps)
    visited = [0] * n  # 0=unseen, 1=on-stack, 2=done
    order: List[int] = []

    def visit(i: int) -> bool:
        if visited[i] == 2:
            return True
        if visited[i] == 1:
            return False  # cycle
        visited[i] = 1
        for dep in steps[i].depends_on:
            if 0 <= dep < n and dep != i:
                if not visit(dep):
                    return False
        visited[i] = 2
        order.append(i)
        return True

    for i in range(n):
        if visited[i] == 0:
            if not visit(i):
                return list(range(n))  # cycle -> trust the model's own order
    return order


class Decomposer:
    name = "decomposer"
    description = "Splits a multi-file feature into ordered Coder steps"

    def __init__(self, provider: Optional[BedrockProvider] = None) -> None:
        self._provider = provider

    def _get_provider(self) -> BedrockProvider:
        if self._provider is None:
            self._provider = BedrockProvider()
        return self._provider

    def plan(
        self,
        task: str,
        repo_full_name: str,
        primary_language: str = "Unknown",
        tech_stack: Optional[List[str]] = None,
        file_tree: Optional[List[str]] = None,
    ) -> Plan:
        """One smart-model call → ordered Plan. Always returns at least one
        step (synthesizes a single-step plan from the task if the model
        returns nothing)."""
        provider = self._get_provider()
        user_prompt = _build_user_prompt(
            task, repo_full_name, primary_language,
            tech_stack or [], file_tree or [],
        )
        logger.info("Decomposer.plan repo=%s", repo_full_name)
        result: Plan = provider.invoke_structured_sync(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema_class=Plan,
            deployment_hint="smart",
        )

        if not result.steps:
            logger.info("Decomposer: model returned 0 steps — synthesizing single step")
            return Plan(
                steps=[PlanStep(name="Implement feature", task=task, target_paths=[])],
                summary=result.summary or task[:120],
            )

        if len(result.steps) > _MAX_STEPS:
            logger.warning(
                "Decomposer: %d steps over cap %d — trimming",
                len(result.steps), _MAX_STEPS,
            )
            result.steps = result.steps[:_MAX_STEPS]

        # Reorder topologically so the orchestrator can dispatch sequentially.
        order = _topo_order(result.steps)
        result.steps = [result.steps[i] for i in order]
        return result
