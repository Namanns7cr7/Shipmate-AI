"""Shared provider-coercion module (C5).

Both BedrockProvider and AzureOpenAIProvider previously carried byte-identical
copies of `_coerce_stringified_json` / `_shrink_oversized_file_blocks` and the
short-summary predicate. They now delegate to app.services.provider_coercion,
and the new `coerce_to_schema` repairs the common "nested array came back as a
JSON string" provider quirk DETERMINISTICALLY (up front) instead of paying for
a second full LLM round-trip. These tests pin that behaviour.
"""
from typing import List, Optional

import pytest
from pydantic import BaseModel, Field

from app.services import provider_coercion as pc


# A schema shaped like CoderOutput (the field that actually broke in prod).
class _Item(BaseModel):
    path: str
    new_content: str
    rationale: str = ""


class _Out(BaseModel):
    files: List[_Item] = Field(default_factory=list)
    skipped: List[str] = Field(default_factory=list)
    summary: str = ""


class TestStringifiedJsonWalk:
    def test_parses_top_level_stringified_array(self):
        assert pc.coerce_stringified_json('[1, 2, 3]') == [1, 2, 3]

    def test_parses_nested_stringified_object(self):
        out = pc.coerce_stringified_json({"a": '{"b": 1}'})
        assert out == {"a": {"b": 1}}

    def test_leaves_plain_prose_untouched(self):
        # A description starting with a normal char must NOT be parsed.
        assert pc.coerce_stringified_json("Fixes the bug in main.py") == \
            "Fixes the bug in main.py"

    def test_leaves_malformed_jsonish_string_untouched(self):
        # Looks like JSON (starts with '[') but isn't — return verbatim.
        assert pc.coerce_stringified_json("[not json") == "[not json"


class TestCoerceToSchema:
    def test_stringified_files_array_is_parsed(self):
        # The exact Bedrock quirk: `files` typed array, arrives as a JSON STRING.
        payload = {
            "files": '[{"path": "a.py", "new_content": "x", "rationale": "r"}]',
            "skipped": [],
            "summary": "did a thing",
        }
        coerced = pc.coerce_to_schema(payload, _Out)
        # Must now validate without any retry.
        out = _Out.model_validate(coerced)
        assert len(out.files) == 1
        assert out.files[0].path == "a.py"

    def test_single_object_at_array_slot_is_wrapped(self):
        # Schema wants a list; a single object arrived — wrap into [obj].
        payload = {
            "files": {"path": "a.py", "new_content": "x", "rationale": "r"},
            "summary": "s",
        }
        out = _Out.model_validate(pc.coerce_to_schema(payload, _Out))
        assert len(out.files) == 1
        assert out.files[0].new_content == "x"

    def test_nested_stringified_item_field_is_parsed(self):
        # files is a native list but one element arrived stringified.
        payload = {
            "files": ['{"path": "a.py", "new_content": "x", "rationale": "r"}'],
            "summary": "s",
        }
        out = _Out.model_validate(pc.coerce_to_schema(payload, _Out))
        assert out.files[0].path == "a.py"

    def test_freeform_summary_starting_with_bracket_is_preserved(self):
        # A summary field (scalar) that happens to start with '[' must survive —
        # we only force-parse fields the schema types as array/object.
        payload = {"files": [], "summary": "[done] applied the patch"}
        out = _Out.model_validate(pc.coerce_to_schema(payload, _Out))
        assert out.summary == "[done] applied the patch"

    def test_typed_string_field_that_is_valid_json_is_not_corrupted(self):
        # Regression (adversarial review): a STRING-typed field whose value is
        # itself valid JSON ("[1, 2, 3]") must NOT be parsed into a list — that
        # would corrupt a legitimate scalar and fail validation. Only array/
        # object-typed (or untyped) slots get parsed.
        payload = {"files": [], "summary": "[1, 2, 3]"}
        coerced = pc.coerce_to_schema(payload, _Out)
        assert coerced["summary"] == "[1, 2, 3]"      # preserved as the string
        out = _Out.model_validate(coerced)            # and still validates
        assert out.summary == "[1, 2, 3]"

    def test_typed_string_field_that_is_json_object_is_not_corrupted(self):
        payload = {"files": [], "summary": '{"k": "v"}'}
        out = _Out.model_validate(pc.coerce_to_schema(payload, _Out))
        assert out.summary == '{"k": "v"}'

    def test_already_native_payload_is_unchanged(self):
        payload = {
            "files": [{"path": "a.py", "new_content": "x", "rationale": "r"}],
            "skipped": ["b.py"],
            "summary": "s",
        }
        out = _Out.model_validate(pc.coerce_to_schema(payload, _Out))
        assert out.skipped == ["b.py"]
        assert len(out.files) == 1


class TestShortSummary:
    def test_short_summary_flagged_only_for_coder_output(self):
        # Predicate keys on the class NAME 'CoderOutput' — _Out must not trip it.
        class CoderOutput(BaseModel):
            files: list = []
            summary: str = ""
        co = CoderOutput(files=[{"x": 1}], summary="tiny")
        assert pc.is_short_summary_coder_output(co) is True
        co_ok = CoderOutput(files=[{"x": 1}], summary="x" * 40)
        assert pc.is_short_summary_coder_output(co_ok) is False
        # Non-CoderOutput never flagged even with a short summary.
        assert pc.is_short_summary_coder_output(_Out(summary="hi")) is False

    def test_shrink_noop_under_threshold(self):
        s = "x" * 100
        assert pc.shrink_oversized_file_blocks(s) == s

    def test_shrink_trims_oversized(self):
        big = "H" * 9000 + "M" * 5000 + "T" * 9000
        out = pc.shrink_oversized_file_blocks(big, threshold=8000)
        assert len(out) < len(big)
        assert out.startswith("H")
        assert out.endswith("T")
        assert "dropped" in out
