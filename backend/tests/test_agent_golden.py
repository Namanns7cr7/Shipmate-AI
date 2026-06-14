"""Golden / snapshot tests over a frozen fixture corpus (A4).

Agent findings are LLM-generated, so regressions are normally invisible until a
dogfood loop surfaces them: a prompt or heuristic tweak could silently start
re-proposing shipped work, or stop suppressing a known false positive, and no
test would catch it.

These tests freeze two repo snapshots and assert STRUCTURAL properties of the
agents' deterministic (LLM-off) output — not exact prose, which would be brittle.
They directly guard the anti-recurrence + code-aware-detection work:
  • On a HARDENED repo (all 9 security controls present), GuardRail's heuristic
    pass must NOT raise the known false positives (defensive regexes flagged as
    injection; 'jwt' substring; localhost http), and _detect_security_controls
    must recognise the controls that exist.
  • On a VULNERABLE repo, GuardRail MUST catch the real issues (hardcoded secret,
    wildcard CORS, real eval() call).
Running with the provider forced off keeps these fast + deterministic.
"""
import pytest

from app.agents.guardrail_agent import GuardRailAgent, _has_real_dynamic_exec
from app.agents.repo_lens_agent import RepoLensAgent
from app.agents.testpilot_agent import TestPilotAgent
from app.services.llm_service import _detect_security_controls


@pytest.fixture(autouse=True)
def _llm_off(monkeypatch):
    import app.services.llm_service as llm
    monkeypatch.setattr(llm, "_get_provider", lambda: None)


# ── Fixture corpus: a HARDENED repo (defensive code + all controls present) ──

_HARDENED_MAIN = '''
import os, re, hmac, hashlib
from fastapi import FastAPI, Request

app = FastAPI()

# Anti-injection middleware — these are DETECTION regexes, NOT calls. GuardRail
# must not flag them as "dynamic code execution".
_DANGEROUS_PATTERNS = [
    re.compile(r"eval\\s*\\("),
    re.compile(r"exec\\s*\\("),
    re.compile(r"__import__\\s*\\("),
]

def _contains_dangerous_pattern(text: str) -> bool:
    return any(p.search(text) for p in _DANGEROUS_PATTERNS)

ALLOWED_ORIGINS = ["https://app.example.com"]
def _validate_origin(origin: str) -> bool:
    return origin in ALLOWED_ORIGINS

async def security_headers_middleware(request, call_next):
    resp = await call_next(request)
    resp.headers["Strict-Transport-Security"] = "max-age=63072000"
    resp.headers["X-Frame-Options"] = "DENY"
    return resp

def _verify_github_webhook_signature(secret: bytes, body: bytes, sig: str) -> bool:
    mac = hmac.new(secret, body, hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig)
'''

_HARDENED_AUTH = '''
from fastapi import Depends, Header
from app.services import session_store

def resolve_access_token(authorization: str = Header(None)) -> str:
    """Header-only — never a query param."""
    return session_store.resolve(authorization)

async def verify_repo_write_access(owner, repo, token):
    ...

# OAuth state persisted to sqlite, single-use — survives restart.
def _store_state(state): ...
def _consume_state(state): ...
'''

_HARDENED_ANALYSIS = '''
from app.api.deps import resolve_access_token
from app.services import report_store

async def analyze(req):
    await verify_repo_write_access(req.owner, req.repo, req.token)
    report = run()
    report_store.save_report(report)   # results persisted
    return report
'''


def _hardened_ctx():
    key_files = {
        "backend/app/main.py": _HARDENED_MAIN,
        "backend/app/api/deps.py": _HARDENED_AUTH,
        "backend/app/api/routes/analysis.py": _HARDENED_ANALYSIS,
        "backend/app/services/session_store.py": "def mint(access_token): ...\n_PREFIX='shipmate_sess_'\n",
        "requirements.txt": "fastapi\npytest\n",
    }
    return {
        "repo_info": {"full_name": "octo/hardened", "owner": {"login": "octo"},
                      "name": "hardened"},
        "branch": "main",
        "file_tree": list(key_files) + ["backend/tests/test_main.py", "nginx/ssl.conf"],
        "key_files": key_files,
        "feature_context": "",
    }


# ── Fixture corpus: a VULNERABLE repo (real issues present) ──────────────────

_VULN_MAIN = '''
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

API_KEY = "sk-supersecretkey1234567890abcdef"   # hardcoded secret

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # wildcard CORS
    allow_credentials=True,
)

@app.get("/run")
def run(code: str):
    return str(eval(code))   # REAL eval() call on user input
'''


def _vuln_ctx():
    key_files = {"app.py": _VULN_MAIN}
    return {
        "repo_info": {"full_name": "octo/vuln", "owner": {"login": "octo"}, "name": "vuln"},
        "branch": "main",
        "file_tree": ["app.py"],
        "key_files": key_files,
        "feature_context": "",
    }


# ── Detection-helper goldens (pure functions, no agent) ──────────────────────

class TestDynamicExecDetection:
    def test_defensive_regexes_are_not_a_real_call(self):
        # The hardened main.py mentions eval/exec ONLY in detection regexes.
        assert _has_real_dynamic_exec(_HARDENED_MAIN) is False

    def test_real_eval_call_is_detected(self):
        assert _has_real_dynamic_exec(_VULN_MAIN) is True


class TestSecurityControlDigest:
    def test_hardened_repo_controls_are_recognised(self):
        ctx = _hardened_ctx()
        controls = _detect_security_controls(ctx["key_files"], ctx["file_tree"])
        # The known controls whose proofs are in the fixture must all be found.
        blob = " ".join(c.lower() for c in controls)
        assert "oauth" in blob              # _consume_state / _store_state
        assert "session_store" in blob or "vaulted" in blob
        assert any("authorization header" in c.lower() or "resolve_access_token" in c.lower()
                   for c in controls)
        assert any("cors" in c.lower() for c in controls)
        assert any("header" in c.lower() for c in controls)  # security headers
        assert any("webhook" in c.lower() for c in controls)
        assert any("persist" in c.lower() or "report_store" in c.lower() for c in controls)
        # At least 6 of the 9 known controls present in this fixture.
        assert len(controls) >= 6

    def test_vulnerable_repo_has_few_controls(self):
        ctx = _vuln_ctx()
        controls = _detect_security_controls(ctx["key_files"], ctx["file_tree"])
        assert len(controls) == 0


# ── GuardRail heuristic goldens ──────────────────────────────────────────────

class TestGuardRailGolden:
    def test_hardened_repo_no_false_positive_injection(self):
        out = GuardRailAgent().run(_hardened_ctx())
        titles = " ".join(f.title.lower() for f in out.findings)
        # The defensive anti-injection regexes must NOT be flagged as a real
        # dynamic-execution finding (the chronic recurrence this guards).
        assert "dynamic code execution" not in titles

    def test_hardened_repo_no_jwt_false_positive(self):
        out = GuardRailAgent().run(_hardened_ctx())
        titles = " ".join(f.title.lower() for f in out.findings)
        # No JWT anywhere in the fixture → no JWT finding.
        assert "jwt" not in titles

    def test_vulnerable_repo_catches_real_issues(self):
        out = GuardRailAgent().run(_vuln_ctx())
        titles = " ".join(f.title.lower() for f in out.findings)
        cats = {f.category for f in out.findings}
        # Hardcoded secret + wildcard CORS + real eval are all present.
        assert "secrets" in cats
        assert any("cors" in t for t in titles) or "cors" in cats
        assert "injection" in cats  # the real eval() call

    def test_vulnerable_repo_scores_lower_than_hardened(self):
        vuln = GuardRailAgent().run(_vuln_ctx())
        hard = GuardRailAgent().run(_hardened_ctx())
        assert vuln.security_score < hard.security_score


# ── RepoLens / TestPilot structural goldens ──────────────────────────────────

class TestRepoLensGolden:
    def test_detects_python_and_entry_points(self):
        out = RepoLensAgent().run(_hardened_ctx())
        assert out.primary_language == "Python"
        assert out.file_count == len(_hardened_ctx()["file_tree"])
        assert 0 <= out.repo_score <= 100


class TestTestPilotGolden:
    def test_flags_missing_coverage_and_scores(self):
        ctx = _hardened_ctx()
        ctx["repo_lens"] = RepoLensAgent().run(ctx)
        out = TestPilotAgent().run(ctx)
        assert 0 <= out.test_score <= 100
        assert out.qa_readiness in ("not_ready", "partial", "ready")
        # Exactly one test file in the fixture tree → existing_tests.count == 1.
        assert out.existing_tests.count == 1
