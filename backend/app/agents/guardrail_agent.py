import re
from typing import Any, Dict, List

from .base_agent import BaseAgent
from ..schemas.agent_schemas import GuardRailOutput, SecurityFinding, Severity
from ..services.llm_service import LLMService

# ── Code-aware injection detection ───────────────────────────────────────────
# A naive substring scan for "eval(" / "__import__" produces chronic false
# positives, because a *defensive* codebase mentions those tokens precisely to
# block them: a regex literal `re.compile(r"eval\s*\(")`, a denylist string
# `"eval"`, a sanitiser comment, or a security test. Flagging that as "dynamic
# code execution detected" is the single biggest source of recurring noise.
#
# These regexes match a REAL dynamic-execution CALL — the token followed by an
# opening paren that is NOT itself inside a string/regex literal context. We
# additionally drop any line that is clearly a pattern definition, denylist, or
# comment (see _is_detection_or_defensive_line). Bias: prefer a false NEGATIVE
# (miss a contrived case) over the false POSITIVE that trains users to ignore
# the agent entirely.
# The call token must NOT be preceded by a quote, word char, dot, or BACKTICK
# (backtick guards against Markdown/docstring prose like `eval(`).
_EVAL_CALL_RE = re.compile(r"(?<![\"'`\w.])eval\s*\(")
_EXEC_CALL_RE = re.compile(r"(?<![\"'`\w.])exec\s*\(")
_DYN_IMPORT_CALL_RE = re.compile(r"(?<![\"'`\w.])__import__\s*\(")

# Markers that mean a line is defining/blocking these tokens rather than calling
# them: a regex literal, a denylist entry, a detection helper, or a comment.
# Kept to STRUCTURAL signals only — prose-word heuristics (e.g. "payload") were
# tried and rejected because they collide with legitimate variable names. The
# backtick check below handles documentation/Markdown prose instead.
_DEFENSIVE_LINE_MARKERS = (
    "re.compile", "re.search", "re.match", "re.findall",
    "_dangerous", "dangerous_pattern", "blocklist", "denylist",
    "_risky", "sanitize", "sanitiz", "detect", "pattern",
)


def _has_real_dynamic_exec(content: str) -> bool:
    """True only if *content* contains a genuine eval/exec/__import__ CALL that
    is not part of a detection pattern, denylist, comment, docstring prose, or
    string literal.

    Walks line-by-line so one defensive line (e.g. the anti-injection regex or
    the documentation in main.py) can't poison the whole-file check the way the
    old `"eval(" in combined` did. Bias toward false-negative: when a line looks
    even slightly like prose/defense, skip it — the pytest gate and human review
    catch a genuinely-missed call, but a false positive trains users to ignore
    the agent entirely."""
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Skip pure comment lines and docstring delimiters (prose, not calls).
        if line.startswith("#") or line.startswith('"""') or line.startswith("'''"):
            continue
        # Skip lines where the token is wrapped in backticks anywhere — Markdown
        # / docstring prose like `eval(` that documents rather than executes.
        if "`" in line:
            continue
        lowered = line.lower()
        # Skip lines that are clearly defining/blocking these tokens (regex
        # literal, denylist, detection helper).
        if any(marker in lowered for marker in _DEFENSIVE_LINE_MARKERS):
            continue
        if _EVAL_CALL_RE.search(line) or _EXEC_CALL_RE.search(line) or _DYN_IMPORT_CALL_RE.search(line):
            return True
    return False


# A non-local http:// URL (anything but localhost/127.0.0.1/0.0.0.0/::1/*.local).
_NONLOCAL_HTTP_RE = re.compile(
    r"http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|\[?::1\]?|[\w-]+\.local\b)[\w.-]+",
    re.IGNORECASE,
)


def _has_insecure_http_with_auth(combined_lower: str) -> bool:
    """True only if a NON-local http:// URL coexists with auth/token handling.

    The old check fired on any `http://` (including localhost dev servers and
    the OAuth redirect to localhost:5173), which is not a real TLS risk and made
    the finding chronic noise. We require a remote http endpoint."""
    if not ("token" in combined_lower or "auth" in combined_lower):
        return False
    return _NONLOCAL_HTTP_RE.search(combined_lower) is not None

# Patterns that suggest hardcoded secrets
_SECRET_PATTERNS = [
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{6,}["\']', "Hardcoded password"),
    (r'(?i)(secret|api_key|apikey|token)\s*=\s*["\'][^"\']{10,}["\']', "Hardcoded secret/token"),
    (r'(?i)sk-[a-zA-Z0-9]{20,}', "OpenAI API key pattern"),
    (r'(?i)ghp_[a-zA-Z0-9]{36}', "GitHub personal access token"),
    (r'(?i)AKIA[0-9A-Z]{16}', "AWS access key"),
    (r'(?i)(mongodb\+srv|postgres|mysql|redis)://[^@\s]+:[^@\s]+@', "Database URL with credentials"),
]

# Known vulnerable / risky npm packages
_RISKY_NPM = {"node-serialize", "serialize-javascript", "lodash", "minimist",
              "node-ipc", "colors", "faker"}

# Known risky Python packages
_RISKY_PY = {"pickle", "yaml", "subprocess", "eval", "exec"}

# CORS wildcard patterns
_CORS_WILD = re.compile(r'(?i)allow_origins\s*=\s*\[?\s*["\'\*]', re.MULTILINE)
_CORS_STAR = re.compile(r'(?i)Access-Control-Allow-Origin["\']?\s*[:=]\s*["\']?\s*\*')


class GuardRailAgent(BaseAgent):
    name = "guardrail"
    description = "Security risk scanner: secrets, auth, CORS, injection, and dependency vulnerabilities"

    def run(self, context: Dict[str, Any]) -> GuardRailOutput:
        tree = self._file_tree(context)
        kf = self._key_files(context)
        repo_lens = context.get("repo_lens")

        findings: List[SecurityFinding] = []
        exposed_secrets: List[str] = []
        cors_issues: List[str] = []
        auth_risks: List[str] = []
        dep_vulns: List[str] = []

        fid = 1

        # ── Secret scanning ────────────────────────────────────────────────
        for filename, content in kf.items():
            if not content:
                continue
            for pattern, label in _SECRET_PATTERNS:
                if re.search(pattern, content):
                    exposed_secrets.append(f"{label} in {filename}")
                    findings.append(SecurityFinding(
                        id=f"SEC-{fid:03d}",
                        title=f"{label} detected",
                        severity=Severity.CRITICAL,
                        category="secrets",
                        description=f"A {label.lower()} was found hardcoded in `{filename}`. "
                                    "This credential is now exposed to anyone with repository access.",
                        recommendation="Remove immediately, rotate the credential, and use environment variables or a secrets manager.",
                        file=filename,
                    ))
                    fid += 1
                    break  # one finding per file

        # ── .env committed ─────────────────────────────────────────────────
        if ".env" in tree:
            findings.append(SecurityFinding(
                id=f"SEC-{fid:03d}",
                title=".env file committed to repository",
                severity=Severity.CRITICAL,
                category="secrets",
                description="The .env file containing environment variables is tracked by Git. "
                            "All secrets inside are exposed to anyone with read access.",
                recommendation="Delete from Git history (`git rm --cached .env`), add `.env` to .gitignore, "
                               "and rotate all exposed credentials immediately.",
                file=".env",
            ))
            exposed_secrets.append(".env file committed")
            fid += 1

        # ── CORS analysis ──────────────────────────────────────────────────
        for filename, content in kf.items():
            if not content:
                continue
            if _CORS_WILD.search(content) or _CORS_STAR.search(content):
                cors_issues.append(f"Wildcard CORS origin in {filename}")
                findings.append(SecurityFinding(
                    id=f"SEC-{fid:03d}",
                    title="Overly permissive CORS configuration",
                    severity=Severity.HIGH,
                    category="cors",
                    description=f"Wildcard `*` CORS origin detected in `{filename}`. "
                                "This allows any domain to make authenticated cross-origin requests.",
                    recommendation="Restrict allowed origins to explicit domains. "
                                   "Use environment-variable–driven origin lists.",
                    file=filename,
                ))
                fid += 1

        # ── Auth risks ─────────────────────────────────────────────────────
        combined = " ".join(kf.values()).lower()

        if "jwt" in combined and "secret" in combined and "env" not in combined[:500]:
            auth_risks.append("JWT secret may not be loaded from environment variables")
            findings.append(SecurityFinding(
                id=f"SEC-{fid:03d}",
                title="JWT secret not loaded from environment",
                severity=Severity.HIGH,
                category="auth",
                description="JWT secret appears to be hardcoded rather than injected via environment variable.",
                recommendation="Load JWT secret exclusively from `os.environ` / `process.env` and never commit it.",
            ))
            fid += 1

        # Plain-HTTP-with-tokens: only flag a NON-localhost http:// URL. Localhost
        # http (dev servers, OAuth redirect to localhost:5173, the vite proxy) is
        # not a TLS risk, and flagging it trained users to ignore this finding.
        if _has_insecure_http_with_auth(combined):
            auth_risks.append("Tokens may be transmitted over plain HTTP")
            findings.append(SecurityFinding(
                id=f"SEC-{fid:03d}",
                title="Auth tokens potentially sent over plain HTTP",
                severity=Severity.MEDIUM,
                category="auth",
                description="A non-local `http://` (non-TLS) URL appears alongside auth/token "
                            "handling. Tokens transmitted over HTTP are vulnerable to interception.",
                recommendation="Enforce HTTPS everywhere. Use HSTS headers in production.",
            ))
            fid += 1

        # Dynamic code execution: code-aware — only a REAL eval/exec/__import__
        # CALL counts, never a detection regex, denylist entry, comment, or test.
        # (A security codebase mentions these tokens precisely to BLOCK them; the
        # old substring check flagged its own anti-injection middleware.)
        if any(_has_real_dynamic_exec(c) for c in kf.values() if c):
            findings.append(SecurityFinding(
                id=f"SEC-{fid:03d}",
                title="Dynamic code execution detected",
                severity=Severity.HIGH,
                category="injection",
                description="A genuine `eval()`, `exec()`, or `__import__()` call was found. "
                            "If user input reaches these calls, arbitrary code execution is possible.",
                recommendation="Replace dynamic execution with safe alternatives. "
                               "Never pass untrusted input to eval/exec/__import__.",
            ))
            fid += 1

        # ── Dependency vulnerability checks ────────────────────────────────
        if repo_lens:
            npm_deps = set(repo_lens.dependency_summary.get("npm", []))
            for risky in _RISKY_NPM & npm_deps:
                dep_vulns.append(f"npm: {risky}")
                findings.append(SecurityFinding(
                    id=f"SEC-{fid:03d}",
                    title=f"Potentially risky npm package: {risky}",
                    severity=Severity.MEDIUM,
                    category="deps",
                    description=f"Package `{risky}` has known vulnerabilities or supply-chain risks.",
                    recommendation="Run `npm audit` and upgrade or replace this package.",
                ))
                fid += 1

            py_deps = set(d.lower() for d in repo_lens.dependency_summary.get("python", []))
            if "pyyaml" in py_deps or "yaml" in py_deps:
                dep_vulns.append("python: PyYAML unsafe load")
                findings.append(SecurityFinding(
                    id=f"SEC-{fid:03d}",
                    title="PyYAML unsafe load usage risk",
                    severity=Severity.MEDIUM,
                    category="deps",
                    description="`yaml.load()` without Loader can lead to arbitrary code execution if parsing untrusted YAML.",
                    recommendation="Always use `yaml.safe_load()` instead of `yaml.load()`.",
                ))
                fid += 1

        # ── No HTTPS enforcement ───────────────────────────────────────────
        if not any("ssl" in f.lower() or "https" in f.lower() or "nginx" in f.lower() for f in tree):
            findings.append(SecurityFinding(
                id=f"SEC-{fid:03d}",
                title="No HTTPS/TLS enforcement detected",
                severity=Severity.MEDIUM,
                category="config",
                description="No Nginx config, SSL certificate setup, or HTTPS redirect detected.",
                recommendation="Configure HTTPS with a valid TLS certificate. "
                               "Use Let's Encrypt or a cloud load-balancer for TLS termination.",
            ))
            fid += 1

        # ── Score ──────────────────────────────────────────────────────────
        score = self._score(findings, exposed_secrets)

        # Sort findings by severity
        SEV_ORDER = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3, Severity.INFO: 4}
        findings.sort(key=lambda f: SEV_ORDER.get(f.severity, 99))

        base = GuardRailOutput(
            findings=findings,
            exposed_secrets=exposed_secrets,
            cors_issues=cors_issues,
            auth_risks=auth_risks,
            dependency_vulnerabilities=dep_vulns,
            security_score=score,
        )
        # Step 1: rewrite prose on heuristic findings.
        enhanced = LLMService.enhance(self.name, context, base)
        # Step 2: append LLM-discovered findings grounded in real auth/CORS code.
        return LLMService.discover_guardrail(context, enhanced)

    def _score(self, findings: List[SecurityFinding], secrets: List[str]) -> int:
        s = 100
        for f in findings:
            if f.severity == Severity.CRITICAL: s -= 25
            elif f.severity == Severity.HIGH:   s -= 15
            elif f.severity == Severity.MEDIUM: s -= 8
            elif f.severity == Severity.LOW:    s -= 3
        if secrets:
            s -= 10  # extra penalty for confirmed exposed secrets
        return max(0, min(100, s))
