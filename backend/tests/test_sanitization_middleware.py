import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_sanitization_middleware_blocks_eval_in_body():
    """Test that POST requests with 'eval(' in JSON body are rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"prompt": "eval(malicious_code)"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_sanitization_middleware_blocks_exec_in_body():
    """Test that POST requests with 'exec(' in JSON body are rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"prompt": "exec(malicious_code)"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_sanitization_middleware_blocks_import_in_body():
    """Test that POST requests with '__import__' in JSON body are rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"prompt": "__import__('os')"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_sanitization_middleware_allows_safe_body():
    """Test that POST requests with safe content in JSON body are not blocked by sanitization."""
    response = client.post(
        "/api/analysis/analyze",
        json={"prompt": "Please analyze this code for vulnerabilities"},
        headers={"Content-Type": "application/json"},
    )
    # Should not be 400 (sanitization rejection); may be other error codes depending on endpoint logic
    assert response.status_code != 400
