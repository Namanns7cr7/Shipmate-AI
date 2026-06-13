"""PRRiskAgent — scores the risk of a *specific pull request*.

The four repo-level agents (RepoLens / PlanForge / GuardRail / TestPilot) judge
the whole repository. PRRiskAgent is different: it reasons over the ACTUAL DIFF of
one open PR — which files changed, how much, which sensitive surfaces were
touched (auth, migrations, CI/CD, dependencies, secrets), whether a dangerous
construct or a credential was introduced, and whether changed source code arrived
WITHOUT a matching test change. Every factor is grounded in a real changed file
or a real added diff line.

Deterministic by design: `risk_score` and `risk_factors` come from the diff, not
an LLM. An optional, fail-open LLM pass rewrites ONLY the prose (`summary` +
`recommendation`) so it reads PR-specific — it never changes the score or the
factors. Same principle as the rest of ShipMate: the model writes words, never
numbers.

Runs only when the analyze request carried a pr_number (so context has both
`pr_info` and `pr_files`). For a plain branch analysis there is no PR, the
orchestrator skips this agent, and ShipMateReport.pr_risk stays None.

Note on the score direction: unlike the repo *_score fields (higher = healthier),
risk_score is 0-100 where HIGHER = RISKIER. It is a standalone signal and does
NOT feed the deterministic readiness_score.
"""
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .base_agent import BaseAgent
from ..schemas.agent_schemas import PRRiskFactor, PRRiskOutput, Severity
from ..services.llm_service import LLMService

# Severity → risk points. Summed across factors, capped at 100.
_RISK_POINTS = {
    Severity.CRITICAL: 35,
    Severity.HIGH: 18,
    Severity.MEDIUM: 9,
    Severity.LOW: 3,
    Severity.INFO: 0,
}

_SEV_ORDER = {
    Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2,
    Severity.LOW: 3, Severity.INFO: 4,
}

_SOURCE_EXTS = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs",
    ".java", ".kt", ".rb", ".php", ".cs", ".swift", ".scala",
)

# ── Path-based sensitive-surface rules ───────────────────────────────────────
# (category, severity, human label, path regex). A changed file matching the
# regex contributes one factor. Bias toward the HIGHEST-signal surfaces so the
# card stays meaningful rather than flagging every file.
_SURFACE_RULES = [
    ("auth", Severity.HIGH, "authentication / authorization code",
     re.compile(r"(auth|oauth|login|logout|session|token|password|passwd|credential|permission|rbac|\bjwt\b|crypto|security|guard|middleware)", re.I)),
    ("migration", Severity.HIGH, "database migration / schema",
     re.compile(r"(/migrations?/|alembic|schema\.sql|\.sql$|/models?\.py$|prisma/migrations|/knex)", re.I)),
    ("ci_cd", Severity.MEDIUM, "CI/CD or deployment config",
     re.compile(r"(\.github/workflows/|dockerfile|docker-compose|\.tf$|/k8s/|/helm/|nginx\.conf|procfile|pipelines?\.ya?ml|\.azure)", re.I)),
    ("deps", Severity.MEDIUM, "dependency manifest",
     re.compile(r"(requirements[\w-]*\.txt$|package\.json$|package-lock\.json$|yarn\.lock$|pnpm-lock|go\.mod$|go\.sum$|cargo\.(toml|lock)$|pyproject\.toml$|poetry\.lock$|gemfile)", re.I)),
    ("config", Severity.MEDIUM, "configuration / secrets surface",
     re.compile(r"(\.env|settings\.py|/config\b|config\.(py|ts|js|json|ya?ml)$|\.pem$|\.key$|secret)", re.I)),
]

# ── Added-line content rules (scanned on '+' lines only) ─────────────────────
# Introducing one of these in a diff is a strong signal regardless of the file.
_SECRET_LINE_RULES = [
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "GitHub personal access token literal"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "OpenAI-style API key literal"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id literal"),
    (re.compile(r"(?i)(password|passwd|secret|api[_-]?key|token)\s*[=:]\s*[\"'][^\"']{8,}[\"']"), "hardcoded credential literal"),
    (re.compile(r"(?i)(mongodb\+srv|postgres|postgresql|mysql|redis)://[^@\s]+:[^@\s]+@"), "database URL with inline credentials"),
]
_DANGER_LINE_RULES = [
    (re.compile(r"(?<![\w.])eval\s*\("), "introduces an eval() call"),
    (re.compile(r"(?<![\w.])exec\s*\("), "introduces an exec() call"),
    (re.compile(r"\bos\.system\s*\("), "introduces an os.system() call"),
    (re.compile(r"subprocess\.[A-Za-z_]+\([^)]*shell\s*=\s*True"), "introduces subprocess(shell=True)"),
]

_TEST_PATH_RE = re.compile(
    r"(^|/)tests?/|/__tests__/|(^|/)spec/|"
    r"(^|/)test_[^/]+\.py$|[^/]+_test\.py$|"
    r"[^/]+\.(test|spec)\.(t|j)sx?$",
    re.I,
)


def _is_test_path(path: str) -> bool:
    return bool(_TEST_PATH_RE.search(path or ""))


def _is_source(path: str) -> bool:
    p = (path or "").lower()
    if any(skip in p for skip in ("node_modules/", "/dist/", "/build/", "__pycache__/", ".min.")):
        return False
    return p.endswith(_SOURCE_EXTS)


def _added_lines(patch: Optional[str]) -> Iterable[str]:
    """Yield the ADDED lines of a unified-diff patch (lines starting with a
    single '+', excluding the '+++' file header). Pre-existing lines and removed
    lines are skipped — we only flag what the PR INTRODUCES."""
    if not patch:
        return
    for raw in patch.splitlines():
        if raw.startswith("+") and not raw.startswith("+++"):
            yield raw[1:]


def _stem(path: str) -> str:
    return Path(path).stem.lower()


class PRRiskAgent(BaseAgent):
    name = "pr_risk"
    description = "Scores the risk of a specific pull request from its real diff"

    def run(self, context: Dict[str, Any]) -> PRRiskOutput:
        pr_info: Dict[str, Any] = context.get("pr_info") or {}
        pr_files: List[Dict[str, Any]] = context.get("pr_files") or []

        pr_number = int(pr_info.get("number") or context.get("pr_number") or 0)
        title = pr_info.get("title") or ""

        # No diff available → a benign, explicit empty result rather than a crash.
        if not pr_files:
            return PRRiskOutput(
                pr_number=pr_number,
                title=title,
                summary="No changed-file diff was available for this PR, so no risk could be assessed.",
                recommendation="Re-run analysis once the PR has commits, or check that the token can read this PR.",
            )

        additions = sum(int(f.get("additions") or 0) for f in pr_files)
        deletions = sum(int(f.get("deletions") or 0) for f in pr_files)
        files_changed = len(pr_files)

        factors: List[PRRiskFactor] = []
        risky_surfaces: List[str] = []
        fid = 1

        def _add(category: str, severity: Severity, title_: str, desc: str,
                 file: Optional[str] = None, evidence: Optional[str] = None) -> None:
            nonlocal fid
            factors.append(PRRiskFactor(
                id=f"PRR-{fid:03d}", title=title_, severity=severity,
                category=category, description=desc, file=file, evidence=evidence,
            ))
            fid += 1

        # ── 1. Sensitive surfaces touched (path-based) ──────────────────────
        seen_surface: set = set()
        for f in pr_files:
            fname = f.get("filename") or ""
            status = f.get("status") or "modified"
            if status == "removed":
                continue  # deletions handled separately; don't double-count surface
            for category, severity, label, rx in _SURFACE_RULES:
                if category in seen_surface:
                    continue
                if rx.search(fname):
                    seen_surface.add(category)
                    risky_surfaces.append(label)
                    _add(category, severity, f"Touches {label}",
                         f"This PR modifies `{fname}`, a {label} surface — changes here "
                         "have outsized blast radius and warrant focused review.",
                         file=fname, evidence=fname)
                    break

        # ── 2. Introduced secrets / dangerous constructs (added lines) ──────
        for f in pr_files:
            fname = f.get("filename") or ""
            if _is_test_path(fname):
                continue  # fixtures/mocks intentionally carry fake creds + eval paths
            patch = f.get("patch")
            secret_hit = danger_hit = False
            for line in _added_lines(patch):
                if not secret_hit:
                    for rx, label in _SECRET_LINE_RULES:
                        if rx.search(line):
                            _add("secrets", Severity.CRITICAL,
                                 "Possible secret introduced in the diff",
                                 f"An added line in `{fname}` looks like a {label}. "
                                 "Committing a live credential exposes it to anyone with repo access.",
                                 file=fname, evidence=line.strip()[:120])
                            secret_hit = True
                            break
                if not danger_hit:
                    for rx, label in _DANGER_LINE_RULES:
                        if rx.search(line):
                            _add("injection", Severity.HIGH,
                                 "Dangerous construct introduced in the diff",
                                 f"An added line in `{fname}` {label}. If untrusted input can "
                                 "reach it, this is a code-execution risk.",
                                 file=fname, evidence=line.strip()[:120])
                            danger_hit = True
                            break
                if secret_hit and danger_hit:
                    break

        # ── 3. Changed source code without an accompanying test change ──────
        changed_test_blob = " ".join(
            (f.get("filename") or "").lower()
            for f in pr_files if _is_test_path(f.get("filename") or "")
        )
        changed_no_test: List[str] = []
        for f in pr_files:
            fname = f.get("filename") or ""
            status = f.get("status") or "modified"
            if status == "removed" or not _is_source(fname) or _is_test_path(fname):
                continue
            if _stem(fname) and _stem(fname) not in changed_test_blob:
                changed_no_test.append(fname)
        if changed_no_test:
            sev = Severity.MEDIUM if len(changed_no_test) >= 3 else Severity.LOW
            preview = ", ".join(f"`{p}`" for p in changed_no_test[:4])
            _add("tests", sev, "Changed source code without matching tests",
                 f"{len(changed_no_test)} changed source file(s) have no accompanying test "
                 f"change in this PR ({preview}). Untested changes raise regression risk.",
                 file=changed_no_test[0])

        # ── 4. Blast radius / reviewability (size) ──────────────────────────
        if files_changed > 25:
            _add("size", Severity.MEDIUM, "Large PR — hard to review in one pass",
                 f"This PR changes {files_changed} files; large PRs hide regressions and "
                 "slow review. Consider splitting into focused changes.")
        elif files_changed > 12:
            _add("size", Severity.LOW, "Sizeable PR",
                 f"This PR changes {files_changed} files — keep an eye on reviewability.")
        if additions > 1500:
            _add("size", Severity.HIGH, "Very large diff",
                 f"+{additions} lines added. A diff this big is rarely reviewed thoroughly.")
        elif additions > 600:
            _add("size", Severity.MEDIUM, "Large diff",
                 f"+{additions} lines added — review carefully, especially untested paths.")

        # ── Score + level (deterministic) ───────────────────────────────────
        risk_score = min(100, sum(_RISK_POINTS.get(fc.severity, 0) for fc in factors))
        risk_level = self._level(risk_score)
        # Severity floor: a lone CRITICAL factor (e.g. a committed credential) or
        # a HIGH one (auth change, very large diff) must NOT be downgraded just
        # because the PR is otherwise small. The additive score still escalates
        # when several factors stack; MEDIUM/LOW factors ride the score only.
        if factors:
            top_sev = min(_SEV_ORDER.get(fc.severity, 9) for fc in factors)
            if top_sev == _SEV_ORDER[Severity.CRITICAL]:
                risk_level = self._max_level(risk_level, "critical")
            elif top_sev == _SEV_ORDER[Severity.HIGH]:
                risk_level = self._max_level(risk_level, "high")
        factors.sort(key=lambda fc: _SEV_ORDER.get(fc.severity, 9))
        # Dedupe risky_surfaces while preserving order.
        risky_surfaces = list(dict.fromkeys(risky_surfaces))

        summary, recommendation = self._deterministic_prose(
            pr_number, title, files_changed, additions, deletions,
            risk_level, factors, risky_surfaces,
        )

        out = PRRiskOutput(
            pr_number=pr_number,
            title=title,
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
            net_lines=additions - deletions,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=factors,
            risky_surfaces=risky_surfaces,
            changed_files_without_tests=changed_no_test[:20],
            summary=summary,
            recommendation=recommendation,
        )
        # Optional, fail-open: let the LLM rewrite ONLY the prose so it reads
        # PR-specific. Numbers/factors are never touched. No provider → base.
        return self._enhance_prose(context, out)

    # ── helpers ───────────────────────────────────────────────────────────────

    _LEVEL_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    @staticmethod
    def _level(score: int) -> str:
        if score >= 70:
            return "critical"
        if score >= 45:
            return "high"
        if score >= 20:
            return "medium"
        return "low"

    @classmethod
    def _max_level(cls, a: str, b: str) -> str:
        """Return the more severe of two risk levels."""
        return a if cls._LEVEL_RANK.get(a, 0) >= cls._LEVEL_RANK.get(b, 0) else b

    @staticmethod
    def _deterministic_prose(
        pr_number, title, files_changed, additions, deletions,
        risk_level, factors: List[PRRiskFactor], risky_surfaces: List[str],
    ):
        surfaces = (", ".join(risky_surfaces[:3]) + ".") if risky_surfaces else "no high-risk surfaces."
        summary = (
            f"PR #{pr_number} changes {files_changed} file(s) (+{additions}/-{deletions}) and "
            f"touches {surfaces} Overall PR risk: {risk_level.upper()}."
        )
        if factors:
            top = factors[0]
            recommendation = (
                f"Prioritize review of: {top.title.lower()}"
                + (f" in `{top.file}`" if top.file else "")
                + ". Confirm tests cover the changed paths before merging."
            )
        else:
            recommendation = "Low-risk change — a standard review should suffice."
        return summary, recommendation

    def _enhance_prose(self, context: Dict[str, Any], base: PRRiskOutput) -> PRRiskOutput:
        """Optional LLM pass: rewrite summary + recommendation to be PR-specific.
        Fail-open and prose-only — score/factors are immutable here. Any failure
        (no provider, parse error, timeout) returns `base` unchanged."""
        try:
            provider = LLMService.provider()
        except Exception:
            provider = None
        if provider is None or not base.risk_factors:
            return base

        from pydantic import BaseModel, Field

        class _PRRiskNarrative(BaseModel):
            summary: str = Field(..., description="2 sentences: the PR's risk in plain English, citing the riskiest factor.")
            recommendation: str = Field(..., description="1-2 sentences: the single most important thing a reviewer should check before merging.")

        factor_lines = "\n".join(
            f"- [{fc.severity.value}] {fc.title}" + (f" ({fc.file})" if fc.file else "")
            for fc in base.risk_factors[:8]
        )
        system = (
            "You are a staff engineer triaging a pull request. You are given a PR's "
            "deterministic risk factors. Write a crisp, specific summary + the one "
            "review action that matters most. Do NOT invent factors beyond those listed; "
            "do NOT mention a numeric score."
        )
        user = (
            f"PR #{base.pr_number}: {base.title}\n"
            f"{base.files_changed} files, +{base.additions}/-{base.deletions}, "
            f"risk level {base.risk_level}.\n\n# Risk factors\n{factor_lines}\n\n"
            "Return ONLY the requested fields."
        )
        try:
            narr = provider.invoke_structured_sync(
                system_prompt=system, user_prompt=user,
                schema_class=_PRRiskNarrative, deployment_hint="fast",
            )
            return base.model_copy(update={
                "summary": narr.summary or base.summary,
                "recommendation": narr.recommendation or base.recommendation,
            })
        except Exception:
            return base
