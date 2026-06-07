"""Tests for production-hardening changes:
  - Swagger /docs + /redoc + /openapi gated off when ENVIRONMENT=production
  - sanitize middleware defeats encoding-based blocklist evasion
  - security-headers middleware emits the always-on headers
  - report_store round-trip (persist + list + get)
"""
import importlib
import os
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport


# ── Docs gating ──────────────────────────────────────────────────────────────

class TestDocsGating:
    def test_docs_enabled_in_development(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            import app.main as m
            importlib.reload(m)
            assert m.app.docs_url == "/docs"
            assert m.app.openapi_url == "/openapi.json"

    def test_docs_disabled_in_production(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            import app.main as m
            importlib.reload(m)
            assert m.app.docs_url is None
            assert m.app.redoc_url is None
            assert m.app.openapi_url is None
        # Restore the module to dev state so later tests see the default app.
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            importlib.reload(m)


# ── Encoding-bypass hardening ────────────────────────────────────────────────

class TestEncodingBypass:
    def test_raw_eval_detected(self):
        from app.main import _contains_dangerous_pattern
        assert _contains_dangerous_pattern("eval(x)") is True

    def test_single_url_encoded_eval_detected(self):
        from app.main import _contains_dangerous_pattern
        assert _contains_dangerous_pattern("eval%28x%29") is True

    def test_double_url_encoded_eval_detected(self):
        from app.main import _contains_dangerous_pattern
        assert _contains_dangerous_pattern("eval%2528x%2529") is True

    def test_benign_word_not_flagged(self):
        from app.main import _contains_dangerous_pattern
        assert _contains_dangerous_pattern("please evaluate this proposal") is False

    def test_normalize_is_bounded(self):
        # A pathological nested-encoding input must terminate (bounded passes).
        from app.main import _normalize_for_scanning
        s = "%25" * 50
        out = _normalize_for_scanning(s)  # must return, not hang
        assert isinstance(out, str)


# ── Security headers ─────────────────────────────────────────────────────────

class TestSecurityHeaders:
    @pytest.mark.anyio
    async def test_always_on_headers_present(self):
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("referrer-policy") == "no-referrer"

    @pytest.mark.anyio
    async def test_hsts_absent_when_not_enabled(self):
        # Default (ENABLE_HSTS unset) must NOT emit HSTS on a plain-http origin.
        from app.main import app, _HSTS_ENABLED
        if _HSTS_ENABLED:
            pytest.skip("ENABLE_HSTS is on in this environment")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
        assert "strict-transport-security" not in {k.lower() for k in resp.headers}


# ── Report store ─────────────────────────────────────────────────────────────

class TestReportStore:
    def test_save_list_get_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SHIPMATE_REPORTS_DB", str(tmp_path / "reports.db"))
        # Fresh thread-local connection for the new path.
        from app.services import report_store as rs
        rs._local.__dict__.clear()

        class _Repo:
            owner, name, branch = "acme", "widget", "main"

        class _Report:
            repo = _Repo()
            readiness_score = 82

            class _Rec:
                value = "ready"
            ship_recommendation = _Rec()

            def model_dump_json(self):
                return '{"readiness_score": 82, "repo": {"owner": "acme"}}'

        rid = rs.save_report(_Report())
        assert rid > 0

        rows = rs.list_reports("acme", "widget")
        assert len(rows) == 1
        assert rows[0]["readiness_score"] == 82
        assert rows[0]["ship_recommendation"] == "ready"

        full = rs.get_report(rid)
        assert full is not None
        assert full["readiness_score"] == 82

        # Unknown repo -> empty, unknown id -> None
        assert rs.list_reports("nobody", "nope") == []
        assert rs.get_report(999999) is None
