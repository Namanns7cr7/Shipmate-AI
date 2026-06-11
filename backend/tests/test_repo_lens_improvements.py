"""Phase 1, Task 3 — RepoLens entry point, architecture, and score fixes.

RED: tests fail until the three improvements land in repo_lens_agent.py.
GREEN:
  - /components/ and /hooks/ excluded from entry points
  - repos with frontend/ + backend/ top-level dirs get "fullstack" pattern
  - score formula is severity-weighted (one critical counts more than five lows)
"""
import pytest
from app.agents.repo_lens_agent import RepoLensAgent


class TestEntryPointExclusions:
    def _run(self, tree):
        agent = RepoLensAgent()
        return agent._entry_points(tree)

    def test_index_ts_in_components_excluded(self):
        tree = ["frontend/src/components/index.ts", "backend/app/main.py"]
        result = self._run(tree)
        assert "frontend/src/components/index.ts" not in result

    def test_index_ts_in_hooks_excluded(self):
        tree = ["frontend/src/hooks/index.ts", "backend/app/main.py"]
        result = self._run(tree)
        assert "frontend/src/hooks/index.ts" not in result

    def test_real_main_py_included(self):
        tree = ["backend/app/main.py"]
        result = self._run(tree)
        assert "backend/app/main.py" in result

    def test_real_index_ts_at_src_included(self):
        tree = ["frontend/src/index.ts"]
        result = self._run(tree)
        assert "frontend/src/index.ts" in result


class TestArchitectureFullstack:
    def _run(self, tree):
        agent = RepoLensAgent()
        return agent._architecture(tree)

    def test_frontend_and_backend_dirs_give_fullstack(self):
        tree = [
            "frontend/src/App.tsx",
            "frontend/src/main.tsx",
            "backend/app/main.py",
            "backend/requirements.txt",
        ]
        assert self._run(tree) == "fullstack"

    def test_only_frontend_is_not_fullstack(self):
        tree = ["frontend/src/App.tsx", "frontend/src/main.tsx"]
        result = self._run(tree)
        assert result != "fullstack"

    def test_only_backend_is_not_fullstack(self):
        tree = ["backend/app/main.py", "backend/requirements.txt"]
        result = self._run(tree)
        assert result != "fullstack"

    def test_monorepo_pattern_still_detected(self):
        tree = [
            "packages/core/index.ts",
            "packages/ui/index.ts",
            "apps/web/index.ts",
        ]
        assert self._run(tree) == "monorepo"


class TestSeverityWeightedScore:
    """One critical risk must deduct more than five low risks."""

    def _run_risks(self, has_ci=True, has_docker=True, has_tests=True,
                   risks=None, tree=None):
        from app.schemas.agent_schemas import ArchitectureRisk
        agent = RepoLensAgent()
        return agent._score(
            has_ci, has_docker, has_tests,
            risks or [],
            tree or ["README.md", ".gitignore"],
        )

    def test_single_critical_risk_deducts_more_than_five_lows(self):
        from app.schemas.agent_schemas import ArchitectureRisk
        one_critical = [ArchitectureRisk(risk="x", impact="critical", category="security")]
        five_lows = [ArchitectureRisk(risk=f"l{i}", impact="low", category="docs") for i in range(5)]

        score_critical = self._run_risks(risks=one_critical)
        score_five_lows = self._run_risks(risks=five_lows)

        assert score_critical < score_five_lows, (
            f"One critical ({score_critical}) should score lower than five lows ({score_five_lows})"
        )

    def test_all_green_scores_100(self):
        score = self._run_risks()
        assert score == 100

    def test_high_risk_deducts_less_than_critical(self):
        from app.schemas.agent_schemas import ArchitectureRisk
        critical = [ArchitectureRisk(risk="c", impact="critical", category="security")]
        high = [ArchitectureRisk(risk="h", impact="high", category="ci_cd")]

        score_c = self._run_risks(risks=critical)
        score_h = self._run_risks(risks=high)

        assert score_c < score_h, (
            f"Critical ({score_c}) should score lower than single high ({score_h})"
        )
