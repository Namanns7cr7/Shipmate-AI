"""Integration tests for strict CORS origin validation (SEC-004).

These tests import the real `app` object from app.main and use
httpx.AsyncClient / starlette.testclient to exercise the actual middleware
stack — no hand-rolled FastAPI apps.
"""
import pytest
from starlette.testclient import TestClient

from app.main import app, _is_origin_allowed


# ---------------------------------------------------------------------------
# Unit tests for the exact-match helper
# ---------------------------------------------------------------------------

class TestIsOriginAllowed:
    def test_exact_allowed_origin_is_accepted(self):
        assert _is_origin_allowed("http://localhost:5173") is True

    def test_spoofed_prefix_origin_is_rejected(self):
        """http://localhost:5173.evil.com must NOT be treated as allowed."""
        assert _is_origin_allowed("http://localhost:5173.evil.com") is False

    def test_subdomain_of_allowed_origin_is_rejected(self):
        assert _is_origin_allowed("http://evil.localhost:5173") is False

    def test_allowed_origin_with_trailing_slash_is_rejected(self):
        """Trailing slash changes the origin string — must not match."""
        assert _is_origin_allowed("http://localhost:5173/") is False

    def test_empty_string_is_rejected(self):
        assert _is_origin_allowed("") is False

    def test_wildcard_string_is_rejected(self):
        assert _is_origin_allowed("*") is False


# ---------------------------------------------------------------------------
# Integration tests against the real ASGI app
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


class TestCORSMiddlewareIntegration:
    def test_spoofed_origin_not_reflected_in_response(self, client):
        """Access-Control-Allow-Origin must NOT be set to the spoofed origin."""
        spoofed = "http://localhost:5173.evil.com"
        response = client.get("/health", headers={"Origin": spoofed})
        acao = response.headers.get("access-control-allow-origin", "")
        assert acao != spoofed

    def test_spoofed_origin_not_reflected_as_wildcard(self, client):
        """The response must not fall back to a wildcard when origin is spoofed."""
        spoofed = "http://localhost:5173.evil.com"
        response = client.get("/health", headers={"Origin": spoofed})
        acao = response.headers.get("access-control-allow-origin", "")
        assert acao != "*"

    def test_legitimate_origin_is_reflected(self, client):
        """A valid allowlisted origin must be echoed back."""
        valid = "http://localhost:5173"
        response = client.get("/health", headers={"Origin": valid})
        assert response.headers.get("access-control-allow-origin") == valid

    def test_spoofed_preflight_returns_4xx(self, client):
        """OPTIONS preflight from a spoofed origin must be rejected (Starlette returns 400)."""
        spoofed = "http://localhost:5173.evil.com"
        response = client.options(
            "/health",
            headers={
                "Origin": spoofed,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (400, 403)

    def test_legitimate_preflight_is_not_403(self, client):
        """OPTIONS preflight from a valid origin must not be rejected."""
        valid = "http://localhost:5173"
        response = client.options(
            "/health",
            headers={
                "Origin": valid,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code != 403
