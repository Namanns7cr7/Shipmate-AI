"""
Anthropic API provider for ShipMate agents.

Drop-in replacement for BedrockProvider — implements the same
`invoke_structured_sync()` contract using the Anthropic Python SDK
with tool-use to force structured JSON output.

Set LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY=sk-... to enable.
This works anywhere without AWS credentials, making it the best choice
for demos and development.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Type

from pydantic import BaseModel

logger = logging.getLogger("shipmate.anthropic_provider")

# Default model — claude-haiku-4-5 is fast and cheap for enhancement passes.
# Override with ANTHROPIC_MODEL env var for smarter output.
_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_SMART_MODEL = "claude-sonnet-4-6"


class AnthropicProvider:
    """Wraps the Anthropic SDK to match BedrockProvider's interface."""

    def __init__(self):
        try:
            import anthropic as _anthropic
            self._anthropic = _anthropic
        except ImportError as e:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from e

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY env var is not set")

        self._client = self._anthropic.Anthropic(api_key=api_key)
        logger.info("AnthropicProvider ready (model=%s)", _DEFAULT_MODEL)

    def invoke_with_lint_feedback(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_class: Type[BaseModel],
        lint_issues: list,
        deployment_hint: str = "smart",
    ) -> BaseModel:
        """Re-invoke after lint rejection — same as BedrockProvider's contract."""
        issues_block = "\n".join(f"  - {i}" for i in lint_issues)
        feedback_user = (
            user_prompt
            + "\n\n# LINT REJECTION — CORRECT AND RESUBMIT\n"
            "Your previous patch was rejected by automated lint for:\n"
            f"{issues_block}\n"
            "Produce a corrected patch that resolves every issue above. "
            "Return ONLY the structured object."
        )
        return self.invoke_structured_sync(
            system_prompt, feedback_user, schema_class, deployment_hint,
        )

    def invoke_structured_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_class: Type[BaseModel],
        deployment_hint: str = "fast",
    ) -> BaseModel:
        """
        Call Claude with tool-use to force structured output matching
        `schema_class`. Returns a validated Pydantic instance.

        deployment_hint:
          "fast"  → claude-haiku (default, cheap)
          "smart" → claude-sonnet (discovery passes)
        """
        model = _SMART_MODEL if deployment_hint == "smart" else _DEFAULT_MODEL
        model = os.getenv("ANTHROPIC_MODEL", model)

        schema_name = schema_class.__name__
        json_schema = schema_class.model_json_schema()

        tools = [{
            "name": schema_name,
            "description": f"Return the structured {schema_name} output.",
            "input_schema": json_schema,
        }]

        response = self._client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": schema_name},
        )

        # Extract tool-use block
        for block in response.content:
            if block.type == "tool_use" and block.name == schema_name:
                raw: Any = block.input
                if isinstance(raw, str):
                    raw = json.loads(raw)
                return schema_class.model_validate(raw)

        raise ValueError(
            f"AnthropicProvider: no tool_use block in response for {schema_name}"
        )
