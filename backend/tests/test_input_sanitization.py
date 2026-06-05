import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_post_body_with_eval_injection_blocked():
    """Test that POST body containing eval( is rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"repo_url": "https://github.com/test/repo", "prompt": "eval(malicious_code)"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_post_body_with_exec_injection_blocked():
    """Test that POST body containing exec( is rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"repo_url": "https://github.com/test/repo", "prompt": "exec(code)"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_post_body_with_import_injection_blocked():
    """Test that POST body containing __import__ is rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"repo_url": "https://github.com/test/repo", "prompt": "__import__('os')"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_post_body_with_subprocess_injection_blocked():
    """Test that POST body containing subprocess is rejected with 400."""
    response = client.post(
        "/api/analysis/analyze",
        json={"repo_url": "https://github.com/test/repo", "prompt": "subprocess.run(cmd)"},
    )
    assert response.status_code == 400
    assert "disallowed content" in response.json()["detail"].lower()


def test_post_body_clean_accepted():
    """Test that POST body without dangerous patterns is accepted (passes middleware)."""
    response = client.post(
        "/api/analysis/analyze",
        json={"repo_url": "https://github.com/test/repo", "prompt": "Analyze this code for bugs"},
    )
    # Should not be 400 (middleware passes it through; endpoint may return 401, 422, etc.)
    assert response.status_code != 400
