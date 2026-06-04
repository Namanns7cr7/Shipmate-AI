import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_sanitize_input_middleware_passes_clean_request_unchanged():
    """
    Verifies that sanitize_input_middleware does NOT block a normal request
    whose headers, query params, and body contain no dangerous patterns,
    ensuring legitimate traffic is never rejected.
    
    This guards against over-blocking regressions where a pattern change in
    _DANGEROUS_PATTERNS accidentally matches benign content.
    """
    # Test with clean query parameters
    response = client.get(
        "/health",
        params={"user_id": "12345", "action": "analyze"},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "agents": 4}


def test_sanitize_input_middleware_blocks_dangerous_query_param():
    """
    Verifies that sanitize_input_middleware blocks requests with dangerous
    patterns in query parameters.
    """
    response = client.get(
        "/health",
        params={"code": "eval(malicious)"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_sanitize_input_middleware_blocks_dangerous_header():
    """
    Verifies that sanitize_input_middleware blocks requests with dangerous
    patterns in headers.
    """
    response = client.get(
        "/health",
        headers={"X-Custom-Header": "__import__(os)"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_sanitize_input_middleware_blocks_dangerous_body():
    """
    Verifies that sanitize_input_middleware blocks requests with dangerous
    patterns in the request body.
    """
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "exec(code)"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()
