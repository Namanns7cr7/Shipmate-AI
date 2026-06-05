"""
AWS Bedrock provider for ShipMate agents.

Implements the same `invoke_structured(...)` contract as
`AzureOpenAIProvider`, using Bedrock's Converse API with `toolConfig` to
force structured JSON output. The model is required to call a single tool
whose `inputSchema` is the Pydantic JSON schema; the resulting tool-use
block carries the validated JSON payload.

Why Converse + toolConfig (vs InvokeModel + per-model body):
  • Converse is a unified API across Anthropic / Llama / Mistral / Titan.
  • toolChoice={"tool": ...} guarantees the model emits structured JSON
    matching the schema — no markdown extraction, no regex, no "give me
    valid JSON" prompting.
  • boto3-only — no extra deps. The SDK is sync; we wrap calls with
    `asyncio.to_thread` exactly like AzureOpenAIProvider does.

Auth: relies on the standard boto3 credential provider chain. On the
Pharma-ASIN-Enrich-9 burner account, `ada credentials update` populates
the default profile at ~/.aws/credentials and boto3 picks it up
transparently — no AWS_PROFILE env var needed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Literal, Type

from pydantic import BaseModel

logger = logging.getLogger("shipmate.bedrock_provider")


def _coerce_stringified_json(value: Any) -> Any:
    """
    Recursively walk a payload and parse any string that looks like JSON.

    Bedrock's Converse toolUse blocks occasionally return nested arrays/objects
    as serialized JSON strings instead of native types — even when the tool
    inputSchema clearly types them as arrays/objects. This walks the structure
    and best-effort decodes those strings so Pydantic can validate normally.

    A string is treated as "looks like JSON" iff its first non-whitespace
    character is `[` or `{` — narrow enough to avoid corrupting freeform text
    fields (descriptions, summaries) that happen to start with other chars.
    """
    if isinstance(value, str):
        stripped = value.lstrip()
        if stripped[:1] in ("[", "{"):
            try:
                return _coerce_stringified_json(json.loads(value))
            except json.JSONDecodeError:
                return value
        return value
    if isinstance(value, list):
        return [_coerce_stringified_json(v) for v in value]
    if isinstance(value, dict):
        return {k: _coerce_stringified_json(v) for k, v in value.items()}
    return value


class BedrockProvider:
    """Bedrock Converse-API client returning Pydantic-validated objects."""

    def __init__(self) -> None:
        # Defer the boto3 import so a missing dep doesn't break the rest of
        # the app — the factory in llm_provider.py catches and falls back.
        import boto3

        from botocore.config import Config

        region = os.getenv("AWS_REGION", "us-west-2")
        # Default boto3 read timeout is 60s — Sonnet 4.6 producing a full
        # 4-list-of-objects schema (planner / repo_analyst) can exceed that.
        # Push to 5min and disable retries (we already have an outer fallback
        # at the agent layer; retrying inside boto3 just multiplies wall time).
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 1}),
        )
        # Defaults use cross-region inference profile IDs (`us.*`). The newer
        # Claude generation (Sonnet 4.6, Haiku 4.5) doesn't support direct
        # on-demand throughput — Bedrock requires invocation through an
        # inference profile so the request can route across regions.
        self.smart_model = os.getenv(
            "BEDROCK_MODEL_SMART",
            "us.anthropic.claude-sonnet-4-6",
        )
        self.fast_model = os.getenv(
            "BEDROCK_MODEL_FAST",
            "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        )
        logger.info(
            "BedrockProvider initialized (region=%s, smart=%s, fast=%s)",
            region, self.smart_model, self.fast_model,
        )

    def invoke_structured_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_class: Type[BaseModel],
        deployment_hint: Literal["smart", "fast"] = "smart",
    ) -> BaseModel:
        """Synchronous version. Safe to call from inside a running event loop
        (e.g. from a FastAPI request handler). The boto3 SDK is sync; we just
        skip the asyncio wrapping. Use this from `LLMService.enhance`.

        Includes a one-shot retry if Pydantic validation fails. Bedrock
        occasionally serialises nested complex fields (`files: [...]`) as a
        string with escape sequences that don't round-trip through json.loads
        — when that happens we re-prompt with an explicit reminder that the
        field must be a native JSON array, not a stringified one.
        """
        model_id = self.smart_model if deployment_hint == "smart" else self.fast_model
        tool_name = f"emit_{schema_class.__name__}"
        schema = schema_class.model_json_schema()
        max_tokens = 8192

        try:
            payload = self._call_converse(
                model_id, tool_name, schema, system_prompt, user_prompt, max_tokens
            )
            coerced = _coerce_stringified_json(payload)
            return schema_class.model_validate(coerced)
        except Exception as first_err:
            from pydantic import ValidationError as _VE
            err_str = str(first_err)
            # Auto-recover from expired creds: rebuild the boto3 client on
            # auth-class errors so the next call picks up freshly-refreshed
            # ADA creds without needing a process restart. The default
            # session caches credential providers, so simply discarding the
            # client and rebuilding it is what triggers the refresh.
            if any(m in err_str for m in (
                "ExpiredToken", "ExpiredTokenException",
                "InvalidSignatureException", "UnrecognizedClientException",
                "Signature expired",
            )):
                logger.warning(
                    "BedrockProvider: auth failure (%s) — rebuilding boto3 "
                    "client to pick up refreshed credentials, then retrying once",
                    type(first_err).__name__,
                )
                import boto3
                from botocore.config import Config
                self.client = boto3.client(
                    "bedrock-runtime",
                    region_name=os.getenv("AWS_REGION", "us-west-2"),
                    config=Config(read_timeout=300, connect_timeout=10,
                                  retries={"max_attempts": 1}),
                )
                payload = self._call_converse(
                    model_id, tool_name, schema, system_prompt, user_prompt, max_tokens
                )
                coerced = _coerce_stringified_json(payload)
                return schema_class.model_validate(coerced)

            is_validation = isinstance(first_err, _VE) or "validation error" in err_str.lower()
            if not is_validation:
                raise
            logger.warning(
                "BedrockProvider: structured-output validation failed (%s); "
                "retrying once with explicit array-not-string reminder",
                err_str[:200],
            )
            retry_user = (
                user_prompt
                + "\n\n# RETRY NOTICE\nA prior attempt returned the `files` field "
                "as a JSON-encoded STRING instead of a native JSON array, which "
                "broke parsing. Return `files` as a native JSON array of "
                "objects: `[{\"path\": ..., \"new_content\": ..., "
                "\"rationale\": ...}, ...]`. Do not stringify the array."
            )
            payload = self._call_converse(
                model_id, tool_name, schema, system_prompt, retry_user, max_tokens
            )
            coerced = _coerce_stringified_json(payload)
            return schema_class.model_validate(coerced)

    async def invoke_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_class: Type[BaseModel],
        deployment_hint: Literal["smart", "fast"] = "smart",
    ) -> BaseModel:
        """Async wrapper — kept for parallel multi-agent fan-out. Calls the
        sync implementation on a worker thread so we don't block the loop."""
        return await asyncio.to_thread(
            self.invoke_structured_sync,
            system_prompt, user_prompt, schema_class, deployment_hint,
        )

    def _call_converse(
        self,
        model_id: str,
        tool_name: str,
        schema: dict,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            resp = self.client.converse(
                modelId=model_id,
                system=[{"text": system_prompt}],
                messages=[
                    {"role": "user", "content": [{"text": user_prompt}]},
                ],
                inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2},
                toolConfig={
                    "tools": [
                        {
                            "toolSpec": {
                                "name": tool_name,
                                "description": (
                                    f"Emit a {tool_name} JSON object "
                                    f"matching the provided schema."
                                ),
                                "inputSchema": {"json": schema},
                            }
                        }
                    ],
                    # Force the model to call the tool — guarantees structured output.
                    "toolChoice": {"tool": {"name": tool_name}},
                },
            )

            for block in resp.get("output", {}).get("message", {}).get("content", []):
                if "toolUse" in block:
                    payload = block["toolUse"].get("input")
                    if payload is None:
                        raise RuntimeError(
                            f"Bedrock toolUse block had no `input` for {tool_name}"
                        )
                    return payload

            raise RuntimeError(
                f"Bedrock response contained no toolUse block for {tool_name}; "
                f"stopReason={resp.get('stopReason')!r}"
            )

        return _call()
