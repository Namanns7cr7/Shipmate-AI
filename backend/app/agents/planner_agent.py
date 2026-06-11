"""
PlannerAgent — turns ONE verified Opportunity into an ordered ExecutionPlan.

Phase 1B. The Opportunity (from the 1A pipeline) already carries grounded
evidence, target_files, and a coarse suggested_approach. The PlannerAgent makes
one smart-model call that expands it into a dependency-ordered list of BuildSteps
— each a focused unit a single CoderOrchestrator.run_actuation can land — without
writing any code itself. It is the planning analogue of the Decomposer, but its
input is a structured Opportunity (not a free-text finding) and its output feeds
the PlanCritic before any execution.

Fail-open: if the provider is unavailable or the model returns nothing, it
synthesizes a single-step plan straight from the opportunity (so the route can
still show *a* plan, flagged ai_enhanced=False upstream) rather than raising.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.agent_schemas import BuildStep, ExecutionPlan, Opportunity
from app.services.llm_provider import get_provider

logger = logging.getLogger("shipmate.planner_agent")

_MAX_STEPS = 8

_SYSTEM_PROMPT = (
    "You are a senior engineer turning ONE approved improvement opportunity "
    "into an ordered, minimal implementation plan for a code-writing agent. "
    "You are given the opportunity (title, description, impact, suggested "
    "approach, cited evidence) and the repo's file tree. Produce the FEWEST "
    "steps that actually deliver it.\n\n"
    "HARD RULES:\n"
    "  • Each step touches 1-3 files and is independently implementable by a "
    "code agent in one focused patch.\n"
    "  • Order steps topologically — a step may only depend on EARLIER steps. "
    "Express that via depends_on (1-based indices of earlier steps).\n"
    "  • Every target_files path must be real/plausible: prefer paths from the "
    "opportunity's target_files and the file tree; for new files follow the "
    "repo's existing directory conventions.\n"
    "  • Do NOT invent scope beyond the opportunity. 1-4 steps is typical. A "
    "single-file opportunity is a single step.\n"
    "  • Do NOT write code — only describe what each step accomplishes in its "
    "description (one short paragraph the code agent will act on).\n"
    "  • `kind` should be one of: milestone, blocker, test, guardrail, "
    "next_action — pick whichever best matches the step (most are 'milestone').\n"
    "Return ONLY the structured plan object."
)


class _PlannedStep(BaseModel):
    title: str = Field(..., description="Short imperative label.")
    description: str = Field(..., description="What the code agent must accomplish (1 paragraph).")
    target_files: List[str] = Field(default_factory=list, description="Repo paths this step creates/edits (1-3).")
    depends_on: List[int] = Field(default_factory=list, description="1-based indices of EARLIER steps this depends on.")
    kind: str = Field("milestone", description="milestone|blocker|test|guardrail|next_action.")
    rationale: str = Field("", description="Why this step, citing code where possible.")


class _PlannerOutput(BaseModel):
    summary: str = Field(..., description="1-2 sentence overview of the plan.")
    steps: List[_PlannedStep] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list, description="Assumptions/caveats, if any.")


_VALID_KINDS = {"milestone", "blocker", "test", "guardrail", "next_action"}


def _topo_order(steps: List[_PlannedStep]) -> List[int]:
    """Return step indices in dependency-respecting order (depends_on is 1-based).
    Falls back to given order on any cycle / out-of-range dep."""
    n = len(steps)
    visited = [0] * n
    order: List[int] = []

    def visit(i: int) -> bool:
        if visited[i] == 2:
            return True
        if visited[i] == 1:
            return False
        visited[i] = 1
        for dep in steps[i].depends_on:
            j = dep - 1  # 1-based -> 0-based
            if 0 <= j < n and j != i:
                if not visit(j):
                    return False
        visited[i] = 2
        order.append(i)
        return True

    for i in range(n):
        if visited[i] == 0 and not visit(i):
            return list(range(n))
    return order


class PlannerAgent:
    name = "planner"
    description = "Expands a verified Opportunity into an ordered ExecutionPlan"

    def __init__(self, provider=None) -> None:
        self._provider = provider

    def _get_provider(self):
        if self._provider is None:
            self._provider = get_provider()
        return self._provider

    def plan(self, opp: Opportunity, file_tree: Optional[List[str]] = None) -> ExecutionPlan:
        """One smart-model call → ordered ExecutionPlan. Always returns at least
        one step; on any failure, synthesizes a single step from the opportunity
        (fail-open) so the caller can always show a plan."""
        try:
            provider = self._get_provider()
        except Exception as e:
            logger.warning("Planner: provider unavailable (%s); synthesizing single-step plan", e)
            return self._fallback_plan(opp)

        try:
            out: _PlannerOutput = provider.invoke_structured_sync(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=self._user_prompt(opp, file_tree or []),
                schema_class=_PlannerOutput,
                deployment_hint="smart",
            )
        except Exception as e:
            logger.warning("Planner: model call failed (%s); synthesizing single-step plan", e)
            return self._fallback_plan(opp)

        if not out.steps:
            return self._fallback_plan(opp, summary=out.summary)

        steps = out.steps[:_MAX_STEPS]
        order = _topo_order(steps)            # list of ORIGINAL array indices, new order
        ordered = [steps[i] for i in order]
        # Remap dependencies: the model's depends_on are 1-based indices into its
        # ORIGINAL ordering. After topo reordering those numbers are stale, so we
        # translate each old 1-based index to its new 1-based position. (This is
        # the bug the topo test caught: without remap, a real dep gets dropped.)
        old1_to_new1 = {orig_idx + 1: new_pos + 1 for new_pos, orig_idx in enumerate(order)}

        build_steps: List[BuildStep] = []
        for idx, s in enumerate(ordered, start=1):
            kind = (s.kind or "milestone").lower()
            if kind not in _VALID_KINDS:
                kind = "milestone"
            remapped = sorted({
                old1_to_new1[d] for d in (s.depends_on or [])
                if isinstance(d, int) and d in old1_to_new1 and old1_to_new1[d] < idx
            })
            build_steps.append(BuildStep(
                index=idx,
                title=(s.title or f"Step {idx}").strip()[:120],
                description=(s.description or "").strip(),
                target_files=[t.strip() for t in (s.target_files or []) if t.strip()][:3],
                depends_on=remapped,
                kind=kind,
                rationale=(s.rationale or "").strip()[:400],
            ))

        # Grounded if every step cites at least one target file (planner had real
        # paths to work with) — a soft signal the PlanCritic refines.
        grounded = all(bs.target_files for bs in build_steps)
        return ExecutionPlan(
            opportunity_id=opp.id,
            opportunity_title=opp.title,
            summary=(out.summary or opp.title).strip(),
            steps=build_steps,
            estimated_days=opp.estimated_days,
            grounded=grounded,
            notes=[n.strip() for n in (out.notes or []) if n.strip()][:5],
        )

    def _fallback_plan(self, opp: Opportunity, summary: str = "") -> ExecutionPlan:
        """Single-step plan synthesized directly from the opportunity."""
        return ExecutionPlan(
            opportunity_id=opp.id,
            opportunity_title=opp.title,
            summary=summary or opp.title,
            steps=[BuildStep(
                index=1,
                title=opp.title[:120],
                description=opp.description or opp.impact or opp.title,
                target_files=list(opp.target_files or [])[:3],
                depends_on=[],
                kind="milestone" if opp.category != "bug" else "blocker",
                rationale=opp.rationale or "",
            )],
            estimated_days=opp.estimated_days,
            grounded=bool(opp.target_files),
            notes=["single-step fallback plan (planner LLM unavailable or returned no steps)"],
        )

    def _user_prompt(self, opp: Opportunity, file_tree: List[str]) -> str:
        approach = "\n".join(f"  - {s}" for s in (opp.suggested_approach or [])) or "  (none provided)"
        evidence = "\n".join(f"  - {e}" for e in (opp.evidence or [])) or "  (none provided)"
        tree_sample = "\n".join(sorted(file_tree)[:400])
        return (
            f"# Opportunity to plan\n"
            f"- Title: {opp.title}\n"
            f"- Category: {opp.category}\n"
            f"- Description: {opp.description}\n"
            f"- Impact: {opp.impact}\n"
            f"- Effort: {opp.effort} (~{opp.estimated_days} days)\n"
            f"- Target files (from discovery):\n"
            + ("\n".join(f"  - {t}" for t in (opp.target_files or [])) or "  (none)")
            + f"\n- Suggested approach:\n{approach}\n"
            f"- Evidence:\n{evidence}\n\n"
            f"# Repo file tree (sample)\n{tree_sample}\n\n"
            "Produce the ordered ExecutionPlan. Keep it minimal and in-scope. "
            "Return ONLY the structured plan object."
        )
