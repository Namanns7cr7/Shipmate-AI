"""Unit tests for the Tier-3 BedrockProvider retry triggers.

Two flaky-output recovery paths, both exercised here WITHOUT touching boto3
or the network — we build the provider via __new__ and patch _call_converse:

  1. short-summary retry: a CoderOutput with files but a <30-char summary is a
     truncation signature; retry once with shrunk context, keep the longer
     summary.
  2. invoke_with_lint_feedback: re-prompt with the specific lint issues so the
     model corrects them instead of re-emitting the same mistake.
"""
from unittest.mock import patch

import pytest

from app.agents.coder_agent import CoderOutput
from app.services.bedrock_provider import (
    BedrockProvider,
    _MIN_CODER_SUMMARY_CHARS,
    _shrink_oversized_file_blocks,
)


def _provider() -> BedrockProvider:
    """A provider with model ids set but no boto3 client (we patch converse)."""
    p = BedrockProvider.__new__(BedrockProvider)
    p.smart_model = "smart-test"
    p.fast_model = "fast-test"
    return p


def _coder_payload(summary: str):
    return {
        "files": [{"path": "a.py", "new_content": "x = 1", "rationale": "r"}],
        "summary": summary,
        "skipped": [],
    }


class TestShrinkOversizedFileBlocks:
    def test_short_prompt_unchanged(self):
        s = "x" * 100
        assert _shrink_oversized_file_blocks(s) == s

    def test_big_prompt_shrunk_keeping_head_and_tail(self):
        big = "HEAD" + ("y" * 20_000) + "TAIL"
        out = _shrink_oversized_file_blocks(big, threshold=8_000)
        assert len(out) < len(big)
        assert out.startswith("HEAD")
        assert out.endswith("TAIL")
        assert "dropped" in out


class TestShortSummaryDetection:
    def test_short_summary_with_files_is_flaky(self):
        co = CoderOutput(
            files=[{"path": "a.py", "new_content": "x", "rationale": "r"}],
            summary="fix",
        )
        assert BedrockProvider._is_short_summary_coder_output(co) is True

    def test_long_summary_is_not_flaky(self):
        co = CoderOutput(
            files=[{"path": "a.py", "new_content": "x", "rationale": "r"}],
            summary="A sufficiently detailed summary of the patch and its rationale.",
        )
        assert BedrockProvider._is_short_summary_coder_output(co) is False

    def test_no_files_is_not_flaky(self):
        co = CoderOutput(files=[], summary="hi")
        assert BedrockProvider._is_short_summary_coder_output(co) is False

    def test_threshold_is_documented_value(self):
        assert _MIN_CODER_SUMMARY_CHARS == 30


class TestShortSummaryRetry:
    def test_retry_fires_and_keeps_longer_summary(self):
        p = _provider()
        calls = []

        def fake(model_id, tool_name, schema, system_prompt, user_prompt, max_tokens):
            calls.append(user_prompt)
            if len(calls) == 1:
                return _coder_payload("fix")  # short -> triggers retry
            return _coder_payload("A properly detailed corrective summary.")

        with patch.object(p, "_call_converse", side_effect=fake):
            out = p.invoke_structured_sync("sys", "u" * 20_000, CoderOutput, "smart")

        assert len(calls) == 2, "retry should fire exactly once"
        assert len(out.summary) >= _MIN_CODER_SUMMARY_CHARS
        assert "dropped" in calls[1], "retry should use shrunk context"

    def test_no_retry_when_summary_is_fine(self):
        p = _provider()
        calls = []

        def fake(model_id, tool_name, schema, system_prompt, user_prompt, max_tokens):
            calls.append(user_prompt)
            return _coder_payload("A nice long summary that is clearly fine and complete.")

        with patch.object(p, "_call_converse", side_effect=fake):
            p.invoke_structured_sync("sys", "u", CoderOutput, "smart")

        assert len(calls) == 1, "no retry expected for a good summary"

    def test_retry_failure_keeps_first_result(self):
        p = _provider()
        calls = []

        def fake(model_id, tool_name, schema, system_prompt, user_prompt, max_tokens):
            calls.append(user_prompt)
            if len(calls) == 1:
                return _coder_payload("fix")
            raise RuntimeError("bedrock blew up on retry")

        with patch.object(p, "_call_converse", side_effect=fake):
            out = p.invoke_structured_sync("sys", "u" * 20_000, CoderOutput, "smart")

        assert len(calls) == 2
        assert out.summary == "fix", "first result kept when retry raises"


class TestInvokeWithLintFeedback:
    def test_issues_are_appended_to_prompt(self):
        p = _provider()
        calls = []

        def fake(model_id, tool_name, schema, system_prompt, user_prompt, max_tokens):
            calls.append(user_prompt)
            return _coder_payload("Corrected the hallucinated import as instructed.")

        with patch.object(p, "_call_converse", side_effect=fake):
            p.invoke_with_lint_feedback(
                "sys", "original prompt", CoderOutput,
                ["hallucinated import app.fake"], "smart",
            )

        assert "LINT REJECTION" in calls[0]
        assert "app.fake" in calls[0]
