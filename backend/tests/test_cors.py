"""Integration tests for CORS policy.

Ensures that:
- A request from an unlisted origin does NOT receive CORS headers.
- A request from an allowed origin DOES receive the correct CORS header.
"""
import os
import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def allowed_origin():
    return "http://localhost:5173"


@pytest.fixture()
def unlisted_origin():
    return "https://evil.example.com"


@pytest.fixture()
def client(allowed_origin, monkeypatch):
    """Create a TestClient with a controlled ALLOWED_ORIGINS env var."""
    monkeypatch.setenv("ALLOWED_ORIGINS", allowed_origin)

    # Force re-import of app.main so the middleware picks up the patched env.
    for mod_name in list(sys.modules.keys()):
        if mod_name == "app.main" or mod_name.startswith("app.main."):
            del sys.modules[mod_name]

    from app.main import app  # noqa: PLC0415

    return TestClient(app, raise_server_exceptions=True)


class TestCORSUnlistedOrigin:
    """Requests from origins not in the allowlist must not receive CORS headers."""

    def test_preflight_unlisted_origin_no_acao_header(
        self, client: TestClient, unlisted_origin: str
    ):
        response = client.options(
            "/health",
            headers={
                "Origin": unlisted_origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in response.headers, (
            f"Unlisted origin '{unlisted_origin}' should not receive "
            "Access-Control-Allow-Origin header."
        )

    def test_simple_request_unlisted_origin_no_acao_header(
        self, client: TestClient, unlisted_origin: str
    ):
        response = client.get("/health", headers={"Origin": unlisted_origin})
        assert "access-control-allow-origin" not in response.headers, (
            f"Unlisted origin '{unlisted_origin}' should not receive "
            "Access-Control-Allow-Origin header."
        )


class TestCORSAllowedOrigin:
    """Requests from origins in the allowlist must receive the correct CORS header."""

    def test_preflight_allowed_origin_returns_acao_header(
        self, client: TestClient, allowed_origin: str
    ):
        response = client.options(
            "/health",
            headers={
                "Origin": allowed_origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        acao = response.headers.get("access-control-allow-origin", "")
        assert acao == allowed_origin, (
            f"Expected Access-Control-Allow-Origin: {allowed_origin}, got: {acao!r}"
        )

    def test_simple_request_allowed_origin_returns_acao_header(
        self, client: TestClient, allowed_origin: str
    ):
        response = client.get("/health", headers={"Origin": allowed_origin})
        acao = response.headers.get("access-control-allow-origin", "")
        assert acao == allowed_origin, (
            f"Expected Access-Control-Allow-Origin: {allowed_origin}, got: {acao!r}"
        )
