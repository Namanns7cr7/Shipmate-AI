"""Tests for sanitize_input_middleware in app.main.

Each test imports the real FastAPI `app` object and uses the ASGI test client
so the middleware stack is exercised end-to-end.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.anyio
async def test_clean_get_request_passes():
    """A normal GET request with no dangerous content must reach the handler."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_dangerous_query_param_blocked():
    """A query parameter containing eval( must be rejected with 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health", params={"q": "eval(malicious()"})
    assert response.status_code == 400


@pytest.mark.anyio
async def test_dangerous_body_eval_blocked():
    """A JSON body containing eval( must be rejected with 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            json={"repo_url": "eval(os.system('id'))"},
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_dangerous_body_exec_blocked():
    """A JSON body containing exec( must be rejected with 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            json={"prompt": "exec(open('/etc/passwd').read())"},
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_dangerous_body_import_blocked():
    """A JSON body containing __import__ must be rejected with 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            json={"repo_url": "__import__('os').system('id')"},
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_clean_post_body_not_blocked():
    """A POST body with a legitimate repo URL must NOT be blocked by the middleware (may fail auth, not 400)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            json={"repo_url": "https://github.com/octocat/Hello-World", "branch": "main"},
            headers={"content-type": "application/json"},
        )
    # Middleware must NOT block this — downstream may return 401/422 but not 400 from sanitizer
    assert response.status_code != 400
