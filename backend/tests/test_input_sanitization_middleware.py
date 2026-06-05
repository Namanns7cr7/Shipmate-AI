"""Integration tests for input_sanitization_middleware (SEC-004).

Each test imports the real `app` object and sends requests through the full
middleware stack.  A blocked payload MUST return 400; a clean payload MUST
not return 400 from the middleware (we accept any non-400 response from the
router layer for clean payloads).
"""
import io
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BLOCKED_DETAIL = "Request contains disallowed content"


def _assert_blocked(response):
    assert response.status_code == 400, (
        f"Expected 400 but got {response.status_code}; body={response.text}"
    )
    assert BLOCKED_DETAIL in response.text


# ---------------------------------------------------------------------------
# JSON body tests
# ---------------------------------------------------------------------------


class TestJsonBodyBlocked:
    """Dangerous patterns in JSON bodies must be blocked."""

    def test_eval_in_top_level_string_value(self):
        payload = {"prompt": "eval(malicious_code())"}
        resp = client.post(
            "/api/analysis/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        _assert_blocked(resp)

    def test_exec_in_nested_dict_value(self):
        payload = {"outer": {"inner": "exec(open('/etc/passwd').read())"}}
        resp = client.post(
            "/api/analysis/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        _assert_blocked(resp)

    def test_dunder_import_in_list_element(self):
        payload = {"items": ["safe", "__import__('os').system('id')"]}
        resp = client.post(
            "/api/analysis/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        _assert_blocked(resp)

    def test_subprocess_in_json_value(self):
        payload = {"cmd": "subprocess.run(['ls', '-la'])"}
        resp = client.post(
            "/api/analysis/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        _assert_blocked(resp)

    def test_os_system_in_json_value(self):
        payload = {"action": "os.system('rm -rf /')"}
        resp = client.post(
            "/api/analysis/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        _assert_blocked(resp)

    def test_globals_dunder_in_json_value(self):
        payload = {"x": "print(__globals__)"}
        resp = client.post(
            "/api/analysis/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        _assert_blocked(resp)


class TestJsonBodyAllowed:
    """Clean JSON bodies must not be blocked by the middleware."""

    def test_clean_json_not_blocked(self):
        payload = {"repo": "owner/repo", "branch": "main"}
        resp = client.post(
            "/api/analysis/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        # Middleware must not return 400; router may return anything else
        assert resp.status_code != 400, (
            f"Clean payload was incorrectly blocked: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Form-encoded body tests
# ---------------------------------------------------------------------------


class TestFormBodyBlocked:
    """Dangerous patterns in application/x-www-form-urlencoded bodies must be blocked."""

    def test_eval_in_form_field(self):
        resp = client.post(
            "/api/analysis/analyze",
            data={"field": "eval(dangerous())"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        _assert_blocked(resp)

    def test_exec_in_form_field(self):
        resp = client.post(
            "/api/analysis/analyze",
            data={"cmd": "exec('import os')" },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        _assert_blocked(resp)

    def test_subprocess_in_form_field(self):
        resp = client.post(
            "/api/analysis/analyze",
            data={"value": "subprocess.Popen(['id'])"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        _assert_blocked(resp)


class TestFormBodyAllowed:
    """Clean form bodies must not be blocked by the middleware."""

    def test_clean_form_not_blocked(self):
        resp = client.post(
            "/api/analysis/analyze",
            data={"repo": "owner/repo", "branch": "main"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code != 400, (
            f"Clean form payload was incorrectly blocked: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Multipart body tests
# ---------------------------------------------------------------------------


class TestMultipartBodyBlocked:
    """Dangerous patterns in multipart/form-data bodies must be blocked."""

    def test_eval_in_multipart_field(self):
        resp = client.post(
            "/api/analysis/analyze",
            files={"upload": ("test.txt", io.BytesIO(b"eval(bad())"), "text/plain")},
        )
        _assert_blocked(resp)

    def test_exec_in_multipart_field(self):
        resp = client.post(
            "/api/analysis/analyze",
            files={"upload": ("test.txt", io.BytesIO(b"exec('import subprocess')"), "text/plain")},
        )
        _assert_blocked(resp)

    def test_dunder_import_in_multipart_field(self):
        resp = client.post(
            "/api/analysis/analyze",
            files={"upload": ("test.txt", io.BytesIO(b"__import__('os')"), "text/plain")},
        )
        _assert_blocked(resp)


class TestMultipartBodyAllowed:
    """Clean multipart bodies must not be blocked by the middleware."""

    def test_clean_multipart_not_blocked(self):
        resp = client.post(
            "/api/analysis/analyze",
            files={"upload": ("readme.txt", io.BytesIO(b"Hello, world!"), "text/plain")},
        )
        assert resp.status_code != 400, (
            f"Clean multipart payload was incorrectly blocked: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Query parameter tests
# ---------------------------------------------------------------------------


class TestQueryParamBlocked:
    """Dangerous patterns in query parameters must be blocked."""

    def test_eval_in_query_param(self):
        resp = client.get("/api/analysis/analyze?q=eval(bad())")
        _assert_blocked(resp)

    def test_subprocess_in_query_param(self):
        resp = client.get("/api/analysis/analyze?cmd=subprocess.run(['id'])")
        _assert_blocked(resp)


class TestQueryParamAllowed:
    """Clean query parameters must not be blocked by the middleware."""

    def test_clean_query_not_blocked(self):
        resp = client.get("/api/analysis/analyze?repo=owner%2Frepo&branch=main")
        assert resp.status_code != 400, (
            f"Clean query param was incorrectly blocked: {resp.text}"
        )
