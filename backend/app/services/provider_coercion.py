"""
provider_coercion — ONE place for the response-normalization both LLM providers
need, so Bedrock and Azure stop carrying byte-identical copies of it.

Before this module, `bedrock_provider.py` and `azure_openai_provider.py` each
hand-rolled:
  • `_coerce_stringified_json`     — recursively json.loads any string that
                                     "looks like JSON" ([ or { first).
  • `_shrink_oversized_file_blocks`— halve an oversized prompt on a retry.
  • `_MIN_CODER_SUMMARY_CHARS` + `_is_short_summary_coder_output`.
Two copies meant two places to fix every time the coercion logic changed, and
the only real defense against Bedrock's "nested array came back as a JSON
STRING" quirk was a SECOND full LLM round-trip (the array-not-string retry) —
expensive and ad-hoc.

This module is the single answer, and adds the piece that makes the retry RARE
rather than primary: `coerce_to_schema(payload, schema_class)` walks the
target Pydantic model's JSON schema and, field by field, fixes the exact shapes
the providers used to re-prompt for:
  • a field typed array/object that arrived as a JSON STRING → parsed in place;
  • a field typed `array` that arrived as a single object → wrapped in a list;
  • recursion into nested model `$ref`/`items` so `CoderOutput.files[*]` is
    normalized too.
So the common provider quirk is repaired deterministically on the first
response; the LLM validation-retry only fires for genuinely malformed output.

Everything here is pure + dependency-free (stdlib json + pydantic schema dict),
so it's trivially unit-testable without a live provider.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Type

from pydantic import BaseModel

# A CoderOutput with files but a near-empty summary is the known flaky-output
# signature (model emitted a patch but truncated its reasoning). Shared so both
# providers apply the SAME threshold. 30 chars ≈ "Fixes the bug." — anything
# shorter alongside a real patch is suspect.
MIN_CODER_SUMMARY_CHARS = 30


def coerce_stringified_json(value: Any) -> Any:
    """Recursively walk a payload and parse any string that looks like JSON.

    Bedrock's Converse toolUse blocks (and, more rarely, Azure tool-call
    arguments) sometimes return nested arrays/objects as serialized JSON
    strings even when the tool inputSchema types them as arrays/objects. This
    best-effort decodes those so Pydantic validates normally.

    A string is treated as "looks like JSON" iff its first non-whitespace
    character is `[` or `{` — narrow enough to avoid corrupting freeform text
    fields (descriptions, summaries) that merely start with other characters.
    """
    if isinstance(value, str):
        stripped = value.lstrip()
        if stripped[:1] in ("[", "{"):
            try:
                return coerce_stringified_json(json.loads(value))
            except json.JSONDecodeError:
                return value
        return value
    if isinstance(value, list):
        return [coerce_stringified_json(v) for v in value]
    if isinstance(value, dict):
        return {k: coerce_stringified_json(v) for k, v in value.items()}
    return value


# ── Schema-aware coercion (the part that makes the LLM retry rare) ───────────

def _resolve_ref(node: Dict[str, Any], defs: Dict[str, Any]) -> Dict[str, Any]:
    """Follow a local `$ref` (#/$defs/Name or #/definitions/Name) to its target
    schema node. Returns the node unchanged if it isn't a ref or can't resolve."""
    ref = node.get("$ref")
    if not isinstance(ref, str):
        return node
    name = ref.rsplit("/", 1)[-1]
    return defs.get(name, node)


def _expected_kind(field_schema: Dict[str, Any]) -> str:
    """Classify a field's JSON-schema node as 'array', 'object', or 'other'.
    Tolerates pydantic's `anyOf`/`allOf` (Optional[...] unions) by scanning the
    branches for the first array/object type."""
    t = field_schema.get("type")
    if t == "array":
        return "array"
    if t == "object" or "properties" in field_schema:
        return "object"
    # Optional[...] / unions / $ref-with-array — peek inside.
    for key in ("anyOf", "allOf", "oneOf"):
        for branch in field_schema.get(key, []) or []:
            if isinstance(branch, dict):
                bt = branch.get("type")
                if bt == "array":
                    return "array"
                if bt == "object" or "properties" in branch:
                    return "object"
    return "other"


def coerce_to_schema(payload: Any, schema_class: Type[BaseModel]) -> Any:
    """Deterministically repair the provider quirks the validation-retry used to
    fix, BEFORE validation:
      • a field the schema types as array/object that arrived as a JSON STRING
        is parsed into the native value;
      • a field typed `array` that arrived as a single dict is wrapped `[obj]`;
      • recursion into nested model items (e.g. CoderOutput.files[*]).

    Falls back to the plain `coerce_stringified_json` walk for anything not
    described by the schema, and never raises — a best-effort normalizer always
    returns *something* validate-able-or-not, leaving the existing retry as the
    final safety net for genuinely malformed output.
    """
    try:
        schema = schema_class.model_json_schema()
    except Exception:
        return coerce_stringified_json(payload)
    defs = schema.get("$defs") or schema.get("definitions") or {}
    return _coerce_node(payload, schema, defs)


def _coerce_node(value: Any, node: Dict[str, Any], defs: Dict[str, Any]) -> Any:
    """Coerce `value` against a JSON-schema `node` (with `defs` for $ref)."""
    node = _resolve_ref(node, defs)
    kind = _expected_kind(node)

    # A stringified array/object at a slot the schema expects to be structured:
    # parse it. This is the Bedrock "files came back as a JSON string" case.
    if kind in ("array", "object") and isinstance(value, str):
        stripped = value.lstrip()
        if stripped[:1] in ("[", "{"):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return value  # leave it; the retry/validation will flag it

    if kind == "array":
        items_schema = node.get("items") or {}
        if isinstance(value, dict):
            # Schema wants a list but a single object arrived — wrap it.
            value = [value]
        if isinstance(value, list):
            return [_coerce_node(v, items_schema, defs) for v in value]
        return value

    if kind == "object":
        props = node.get("properties") or {}
        if isinstance(value, dict):
            out: Dict[str, Any] = {}
            for k, v in value.items():
                child = props.get(k)
                if isinstance(child, dict):
                    out[k] = _coerce_node(v, child, defs)
                else:
                    out[k] = coerce_stringified_json(v)
            return out
        return value

    # 'other' = a field the schema types as a scalar (string/int/bool/...) OR a
    # field with NO declared type. We must NOT run coerce_stringified_json on a
    # TYPED scalar: a string field whose value happens to be valid JSON (e.g.
    # summary="[1, 2, 3]") would be wrongly parsed into a list and corrupt the
    # payload. Only do the recovery walk for genuinely UNTYPED fields, where a
    # nested stringified blob is the thing we're trying to recover.
    if node.get("type") is not None:
        return value  # explicit scalar type — leave the value exactly as-is
    return coerce_stringified_json(value)


# ── Short-summary retry helpers (shared by both providers) ───────────────────

def is_short_summary_coder_output(result: BaseModel) -> bool:
    """True when *result* is a CoderOutput carrying a patch but an implausibly
    short summary (a flaky-truncation signature)."""
    if type(result).__name__ != "CoderOutput":
        return False
    files = getattr(result, "files", None) or []
    summary = getattr(result, "summary", "") or ""
    return len(files) > 0 and len(summary.strip()) < MIN_CODER_SUMMARY_CHARS


def shrink_oversized_file_blocks(user_prompt: str, threshold: int = 8_000) -> str:
    """Halve an oversized prompt to free output budget on a short-summary retry.

    We don't parse the prompt structure (it's built by coder_agent); we just cap
    total length: if the prompt exceeds 2*threshold, keep the head (task + early
    files) and the tail (usually the edit target), dropping the middle with a
    marker. Shared verbatim by both providers."""
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
