"""
Coder agent — generates full file contents for a focused patch.

Different shape from the 4 diagnostic agents:
  • RepoLens / PlanForge / GuardRail / TestPilot take a `context: Dict` and
    return Pydantic *report* outputs (heuristic + LLM-enhanced prose).
  • Coder takes a focused brief — one finding + 1–5 target files — and
    returns full new file contents that will be committed verbatim.

Why full files (not diffs):
  LLMs reliably emit valid full files; unified diffs frequently fail to apply
  (line drift, whitespace). The GitHub Contents API takes full content
  anyway — full-file output is the natural shape.

Failure semantics:
  Bedrock unreachable / schema-validation / token cap → caller (orchestrator)
  catches and returns a 500 with the actual error. We do NOT silently fall
  back to a stub here — the user clicked "Apply Fix" expecting real work.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.services.bedrock_provider import BedrockProvider

logger = logging.getLogger("shipmate.coder_agent")

_SYSTEM_PROMPT = (
    "You are a senior staff engineer producing a focused, surgical patch on "
    "behalf of an AI release-readiness platform called ShipMate.\n\n"
    "You will receive: (a) a single task, (b) compact repo context, "
    "(c) the current contents of 1-5 target files. For each file you choose "
    "to change, output the COMPLETE new file content — no diffs, no '...', "
    "no placeholders, no truncation. Match existing style: indentation, "
    "import order, naming. Don't refactor untouched code. Don't introduce "
    "new dependencies unless the task strictly requires it. If a file in "
    "`target_files` doesn't actually need to change for this task, list its "
    "path under `skipped`. Hard cap: 5 modified files. If the task requires "
    "creating a new file (e.g. .github/workflows/ci.yml or a test file), "
    "include it in `files` with the new path and full content; the existing "
    "content for new files will be empty. Provide a one-sentence rationale "
    "per file. Provide a 1-2 sentence overall `summary` describing what the "
    "patch does and why it addresses the task."
)


class CoderFile(BaseModel):
    path: str = Field(..., description="Relative repo path, e.g. 'app/main.py' or '.github/workflows/ci.yml'.")
    new_content: str = Field(..., description="Complete new file content, no diff syntax, no truncation.")
    rationale: str = Field(..., description="One sentence explaining why this file changed.")


class CoderOutput(BaseModel):
    files: List[CoderFile] = Field(default_factory=list)
    skipped: List[str] = Field(default_factory=list, description="Paths from target_files that did not need changes.")
    summary: str = Field(..., description="1-2 sentence summary of what the patch does and why.")


class CoderBrief(BaseModel):
    """Everything Coder needs to produce a patch — built by the orchestrator."""
    task: str
    repo_full_name: str
    primary_language: str = "Unknown"
    tech_stack: List[str] = Field(default_factory=list)
    entry_points: List[str] = Field(default_factory=list)
    target_files: Dict[str, str] = Field(default_factory=dict, description="path -> current content (empty for new files)")
    finding_kind: str
    finding_id: str
    finding_severity: Optional[str] = None


def _truncate_for_prompt(content: str, max_chars: int = 30_000) -> str:
    if len(content) <= max_chars:
        return content
    head = content[: max_chars - 200]
    return (
        head
        + f"\n\n# ... [truncated by ShipMate; original {len(content)} chars]\n"
    )


def _format_files_block(target_files: Dict[str, str]) -> str:
    parts: List[str] = []
    for path, content in target_files.items():
        body = _truncate_for_prompt(content) if content else "(new file — does not exist yet)"
        parts.append(f"### File: {path}\n```\n{body}\n```")
    return "\n\n".join(parts) if parts else "(no target files supplied)"


def _build_user_prompt(brief: CoderBrief) -> str:
    stack = ", ".join(brief.tech_stack) or "unknown"
    entries = ", ".join(brief.entry_points[:5]) or "unknown"
    return (
        f"# Task\n{brief.task}\n\n"
        f"# Repo\n"
        f"- Name: {brief.repo_full_name}\n"
        f"- Primary language: {brief.primary_language}\n"
        f"- Tech stack: {stack}\n"
        f"- Entry points: {entries}\n"
        f"- Originating finding: {brief.finding_kind}/{brief.finding_id}"
        f"{f' (severity {brief.finding_severity})' if brief.finding_severity else ''}\n\n"
        f"# Target files\n{_format_files_block(brief.target_files)}\n\n"
        f"Produce the patch. Return ONLY the structured CoderOutput object."
    )


class CoderAgent:
    name = "coder"
    description = "Generates full file contents to remediate a single finding"

    def __init__(self, provider: Optional[BedrockProvider] = None) -> None:
        self._provider = provider

    def _get_provider(self) -> BedrockProvider:
        if self._provider is None:
            self._provider = BedrockProvider()
        return self._provider

    def run(
        self,
        brief: CoderBrief,
        deployment_hint: Literal["smart", "fast"] = "smart",
    ) -> CoderOutput:
        """
        Synchronous (the underlying Bedrock SDK is sync; we call the
        `_sync` variant to stay safe inside FastAPI's running event loop —
        the route awaits us via `asyncio.to_thread`).
        """
        provider = self._get_provider()
        user_prompt = _build_user_prompt(brief)

        logger.info(
            "Coder.run kind=%s id=%s files=%d hint=%s",
            brief.finding_kind, brief.finding_id, len(brief.target_files), deployment_hint,
        )

        result = provider.invoke_structured_sync(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema_class=CoderOutput,
            deployment_hint=deployment_hint,
        )
        # Hard cap defense (in case Bedrock ignores the prompt cap).
        if len(result.files) > 5:
            logger.warning("Coder returned %d files; truncating to 5", len(result.files))
            result.files = result.files[:5]
        return result
