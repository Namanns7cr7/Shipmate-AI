"""Tests for CoderAgent diff mode — the model emits unified diffs, the agent
applies them and returns a normal full-content CoderOutput, falling back to
full mode on any apply failure. Provider is mocked so these run offline.
"""
from app.agents.coder_agent import (
    CoderAgent, CoderBrief, CoderOutput, CoderFile,
    CoderOutputDiff, CoderFileDiff,
)


_ORIGINAL = "def beta():\n    return 2\n"


def _brief() -> CoderBrief:
    return CoderBrief(
        task="bump beta",
        repo_full_name="o/r",
        target_files={"x.py": _ORIGINAL},
        finding_kind="blocker",
        finding_id="B-1",
    )


class _StubProvider:
    """Returns a queued sequence of structured outputs, one per invoke call."""
    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.calls = []

    def invoke_structured_sync(self, *, system_prompt, user_prompt, schema_class, deployment_hint="smart"):
        self.calls.append(schema_class.__name__)
        return self._outputs.pop(0)


class TestDiffModeApply:
    def test_clean_diff_becomes_full_content(self):
        diff = (
            "@@ -1,2 +1,2 @@\n"
            " def beta():\n"
            "-    return 2\n"
            "+    return 22\n"
        )
        stub = _StubProvider([
            CoderOutputDiff(
                files=[CoderFileDiff(path="x.py", unified_diff=diff, rationale="bump")],
                summary="bump beta to 22",
            )
        ])
        agent = CoderAgent(provider=stub)
        out = agent.run(_brief(), mode="diff")
        assert isinstance(out, CoderOutput)
        assert len(out.files) == 1
        assert out.files[0].path == "x.py"
        assert "return 22" in out.files[0].new_content
        # Only the diff schema was requested — no fallback.
        assert stub.calls == ["CoderOutputDiff"]

    def test_failed_diff_falls_back_to_full(self):
        bad_diff = (
            "@@ -1,2 +1,2 @@\n"
            " def NONEXISTENT():\n"      # context won't match -> apply fails
            "-    return 2\n"
            "+    return 22\n"
        )
        full = CoderOutput(
            files=[CoderFile(path="x.py", new_content="def beta():\n    return 22\n", rationale="bump")],
            summary="bump beta (full)",
        )
        stub = _StubProvider([
            CoderOutputDiff(
                files=[CoderFileDiff(path="x.py", unified_diff=bad_diff, rationale="bump")],
                summary="bump beta diff",
            ),
            full,  # second call (the full-mode fallback)
        ])
        agent = CoderAgent(provider=stub)
        out = agent.run(_brief(), mode="diff")
        assert isinstance(out, CoderOutput)
        assert "return 22" in out.files[0].new_content
        # Both schemas were requested: diff first, then full fallback.
        assert stub.calls == ["CoderOutputDiff", "CoderOutput"]

    def test_empty_diff_output_falls_back(self):
        full = CoderOutput(
            files=[CoderFile(path="x.py", new_content="def beta():\n    return 99\n", rationale="x")],
            summary="full",
        )
        stub = _StubProvider([
            CoderOutputDiff(files=[], summary="nothing to diff"),
            full,
        ])
        agent = CoderAgent(provider=stub)
        out = agent.run(_brief(), mode="diff")
        assert stub.calls == ["CoderOutputDiff", "CoderOutput"]
        assert "return 99" in out.files[0].new_content

    def test_new_file_in_diff_falls_back(self):
        """A diff targeting a file with no existing content can't apply →
        the whole patch falls back to full mode."""
        diff = "@@ -0,0 +1,1 @@\n+new line\n"
        brief = CoderBrief(
            task="add new file",
            repo_full_name="o/r",
            target_files={"new.py": ""},   # empty original
            finding_kind="milestone",
            finding_id="M-1",
        )
        full = CoderOutput(
            files=[CoderFile(path="new.py", new_content="new line\n", rationale="create")],
            summary="full create",
        )
        stub = _StubProvider([
            CoderOutputDiff(
                files=[CoderFileDiff(path="new.py", unified_diff=diff, rationale="create")],
                summary="diff create",
            ),
            full,
        ])
        agent = CoderAgent(provider=stub)
        out = agent.run(brief, mode="diff")
        assert stub.calls == ["CoderOutputDiff", "CoderOutput"]
        assert out.files[0].path == "new.py"

    def test_full_mode_unchanged(self):
        """mode='full' (default) never touches the diff path."""
        full = CoderOutput(
            files=[CoderFile(path="x.py", new_content="def beta():\n    return 2\n", rationale="x")],
            summary="full",
        )
        stub = _StubProvider([full])
        agent = CoderAgent(provider=stub)
        out = agent.run(_brief())  # default mode
        assert stub.calls == ["CoderOutput"]
        assert isinstance(out, CoderOutput)
