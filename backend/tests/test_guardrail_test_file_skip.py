"""Phase 1, Task 2 — GuardRail skips secret/injection scans in test files
but still scans dependency files (requirements.txt, package.json).

RED: tests fail until _is_test_file() exists and the skip is wired up.
GREEN: add helper + skip guards to guardrail_agent.py.
"""
import pytest
from app.agents.guardrail_agent import _is_test_file


class TestIsTestFile:
    @pytest.mark.parametrize("path", [
        "tests/test_auth.py",
        "test_something.py",
        "something_test.py",
        "frontend/src/components/Login.test.ts",
        "frontend/src/components/Login.spec.ts",
        "backend/tests/test_guardrail.py",
        "src/__tests__/App.test.tsx",
        "spec/auth_spec.rb",
    ])
    def test_test_file_paths_are_identified(self, path):
        assert _is_test_file(path) is True

    @pytest.mark.parametrize("path", [
        "requirements.txt",
        "package.json",
        "package-lock.json",
        "backend/app/main.py",
        "frontend/src/App.tsx",
        "backend/app/agents/guardrail_agent.py",
        ".env",
        "docker-compose.yml",
    ])
    def test_non_test_files_are_not_identified(self, path):
        assert _is_test_file(path) is False


class TestGuardrailSkipsTestFiles:
    """Integration: secret patterns in a test file must NOT produce findings."""

    def _make_context(self, filename: str, content: str) -> dict:
        return {
            "file_tree": [filename],
            "key_files": {filename: content},
        }

    def test_hardcoded_secret_in_test_file_is_not_flagged(self):
        from app.agents.guardrail_agent import GuardRailAgent
        # A test file that contains a mock/fixture credential
        ctx = self._make_context(
            "tests/test_auth.py",
            'password = "supersecretfixture123"\n'
            'api_key = "test_key_abc123456789"\n',
        )
        agent = GuardRailAgent()
        result = agent.run(ctx)
        secret_findings = [f for f in result.findings if f.category == "secrets"]
        assert len(secret_findings) == 0, (
            f"Expected no secret findings for test file, got: {[f.title for f in secret_findings]}"
        )

    def test_dynamic_exec_in_test_file_is_not_flagged(self):
        from app.agents.guardrail_agent import GuardRailAgent
        ctx = self._make_context(
            "tests/test_sandbox.py",
            "def test_eval_is_blocked():\n    result = eval('1+1')\n    assert result == 2\n",
        )
        agent = GuardRailAgent()
        result = agent.run(ctx)
        injection_findings = [f for f in result.findings if f.category == "injection"]
        assert len(injection_findings) == 0, (
            f"Expected no injection findings for test file, got: {[f.title for f in injection_findings]}"
        )

    def test_secret_in_requirements_txt_is_still_flagged(self):
        """Dependency files are NOT test files — still scan them."""
        from app.agents.guardrail_agent import GuardRailAgent
        # requirements.txt with a pinned package that matches a risky pattern
        ctx = self._make_context(
            "requirements.txt",
            'password = "hardcoded_secret_value"\n',
        )
        agent = GuardRailAgent()
        result = agent.run(ctx)
        secret_findings = [f for f in result.findings if f.category == "secrets"]
        assert len(secret_findings) >= 1, (
            "requirements.txt should still be scanned for secrets"
        )
