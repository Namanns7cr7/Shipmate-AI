"""
PlanCritic — gates an ExecutionPlan before any code is written (Phase 1B).

Two layers, mirroring the finding/opportunity critics:

  1. DETERMINISTIC (always on, no LLM): structural sanity the model shouldn't be
     trusted to self-report — empty plan, dependency cycles / forward refs,
     duplicate steps, runaway step count, or steps with no target files. These
     are cheap, reliable, and catch the failure modes that would make execution
     blow up.

  2. LLM (optional, fail-open): a skeptic reads the plan + the opportunity and
     judges coherence (steps form a sensible whole), completeness (nothing
     obviously missing to ship it), and scope (no creep beyond the opportunity).

A plan is approved only if the deterministic layer is clean AND (the LLM layer
approves OR is unavailable). Fail-open on the LLM axis: if the critic can't run,
we don't block on it — the deterministic layer is the hard gate, and every step
still passes through CoderOrchestrator's own lint/scope/pytest gates at execution
time, so an over-eager plan can't actually ship bad code.
"""
from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.schemas.agent_schemas import ExecutionPlan, PlanCritique

logger = logging.getLogger("shipmate.plan_critic")

_MAX_STEPS = 8
_LLM_ENABLED = os.getenv("SHIPMATE_PLAN_CRITIC", "1").strip().lower() not in ("0", "false", "no")


# ── Deterministic structural checks ──────────────────────────────────────────

def _structural_issues(plan: ExecutionPlan) -> List[str]:
    issues: List[str] = []
    steps = plan.steps or []
    if not steps:
        issues.append("plan has no steps")
        return issues
    if len(steps) > _MAX_STEPS:
        issues.append(f"plan has {len(steps)} steps (cap {_MAX_STEPS}) — likely scope creep")

    indices = [s.index for s in steps]
    if sorted(indices) != list(range(1, len(steps) + 1)):
        issues.append(f"step indices are not a clean 1..N sequence: {indices}")

    # Dependencies must reference EARLIER steps only (no cycles / forward refs).
    for s in steps:
        for dep in s.depends_on:
            if dep >= s.index:
                issues.append(f"step {s.index} depends on {dep} which is not an earlier step (cycle/forward-ref)")
            if dep < 1 or dep > len(steps):
                issues.append(f"step {s.index} depends on out-of-range step {dep}")

    # Duplicate step titles (case-insensitive) usually mean a redundant plan.
    seen = set()
    for s in steps:
        key = (s.title or "").strip().lower()
        if key and key in seen:
            issues.append(f"duplicate step title: {s.title!r}")
        seen.add(key)

    # A step with no target files is unactionable for the Coder.
    no_targets = [s.index for s in steps if not s.target_files]
    if no_targets:
        issues.append(f"step(s) {no_targets} have no target_files — Coder has nothing to edit")

    return issues


# ── LLM judgement ────────────────────────────────────────────────────────────

class _PlanVerdict(BaseModel):
    coherent: bool = Field(..., description="Do the steps form a sensible, ordered whole?")
    complete: bool = Field(..., description="Is anything obviously missing to actually ship this opportunity?")
    in_scope: bool = Field(..., description="Do the steps stay within the opportunity (no scope creep)?")
    issues: List[str] = Field(default_factory=list, description="Specific problems, empty if clean.")
    reason: str = Field(..., description="One-sentence overall verdict.")


_LLM_SYSTEM = (
    "You are a skeptical staff engineer reviewing an implementation PLAN (not "
    "code) produced for a single improvement opportunity. Judge three things "
    "against the opportunity and the plan's steps:\n"
    "  • coherent — the steps form a sensible, correctly-ordered whole "
    "(dependencies make sense; no step presupposes work no earlier step does).\n"
    "  • complete — nothing obviously required to actually SHIP the opportunity "
    "is missing (e.g. a route added but never registered; a model with no "
    "migration). Don't demand gold-plating — just whether it would work.\n"
    "  • in_scope — the steps stay within the opportunity and don't sprawl into "
    "unrelated refactors or features.\n"
    "Be fair, not pedantic: a minimal plan that ships the opportunity is GOOD. "
    "List concrete issues only when they'd actually break or under-deliver the "
    "result. Return the structured verdict."
)


def _llm_issues(plan: ExecutionPlan, opportunity: Any, provider: Any) -> Optional[_PlanVerdict]:
    if not _LLM_ENABLED or provider is None:
        return None
    try:
        steps_txt = "\n".join(
            f"  {s.index}. [{s.kind}] {s.title} → files: {', '.join(s.target_files) or '(none)'} "
            f"(depends_on: {s.depends_on or '[]'})\n     {s.description[:200]}"
            for s in plan.steps
        )
        opp_txt = ""
        if opportunity is not None:
            opp_txt = (
                f"Title: {getattr(opportunity, 'title', '')}\n"
                f"Description: {getattr(opportunity, 'description', '')}\n"
                f"Impact: {getattr(opportunity, 'impact', '')}\n"
            )
        user = (
            f"## Opportunity\n{opp_txt}\n"
            f"## Proposed plan\nSummary: {plan.summary}\nSteps:\n{steps_txt}\n\n"
            "Judge coherent / complete / in_scope and list concrete issues."
        )
        return provider.invoke_structured_sync(
            system_prompt=_LLM_SYSTEM,
            user_prompt=user,
            schema_class=_PlanVerdict,
            deployment_hint="smart",
        )
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("plan critic LLM pass failed (%s); deterministic-only", e)
        return None


# ── Public entry ─────────────────────────────────────────────────────────────

def critique_plan(
    plan: ExecutionPlan,
    opportunity: Any = None,
    provider: Any = None,
) -> PlanCritique:
    """Return a PlanCritique. Approved iff the deterministic layer is clean AND
    the LLM layer approves (or is unavailable — fail-open on the LLM axis)."""
    structural = _structural_issues(plan)
    verdict = _llm_issues(plan, opportunity, provider)

    issues = list(structural)
    coherent = complete = in_scope = True
    if verdict is not None:
        coherent, complete, in_scope = verdict.coherent, verdict.complete, verdict.in_scope
        issues.extend(verdict.issues or [])
        llm_reason = verdict.reason
    else:
        llm_reason = "LLM plan critic unavailable — deterministic checks only"

    # Structural problems are a hard fail. LLM problems fail too, but only when
    # the LLM actually ran (verdict is not None).
    approved = not structural and (verdict is None or (coherent and complete and in_scope))

    if structural:
        reason = f"rejected on structural checks: {'; '.join(structural[:3])}"
    elif verdict is not None and not approved:
        flags = [n for n, ok in (("incoherent", coherent), ("incomplete", complete),
                                 ("out-of-scope", in_scope)) if not ok]
        reason = f"rejected by critic ({', '.join(flags)}): {llm_reason}"
    else:
        reason = llm_reason if verdict is not None else "approved (deterministic checks clean)"

    return PlanCritique(
        approved=approved,
        coherent=coherent,
        complete=complete,
        in_scope=in_scope,
        issues=issues,
        reason=reason,
    )
