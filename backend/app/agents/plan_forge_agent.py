from typing import Any, Dict, List

from .base_agent import BaseAgent
from ..schemas.agent_schemas import (
    PlanForgeOutput, Milestone, Blocker, RepoLensOutput
)
from ..services.llm_service import LLMService


class PlanForgeAgent(BaseAgent):
    name = "plan_forge"
    description = "Creates delivery milestones, identifies blockers, and recommends next actions"

    def run(self, context: Dict[str, Any]) -> PlanForgeOutput:
        repo_lens: RepoLensOutput = context.get("repo_lens")
        feature_ctx = self._feature_context(context)
        info = self._repo_info(context)
        tree = self._file_tree(context)

        milestones = self._build_milestones(repo_lens, feature_ctx, tree)
        blockers = self._build_blockers(repo_lens)
        deps = self._infer_dependencies(repo_lens)
        next_action = self._next_best_action(blockers, repo_lens)
        effort = self._estimate_effort(milestones)
        score = self._score(blockers, milestones)

        base = PlanForgeOutput(
            milestones=milestones,
            blockers=blockers,
            dependencies=deps,
            next_best_action=next_action,
            estimated_effort=effort,
            delivery_score=score,
        )
        # Step 1: rewrite prose on heuristic items.
        enhanced = LLMService.enhance(self.name, context, base)
        # Step 2: append LLM-discovered milestones/blockers grounded in real code.
        return LLMService.discover_plan_forge(context, enhanced)

    def _build_milestones(
        self, rl: RepoLensOutput, feature_ctx: str, tree: List[str],
    ) -> List[Milestone]:
        ms: List[Milestone] = []
        has_readme = any(
            f.lower().split("/")[-1] in {"readme.md", "readme", "readme.rst", "readme.txt"}
            for f in tree
        )

        if feature_ctx:
            ms.append(Milestone(
                title="Implement Feature: " + feature_ctx[:60].strip(),
                description="Scope, design, and implement the requested feature across affected layers.",
                estimated_days=5,
                priority="high",
                category="feature",
            ))

        if not rl.has_tests:
            ms.append(Milestone(
                title="Establish Test Suite",
                description="Set up testing framework and write unit + integration tests for core modules.",
                estimated_days=3,
                priority="critical",
                category="testing",
            ))
        else:
            # Only suggest "Expand Test Coverage" when the test ratio is
            # actually thin. Heuristic: count test files vs source files in the
            # tree. Fire only when tests < 20% of source. Above that, leave
            # coverage discoveries to the LLM (which can cite specific gaps).
            test_files = sum(1 for f in tree if any(
                t in f.lower() for t in ("test_", "_test.", ".test.", ".spec.", "/tests/", "/test/", "/spec/")
            ))
            src_files = sum(1 for f in tree if f.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs")))
            thin_coverage = src_files > 10 and test_files * 5 < src_files
            if thin_coverage:
                ms.append(Milestone(
                    title="Expand Test Coverage",
                    description="Add tests for uncovered paths, edge cases, and any new feature code.",
                    estimated_days=2,
                    priority="high",
                    category="testing",
                ))

        if not rl.has_ci_cd:
            ms.append(Milestone(
                title="Set Up CI/CD Pipeline",
                description="Configure GitHub Actions (or equivalent) for automated build, test, and deploy.",
                estimated_days=2,
                priority="critical",
                category="ci_cd",
            ))

        # Security risks → milestone
        sec_risks = [r for r in rl.architecture_risks if r.category == "security"]
        if sec_risks:
            ms.append(Milestone(
                title="Remediate Security Findings",
                description="Address critical security risks: " + "; ".join(r.risk for r in sec_risks[:3]),
                estimated_days=2,
                priority="critical",
                category="security",
            ))

        if not rl.has_dockerfile:
            ms.append(Milestone(
                title="Containerize Application",
                description="Write Dockerfile and docker-compose for reproducible local and production deployment.",
                estimated_days=1,
                priority="medium",
                category="infra",
            ))

        if not has_readme:
            ms.append(Milestone(
                title="Write Project Documentation",
                description="Create README, API docs, and deployment guide for the team.",
                estimated_days=1,
                priority="low",
                category="docs",
            ))

        # Production-readiness milestone: ONLY if real shipping risks exist
        # (no CI, no tests, no Docker, or critical security findings). For a
        # repo that already has CI + tests + Docker, this is just noise.
        if (not rl.has_ci_cd) or (not rl.has_tests) or (not rl.has_dockerfile) or sec_risks:
            ms.append(Milestone(
                title="Production Readiness Review",
                description="Final review: load testing, monitoring setup, rollback plan, and stakeholder sign-off.",
                estimated_days=2,
                priority="high",
                category="infra",
            ))

        return ms

    def _build_blockers(self, rl: RepoLensOutput) -> List[Blocker]:
        blockers = []
        bid = 1

        for risk in rl.architecture_risks:
            if risk.impact in ("critical", "high"):
                severity = "critical" if risk.impact == "critical" else "high"
                blockers.append(Blocker(
                    id=f"BLK-{bid:03d}",
                    title=risk.risk,
                    description=f"Architecture risk detected in category '{risk.category}'.",
                    severity=severity,
                    resolution=self._risk_resolution(risk.category, risk.risk),
                    category=risk.category,
                ))
                bid += 1

        if not rl.has_ci_cd:
            blockers.append(Blocker(
                id=f"BLK-{bid:03d}",
                title="No automated CI/CD pipeline",
                description="Without CI/CD, every deployment is manual and error-prone.",
                severity="high",
                resolution="Set up GitHub Actions with build, test, and deploy jobs.",
                category="ci_cd",
            ))
            bid += 1

        if not rl.has_tests:
            blockers.append(Blocker(
                id=f"BLK-{bid:03d}",
                title="No test coverage",
                description="Zero tests means regressions will reach production undetected.",
                severity="critical",
                resolution="Add pytest/jest test suite. Target ≥60% coverage before shipping.",
                category="testing",
            ))

        return blockers

    def _risk_resolution(self, category: str, risk: str) -> str:
        resolutions = {
            "security": "Remove sensitive data immediately, rotate credentials, add to .gitignore.",
            "ci_cd": "Add .github/workflows/ci.yml with test and lint jobs.",
            "config": "Add configuration file and document environment setup.",
            "structure": "Refactor project structure to follow language/framework conventions.",
            "docs": "Write README with setup, usage, and contribution guide.",
            "deps": "Audit and update dependencies. Remove unused packages.",
        }
        return resolutions.get(category, "Review and resolve the identified risk before shipping.")

    def _infer_dependencies(self, rl: RepoLensOutput) -> List[str]:
        deps = []
        stack = set(rl.tech_stack)
        if "React" in stack or "Vue.js" in stack:
            deps.append("Frontend build pipeline (Vite/Webpack)")
        if "FastAPI" in stack or "Django" in stack:
            deps.append("Python runtime environment (3.10+)")
        if "Node.js" in stack:
            deps.append("Node.js runtime (18+)")
        if "Docker" in stack:
            deps.append("Container registry (Docker Hub / GHCR / ECR)")
        if not rl.has_ci_cd:
            deps.append("CI/CD platform (GitHub Actions recommended)")
        deps.append("GitHub repository access and branch protection rules")
        return deps

    def _next_best_action(self, blockers: List[Blocker], rl: RepoLensOutput) -> str:
        critical = [b for b in blockers if b.severity == "critical"]
        if critical:
            return f"Resolve critical blocker immediately: {critical[0].title}"
        if not rl.has_tests:
            return "Set up a test suite — zero coverage is the top shipping risk."
        if not rl.has_ci_cd:
            return "Configure CI/CD pipeline to automate testing and deployment."
        return "Run a full security scan and ensure all high findings are resolved."

    def _estimate_effort(self, milestones: List[Milestone]) -> str:
        total = sum(m.estimated_days for m in milestones)
        if total <= 5:
            return f"{total} days (1 sprint)"
        if total <= 10:
            return f"{total} days (~2 sprints)"
        return f"{total} days (~{total // 5} sprints)"

    def _score(self, blockers: List[Blocker], milestones: List[Milestone]) -> int:
        s = 100
        for b in blockers:
            if b.severity == "critical": s -= 20
            elif b.severity == "high":   s -= 12
            else:                         s -= 6
        s -= min(15, len(milestones) * 2)
        return max(20, min(100, s))
