import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_post_body_with_eval_injection_blocked():
    """Test that POST body containing eval() is rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"prompt": "eval(os.system('rm -rf /'))"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_post_body_with_exec_injection_blocked():
    """Test that POST body containing exec() is rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"prompt": "exec('malicious code')"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_post_body_with_import_injection_blocked():
    """Test that POST body containing __import__ is rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"prompt": "__import__('subprocess').call('id')"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_post_body_with_nested_eval_injection_blocked():
    """Test that POST body with eval() in nested JSON object is rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={
            "prompt": "normal text",
            "metadata": {
                "nested": "eval(dangerous_code())"
            }
        },
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_post_body_with_subprocess_injection_blocked():
    """Test that POST body containing subprocess is rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"prompt": "import subprocess; subprocess.run(['ls'])"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_post_body_with_os_system_injection_blocked():
    """Test that POST body containing os.system is rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"prompt": "os.system('whoami')"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_post_body_with_clean_content_allowed():
    """Test that POST body with clean content is not blocked by sanitization."""
    response = client.post(
        "/api/analysis/analyze",
        json={"prompt": "Please analyze this code for security issues"},
        headers={"Content-Type": "application/json"},
    )
    # Should not be 400 (sanitization should pass)
    # The actual endpoint may return 401/403 if auth is required, but not 400 from sanitization
    assert response.status_code != 400
