import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_sanitization_blocks_eval_in_json_body():
    """Test that POST with 'eval(' in JSON body is rejected with 400."""
    response = client.post(
        "/health",
        json={"code": "eval(malicious_code)"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Request contains disallowed content"


def test_sanitization_blocks_exec_in_json_body():
    """Test that POST with 'exec(' in JSON body is rejected with 400."""
    response = client.post(
        "/health",
        json={"payload": "exec(something)"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Request contains disallowed content"


def test_sanitization_blocks_import_in_json_body():
    """Test that POST with '__import__' in JSON body is rejected with 400."""
    response = client.post(
        "/health",
        json={"data": "__import__('os')"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Request contains disallowed content"


def test_sanitization_blocks_subprocess_in_json_body():
    """Test that POST with 'subprocess' in JSON body is rejected with 400."""
    response = client.post(
        "/health",
        json={"cmd": "subprocess.call(['ls'])"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Request contains disallowed content"


def test_sanitization_blocks_nested_dangerous_pattern():
    """Test that dangerous patterns in nested JSON objects are detected."""
    response = client.post(
        "/health",
        json={
            "user": {
                "name": "Alice",
                "config": {
                    "script": "eval(x)"
                }
            }
        },
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Request contains disallowed content"


def test_sanitization_blocks_dangerous_pattern_in_array():
    """Test that dangerous patterns in JSON arrays are detected."""
    response = client.post(
        "/health",
        json={
            "items": ["safe", "eval(bad)", "also_safe"]
        },
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Request contains disallowed content"


def test_sanitization_allows_safe_json_body():
    """Test that POST with safe JSON body is allowed."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
