"""
LLM enhancement layer.

The 4 agents (RepoLens, PlanForge, GuardRail, TestPilot) compute deterministic
heuristic outputs first — file counts, has_tests flags, score formulas. After
that they hand the result to `LLMService.enhance(...)`, which optionally calls
an LLM to **rewrite the prose fields** (milestone descriptions, blocker
resolutions, security recommendations, suggested-test prose) so they read as
specific to *this* repo instead of generic templates.

What's enhanced (per agent):
  - PlanForge:  milestones[].description, blockers[].resolution,
                next_best_action, dependencies (order/clarity).
  - GuardRail:  findings[].description, findings[].recommendation.
  - TestPilot:  suggested_tests[].description, missing_coverage_areas.
  - RepoLens:   (skipped — every field is heuristic, no template prose).

What's NEVER touched:
  - Numeric scores (repo_score, delivery_score, security_score, test_score).
  - Booleans (has_tests, has_ci_cd, has_dockerfile).
  - Counts (file_count, test count, finding count).
  - Field shapes — we only update existing fields, never add/remove.

If the LLM provider is unavailable, the call fails, or the response can't be
parsed, `enhance(...)` returns `base_output` unchanged. The deterministic
score and verdict are always present even with no Bedrock access.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field

from app.schemas.agent_schemas import (
    GuardRailOutput, PlanForgeOutput, TestPilotOutput,
)

logger = logging.getLogger("shipmate.llm_service")

# ── Provider singleton ──────────────────────────────────────────────────────
# Lazily created on first use; cached for the process lifetime. The provider
# itself logs init failures (e.g. expired ADA creds) and falls back to None
# so subsequent enhance() calls cheaply short-circuit.
_provider: Optional[Any] = None
_provider_init_attempted = False


def _get_provider():
    """Return a Bedrock provider singleton, or None if unavailable."""
    global _provider, _provider_init_attempted
    if _provider_init_attempted:
        return _provider
    _provider_init_attempted = True

    kind = os.getenv("LLM_PROVIDER", "").lower()
    if kind != "bedrock":
        logger.info("LLMService: LLM_PROVIDER=%r → enhancements disabled", kind or "(unset)")
        return None

    try:
        from app.services.bedrock_provider import BedrockProvider
        _provider = BedrockProvider()
        logger.info("LLMService: BedrockProvider ready")
    except Exception as e:
        logger.warning("LLMService: BedrockProvider init failed (%s); enhancements disabled", e)
        _provider = None
    return _provider


# ── Per-agent enhancement schemas ────────────────────────────────────────────
# These are *partial* projections of the agent output schemas. Bedrock fills
# only these prose-y fields; we then merge them back into the heuristic
# base_output via Pydantic `model_copy(update=...)`.

class _MilestoneEnhancement(BaseModel):
    title: str = Field(..., description="Same milestone title from the input plan, repeated verbatim.")
    description: str = Field(..., description="2-sentence repo-specific description of what to do and why it matters here.")


class _BlockerEnhancement(BaseModel):
    id: str = Field(..., description="Blocker id from input, verbatim.")
    resolution: str = Field(..., description="One-paragraph concrete resolution tailored to this repo's tech stack and current state.")


class PlanForgeEnhancement(BaseModel):
    """Prose-only fields PlanForge can have rewritten."""
    milestones: List[_MilestoneEnhancement] = Field(..., description="Same length as input milestones; same titles in same order.")
    blockers: List[_BlockerEnhancement] = Field(..., description="Same length as input blockers; same ids in same order.")
    next_best_action: str = Field(..., description="One actionable sentence — what to do RIGHT NOW given the repo state.")


class _FindingEnhancement(BaseModel):
    id: str = Field(..., description="Finding id from input, verbatim.")
    description: str = Field(..., description="2-3 sentences explaining the actual risk in this repo.")
    recommendation: str = Field(..., description="2-3 concrete steps the team should take to fix it.")


class GuardRailEnhancement(BaseModel):
    """Prose-only fields GuardRail can have rewritten."""
    findings: List[_FindingEnhancement] = Field(..., description="Same length as input findings; same ids in same order.")


class _SuggestedTestEnhancement(BaseModel):
    name: str = Field(..., description="Test name from input, verbatim.")
    description: str = Field(..., description="2 sentences: what this test should cover and why, given the repo's stack.")


class TestPilotEnhancement(BaseModel):
    """Prose-only fields TestPilot can have rewritten."""
    suggested_tests: List[_SuggestedTestEnhancement] = Field(..., description="Same length and order as input.")
    missing_coverage_areas: List[str] = Field(..., description="Same length and order as input; rephrase each item to be specific to this repo.")


# ── Prompt builders ─────────────────────────────────────────────────────────

def _repo_summary(context: Dict[str, Any]) -> str:
    """A compact text blob describing the repo for the system prompt."""
    info = context.get("repo_info") or {}
    repo_lens = context.get("repo_lens")

    parts = [
        f"Repo: {info.get('full_name', '?')}",
        f"Default branch: {context.get('branch', 'main')}",
    ]
    if info.get("description"):
        parts.append(f"Description: {info['description']}")
    if repo_lens is not None:
        # repo_lens is a Pydantic model
        parts.append(f"Tech stack: {', '.join(repo_lens.tech_stack) or '(unknown)'}")
        parts.append(f"Primary language: {repo_lens.primary_language}")
        parts.append(f"Architecture pattern: {repo_lens.architecture_pattern}")
        parts.append(f"Has CI/CD: {repo_lens.has_ci_cd} · Dockerfile: {repo_lens.has_dockerfile} · Tests: {repo_lens.has_tests}")
        parts.append(f"File count: {repo_lens.file_count}")
        if repo_lens.key_modules:
            parts.append(f"Key modules: {', '.join(repo_lens.key_modules[:8])}")
        if repo_lens.entry_points:
            parts.append(f"Entry points: {', '.join(repo_lens.entry_points[:5])}")
        if repo_lens.architecture_risks:
            risks = "; ".join(r.risk for r in repo_lens.architecture_risks[:5])
            parts.append(f"Architecture risks: {risks}")
    feature_ctx = context.get("feature_context")
    if feature_ctx:
        parts.append(f"Feature in scope: {feature_ctx[:300]}")
    return "\n".join(parts)


_AGENT_SYSTEM_PROMPTS: Dict[str, str] = {
    "plan_forge": (
        "You are a senior staff engineer reviewing a repo's release readiness. "
        "Given a deterministic delivery plan (milestones + blockers + a next-best-action), "
        "rewrite the PROSE so each item is concrete and specific to *this* repo's tech "
        "stack, file layout, and current state. Preserve every milestone title and blocker "
        "id verbatim. Do not invent new milestones or blockers."
    ),
    "guardrail": (
        "You are an application-security engineer reviewing findings from a static analysis pass. "
        "For each finding, rewrite the description so it explains the actual risk in *this* repo, "
        "and rewrite the recommendation as 2-3 concrete remediation steps. Preserve every finding "
        "id verbatim. Do not invent new findings or change severities."
    ),
    "testpilot": (
        "You are a QA lead. Given suggested tests and a list of coverage gaps, rewrite the prose "
        "so each test description and gap is specific to this repo's stack and entry points. "
        "Preserve every test name verbatim. Do not invent new tests; do not remove items."
    ),
}


def _user_prompt(agent_name: str, context: Dict[str, Any], base_output_dict: Dict[str, Any]) -> str:
    return (
        f"# Repo summary\n{_repo_summary(context)}\n\n"
        f"# Current {agent_name} output (rewrite the PROSE fields only):\n"
        f"{json.dumps(base_output_dict, indent=2)[:6000]}\n\n"
        f"Return ONLY the requested enhancement schema. Match item ids/titles exactly."
    )


# ── Core enhance() — sync wrapper around the async provider call ────────────

T = TypeVar("T", bound=BaseModel)

_AGENT_TO_SCHEMA: Dict[str, Type[BaseModel]] = {
    "plan_forge": PlanForgeEnhancement,
    "guardrail":  GuardRailEnhancement,
    "testpilot":  TestPilotEnhancement,
}


def _merge_plan_forge(base: PlanForgeOutput, enh: PlanForgeEnhancement) -> PlanForgeOutput:
    # Match enriched milestones/blockers back by title/id, preserving order + length.
    milestone_map = {m.title: m.description for m in enh.milestones}
    blocker_map = {b.id: b.resolution for b in enh.blockers}
    new_milestones = [m.model_copy(update={"description": milestone_map.get(m.title, m.description)})
                       for m in base.milestones]
    new_blockers = [b.model_copy(update={"resolution": blocker_map.get(b.id, b.resolution)})
                     for b in base.blockers]
    return base.model_copy(update={
        "milestones": new_milestones,
        "blockers": new_blockers,
        "next_best_action": enh.next_best_action or base.next_best_action,
    })


def _merge_guardrail(base: GuardRailOutput, enh: GuardRailEnhancement) -> GuardRailOutput:
    finding_map = {f.id: (f.description, f.recommendation) for f in enh.findings}
    new_findings = []
    for f in base.findings:
        upd = finding_map.get(f.id)
        if upd:
            new_findings.append(f.model_copy(update={"description": upd[0], "recommendation": upd[1]}))
        else:
            new_findings.append(f)
    return base.model_copy(update={"findings": new_findings})


def _merge_testpilot(base: TestPilotOutput, enh: TestPilotEnhancement) -> TestPilotOutput:
    desc_map = {t.name: t.description for t in enh.suggested_tests}
    new_tests = [t.model_copy(update={"description": desc_map.get(t.name, t.description)})
                 for t in base.suggested_tests]
    new_gaps = list(enh.missing_coverage_areas) if enh.missing_coverage_areas else base.missing_coverage_areas
    return base.model_copy(update={
        "suggested_tests": new_tests,
        "missing_coverage_areas": new_gaps,
    })


_MERGERS = {
    "plan_forge": _merge_plan_forge,
    "guardrail":  _merge_guardrail,
    "testpilot":  _merge_testpilot,
}


class LLMService:
    """Static helpers that 3 agents call after their heuristic compute."""

    _enabled: Optional[bool] = None

    @classmethod
    def is_available(cls) -> bool:
        if cls._enabled is None:
            cls._enabled = _get_provider() is not None
        return cls._enabled

    @classmethod
    def enhance(cls, agent_name: str, context: Dict[str, Any], base_output: T) -> T:
        """
        Optionally rewrite prose fields on `base_output` using the configured
        LLM provider. Synchronous — agents are sync. On any failure, returns
        `base_output` unchanged.
        """
        provider = _get_provider()
        if provider is None:
            return base_output

        schema = _AGENT_TO_SCHEMA.get(agent_name)
        merger = _MERGERS.get(agent_name)
        if schema is None or merger is None:
            return base_output

        system = _AGENT_SYSTEM_PROMPTS[agent_name]
        user = _user_prompt(agent_name, context, base_output.model_dump())

        try:
            enhancement = provider.invoke_structured_sync(
                system_prompt=system,
                user_prompt=user,
                schema_class=schema,
                deployment_hint="smart" if agent_name == "guardrail" else "fast",
            )
        except Exception as e:
            logger.warning("LLM enhance failed for %s: %s; using base output", agent_name, e)
            return base_output

        try:
            return merger(base_output, enhancement)
        except Exception as e:
            logger.warning("LLM enhance merge failed for %s: %s; using base output", agent_name, e)
            return base_output

    # Kept for backward compatibility with the old async stub signature, in
    # case something starts importing it later.
    @classmethod
    async def enhance_analysis(cls, agent_name: str, context: dict, base_output: dict) -> dict:
        return base_output
