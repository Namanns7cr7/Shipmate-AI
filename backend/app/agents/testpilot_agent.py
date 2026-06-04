from pathlib import Path
from typing import Any, Dict, List

from .base_agent import BaseAgent
from ..schemas.agent_schemas import (
    TestPilotOutput, ExistingTests, SuggestedTest, RepoLensOutput
)

_TEST_FRAMEWORKS_PY = {"pytest", "unittest", "nose", "hypothesis", "behave"}
_TEST_FRAMEWORKS_JS = {"jest", "vitest", "mocha", "jasmine", "cypress", "playwright", "@testing-library"}

_TEST_FILE_PATTERNS = [
    lambda f: f.lower().startswith("test_"),
    lambda f: f.lower().endswith("_test.py"),
    lambda f: ".test." in f.lower(),
    lambda f: ".spec." in f.lower(),
]


def _is_test_file(path: str) -> bool:
    name = Path(path).name.lower()
    folder = path.lower()
    if any(p(name) for p in _TEST_FILE_PATTERNS):
        return True
    if "/tests/" in folder or "/test/" in folder or "/spec/" in folder or "/__tests__/" in folder:
        return True
    return False


class TestPilotAgent(BaseAgent):
    name = "testpilot"
    description = "Audits test coverage, identifies gaps, and recommends a QA strategy"

    def run(self, context: Dict[str, Any]) -> TestPilotOutput:
        tree = self._file_tree(context)
        kf = self._key_files(context)
        repo_lens: RepoLensOutput = context.get("repo_lens")
        feature_ctx = self._feature_context(context)

        test_files = [f for f in tree if _is_test_file(f)]
        frameworks = self._detect_frameworks(kf, tree)

        # Estimate coverage ratio
        src_files = self._source_files(tree)
        if src_files:
            raw_ratio = len(test_files) / len(src_files)
            coverage_est = min(90, int(raw_ratio * 100 * 1.5))  # heuristic
        else:
            coverage_est = 0 if not test_files else 20

        missing = self._missing_areas(tree, repo_lens, test_files)
        suggestions = self._suggest_tests(repo_lens, test_files, feature_ctx, missing)
        qa_readiness = "ready" if coverage_est >= 60 else ("partial" if test_files else "not_ready")
        score = self._score(test_files, coverage_est, missing)

        return TestPilotOutput(
            existing_tests=ExistingTests(
                count=len(test_files),
                coverage_estimate=coverage_est,
                frameworks=frameworks,
                test_files=test_files[:20],
            ),
            missing_coverage_areas=missing,
            suggested_tests=suggestions,
            qa_readiness=qa_readiness,
            test_score=score,
        )

    def _detect_frameworks(self, kf: Dict[str, str], tree: List[str]) -> List[str]:
        found = []
        if "package.json" in kf:
            content = kf["package.json"].lower()
            for fw in _TEST_FRAMEWORKS_JS:
                if fw in content:
                    found.append(fw.capitalize().replace("@testing-library", "Testing Library"))
        req = kf.get("requirements.txt", "") + kf.get("pyproject.toml", "")
        for fw in _TEST_FRAMEWORKS_PY:
            if fw in req.lower():
                found.append(fw.capitalize())
        # Also check if pytest.ini / jest.config.* exist
        for f in tree:
            name = Path(f).name.lower()
            if name in {"pytest.ini", "setup.cfg", "conftest.py"}:
                if "Pytest" not in found:
                    found.append("Pytest")
            if name.startswith("jest.config") or name.startswith("vitest.config"):
                label = "Vitest" if "vitest" in name else "Jest"
                if label not in found:
                    found.append(label)
        return list(dict.fromkeys(found))[:6]

    def _source_files(self, tree: List[str]) -> List[str]:
        SRC_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}
        SKIP = {"node_modules", ".git", "dist", "build", "venv", ".venv"}
        return [
            f for f in tree
            if Path(f).suffix in SRC_EXTS
            and not any(s in f for s in SKIP)
            and not _is_test_file(f)
        ]

    def _missing_areas(self, tree, repo_lens, test_files) -> List[str]:
        missing = []
        if not test_files:
            missing.append("All source modules — no tests exist")
            return missing

        if repo_lens:
            for entry in repo_lens.entry_points:
                base = Path(entry).stem
                has_test = any(base in tf for tf in test_files)
                if not has_test:
                    missing.append(f"Entry point `{entry}` has no corresponding test")

        if not any("integration" in f.lower() or "e2e" in f.lower() for f in test_files):
            missing.append("Integration / end-to-end tests")
        if not any("auth" in f.lower() or "login" in f.lower() for f in test_files):
            missing.append("Authentication and authorization flows")
        if not any("error" in f.lower() or "exception" in f.lower() for f in test_files):
            missing.append("Error handling and edge case paths")
        if not any("security" in f.lower() or "guard" in f.lower() for f in test_files):
            missing.append("Security-sensitive code paths")

        return missing[:8]

    def _suggest_tests(self, repo_lens, test_files, feature_ctx, missing) -> List[SuggestedTest]:
        suggestions: List[SuggestedTest] = []

        if not test_files:
            suggestions.append(SuggestedTest(
                name="test_smoke_all_routes",
                type="integration",
                priority="critical",
                description="Smoke test every API endpoint / page to confirm basic functionality.",
            ))

        if feature_ctx:
            name_slug = feature_ctx[:30].strip().lower().replace(" ", "_").replace("/", "_")
            suggestions.append(SuggestedTest(
                name=f"test_{name_slug[:40]}",
                type="unit",
                priority="high",
                description=f"Unit tests covering the core logic of: {feature_ctx[:80]}",
            ))
            suggestions.append(SuggestedTest(
                name=f"test_{name_slug[:40]}_integration",
                type="integration",
                priority="high",
                description=f"Integration test verifying end-to-end flow for: {feature_ctx[:80]}",
            ))

        if repo_lens:
            for entry in repo_lens.entry_points[:3]:
                base = Path(entry).stem
                suggestions.append(SuggestedTest(
                    name=f"test_{base}",
                    type="unit",
                    priority="high",
                    description=f"Unit tests for the entry module `{entry}`.",
                    target_file=entry,
                ))

        suggestions.append(SuggestedTest(
            name="test_auth_flows",
            type="security",
            priority="critical",
            description="Verify authentication: valid tokens pass, expired/invalid tokens are rejected, "
                        "privilege escalation is prevented.",
        ))
        suggestions.append(SuggestedTest(
            name="test_error_handling",
            type="unit",
            priority="medium",
            description="Test that error conditions return appropriate status codes and messages, "
                        "without leaking internal stack traces.",
        ))
        suggestions.append(SuggestedTest(
            name="test_e2e_happy_path",
            type="e2e",
            priority="high",
            description="End-to-end test of the primary user journey from login to core feature usage.",
        ))

        return suggestions[:10]

    def _score(self, test_files, coverage_est, missing) -> int:
        if not test_files:
            return 10
        s = 40  # base for having some tests
        s += min(40, coverage_est // 2)
        s -= min(20, len(missing) * 4)
        return max(10, min(100, s))
