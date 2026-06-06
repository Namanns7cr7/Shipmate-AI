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

# A CoderOutput with files but a near-empty summary is a known flaky-output
# signature (the model emitted a patch but truncated its reasoning). We retry
# once with a tighter prompt. 30 chars ≈ "Fixes the bug." — anything shorter
# alongside a real patch is suspect.
_MIN_CODER_SUMMARY_CHARS = 30


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


def _shrink_oversized_file_blocks(user_prompt: str, threshold: int = 8_000) -> str:
    """Halve the size of any single oversized region in the prompt to free
    token budget for the model's own output on a short-summary retry.

    We don't parse the prompt structure (it's built by coder_agent), we just
    cap total length: if the prompt exceeds 2*threshold, keep the head (task +
    early files) and the tail, dropping the middle with a marker. This biases
    toward preserving the task framing and the most-recently-listed file,
    which is usually the edit target.
    """
    if len(user_prompt) <= 2 * threshold:
        return user_prompt
    head = user_prompt[:threshold]
    tail = user_prompt[-threshold:]
    dropped = len(user_prompt) - 2 * threshold
    return (
        head
        + f"\n\n# ... [ShipMate retry: dropped {dropped} chars of file context "
        "to free output budget; focus on the task and the file content shown] ...\n\n"
        + tail
    )


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
            result = schema_class.model_validate(coerced)
            # Flaky-output guard: a CoderOutput that has files but an almost
            # empty summary is a sign the model truncated. Retry once with a
            # shrunk context (drop the back half of oversized target-file
            # blocks so the model has more budget for its reasoning).
            result = self._maybe_retry_short_summary(
                result, schema_class, model_id, tool_name, schema,
                system_prompt, user_prompt, max_tokens,
            )
            return result
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
                result = schema_class.model_validate(coerced)
                return self._maybe_retry_short_summary(
                    result, schema_class, model_id, tool_name, schema,
                    system_prompt, user_prompt, max_tokens,
                )

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

    @staticmethod
    def _is_short_summary_coder_output(result: BaseModel) -> bool:
        """True when *result* is a CoderOutput carrying a patch but an
        implausibly short summary (a flaky-truncation signature)."""
        if type(result).__name__ != "CoderOutput":
            return False
        files = getattr(result, "files", None) or []
        summary = getattr(result, "summary", "") or ""
        return len(files) > 0 and len(summary.strip()) < _MIN_CODER_SUMMARY_CHARS

    def _maybe_retry_short_summary(
        self,
        result: BaseModel,
        schema_class: Type[BaseModel],
        model_id: str,
        tool_name: str,
        schema: dict,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> BaseModel:
        """One-shot retry when a CoderOutput came back with files but a
        near-empty summary. Shrinks oversized target-file blocks in the
        prompt to free token budget, then re-invokes once. If the retry is
        ALSO short, keep whichever has the longer summary (never worse)."""
        if not self._is_short_summary_coder_output(result):
            return result
        logger.warning(
            "BedrockProvider: CoderOutput summary suspiciously short "
            "(%d chars, %d files) — retrying once with shrunk context",
            len(getattr(result, "summary", "") or ""),
            len(getattr(result, "files", []) or []),
        )
        shrunk_user = _shrink_oversized_file_blocks(user_prompt)
        try:
            payload = self._call_converse(
                model_id, tool_name, schema, system_prompt, shrunk_user, max_tokens
            )
            coerced = _coerce_stringified_json(payload)
            retried = schema_class.model_validate(coerced)
        except Exception as e:
            logger.info("short-summary retry failed (%s); keeping first result", e)
            return result
        # Prefer whichever summary is longer — the retry isn't guaranteed better.
        first_len = len(getattr(result, "summary", "") or "")
        retry_len = len(getattr(retried, "summary", "") or "")
        return retried if retry_len >= first_len else result

    def invoke_with_lint_feedback(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_class: Type[BaseModel],
        lint_issues: list[str],
        deployment_hint: Literal["smart", "fast"] = "smart",
    ) -> BaseModel:
        """Re-invoke after a patch was rejected by post-Coder lint. Appends an
        explicit fix-up notice listing the issues so the model corrects them
        rather than re-emitting the same mistake. Reuses the full
        invoke_structured_sync path (auth-retry, validation-retry,
        short-summary retry all still apply)."""
        issues_block = "\n".join(f"  - {i}" for i in lint_issues)
        feedback_user = (
            user_prompt
            + "\n\n# LINT REJECTION — CORRECT AND RESUBMIT\n"
            "Your previous patch was rejected by automated lint for:\n"
            f"{issues_block}\n"
            "Produce a corrected patch that resolves every issue above. Do not "
            "reintroduce them. If an issue was a hallucinated import or symbol, "
            "either add the missing definition to a file in `files` or remove "
            "the reference. Return ONLY the structured object."
        )
        logger.info(
            "BedrockProvider: re-invoking with lint feedback (%d issue(s))",
            len(lint_issues),
        )
        return self.invoke_structured_sync(
            system_prompt, feedback_user, schema_class, deployment_hint,
        )

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
