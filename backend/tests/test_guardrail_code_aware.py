"""Tests for GuardRail's code-aware injection / plain-HTTP detectors.

These guard the fix for the single biggest source of recurring false-positive
findings: GuardRail used to substring-scan repo files for "eval(" / "__import__"
/ "http://"+token, which flagged its OWN anti-injection regexes and localhost
dev URLs. The detectors are now code-aware — these tests pin that behavior so a
future refactor can't reintroduce the noise.
"""
from app.agents.guardrail_agent import (
    _has_real_dynamic_exec,
    _has_insecure_http_with_auth,
)


class TestRealDynamicExec:
    def test_genuine_eval_call_is_flagged(self):
        assert _has_real_dynamic_exec("def h(x):\n    return eval(x)\n") is True

    def test_genuine_exec_call_is_flagged(self):
        assert _has_real_dynamic_exec("exec(user_code)\n") is True

    def test_genuine_dunder_import_call_is_flagged(self):
        assert _has_real_dynamic_exec("mod = __import__(name)\n") is True

    def test_detection_regex_literal_is_not_flagged(self):
        # The exact shape of main.py's anti-injection pattern must NOT trip.
        src = 're.compile(r"eval\\s*\\(", re.IGNORECASE)\n'
        assert _has_real_dynamic_exec(src) is False

    def test_denylist_string_names_are_not_flagged(self):
        src = '_RISKY = {"eval", "exec"}\nbad = "__import__"\n'
        assert _has_real_dynamic_exec(src) is False

    def test_comment_mentioning_eval_is_not_flagged(self):
        src = "# never call eval() on user input\n"
        assert _has_real_dynamic_exec(src) is False

    def test_substring_in_identifier_is_not_flagged(self):
        # `medieval(` / `evaluate(` must not match (word-ish boundary).
        assert _has_real_dynamic_exec("result = evaluate(data)\n") is False

    def test_real_eval_among_defensive_lines_still_flagged(self):
        # A file that is mostly defensive but has ONE real call must flag.
        src = (
            '_DANGEROUS = [re.compile(r"eval\\s*\\(")]\n'
            "# guard\n"
            "value = eval(payload)\n"
        )
        assert _has_real_dynamic_exec(src) is True

    def test_actual_main_module_is_not_flagged(self):
        # Regression: scanning the real main.py (full of detection patterns)
        # must not report dynamic execution.
        import app.main as m
        src = open(m.__file__).read()
        assert _has_real_dynamic_exec(src) is False


class TestInsecureHttpWithAuth:
    def test_localhost_http_with_token_not_flagged(self):
        assert _has_insecure_http_with_auth("http://localhost:5173 token") is False

    def test_127_http_with_auth_not_flagged(self):
        assert _has_insecure_http_with_auth("http://127.0.0.1:8000 auth header") is False

    def test_remote_http_with_token_flagged(self):
        assert _has_insecure_http_with_auth("base = http://api.evil.com  token=x") is True

    def test_https_with_token_not_flagged(self):
        assert _has_insecure_http_with_auth("https://api.github.com bearer token") is False

    def test_remote_http_without_auth_not_flagged(self):
        # http to a remote host but no token/auth context -> not this finding.
        assert _has_insecure_http_with_auth("fetch http://example.com/page") is False
