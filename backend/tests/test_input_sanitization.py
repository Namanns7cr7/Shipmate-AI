import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestInputSanitizationMiddleware:
    """Integration tests for input sanitization middleware."""

    def test_valid_json_body_passes_through(self):
        """POST with valid JSON body should be received intact by the route handler."""
        # Create a test endpoint that echoes back the received JSON
        @app.post("/test/echo")
        async def echo_handler(request: Request):
            body = await request.json()
            return {"received": body}
        
        payload = {"name": "test", "value": 42}
        response = client.post("/test/echo", json=payload)
        
        assert response.status_code == 200
        assert response.json() == {"received": payload}

    def test_dangerous_pattern_eval_blocked(self):
        """POST with eval( in JSON body should return 400."""
        payload = {"code": "eval(some_function)"}
        response = client.post("/test/echo", json=payload)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Request contains disallowed content"

    def test_dangerous_pattern_exec_blocked(self):
        """POST with exec( in JSON body should return 400."""
        payload = {"code": "exec(malicious_code)"}
        response = client.post("/test/echo", json=payload)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Request contains disallowed content"

    def test_dangerous_pattern_import_blocked(self):
        """POST with __import__ in JSON body should return 400."""
        payload = {"code": "__import__('os').system('rm -rf /')"}
        response = client.post("/test/echo", json=payload)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Request contains disallowed content"

    def test_dangerous_pattern_subprocess_blocked(self):
        """POST with subprocess in JSON body should return 400."""
        payload = {"cmd": "subprocess.run(['ls'])"}
        response = client.post("/test/echo", json=payload)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Request contains disallowed content"

    def test_dangerous_pattern_os_system_blocked(self):
        """POST with os.system in JSON body should return 400."""
        payload = {"cmd": "os.system('whoami')"}
        response = client.post("/test/echo", json=payload)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Request contains disallowed content"

    def test_dangerous_pattern_in_nested_json_blocked(self):
        """POST with dangerous pattern in nested JSON should return 400."""
        payload = {"user": {"name": "alice", "script": "eval(x)"}}
        response = client.post("/test/echo", json=payload)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Request contains disallowed content"

    def test_dangerous_pattern_in_json_list_blocked(self):
        """POST with dangerous pattern in JSON list should return 400."""
        payload = {"items": ["safe", "eval(bad)", "also_safe"]}
        response = client.post("/test/echo", json=payload)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Request contains disallowed content"

    def test_dangerous_pattern_case_insensitive(self):
        """Dangerous patterns should be detected case-insensitively."""
        payload = {"code": "EVAL(something)"}
        response = client.post("/test/echo", json=payload)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Request contains disallowed content"

    def test_query_parameter_with_dangerous_pattern_blocked(self):
        """GET with dangerous pattern in query param should return 400."""
        response = client.get("/test/echo?code=eval(x)")
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Request contains disallowed content"

    def test_header_with_dangerous_pattern_blocked(self):
        """Request with dangerous pattern in custom header should return 400."""
        response = client.get("/test/echo", headers={"X-Custom": "eval(x)"})
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Request contains disallowed content"

    def test_authorization_header_not_scanned(self):
        """Authorization header should not be scanned for dangerous patterns."""
        # This should pass through without being blocked by the middleware
        response = client.get(
            "/test/echo",
            headers={"Authorization": "Bearer eval(something)"}
        )
        # The endpoint itself may return 404 or 405, but not 400 from middleware
        assert response.status_code != 400

    def test_cookie_header_not_scanned(self):
        """Cookie header should not be scanned for dangerous patterns."""
        response = client.get(
            "/test/echo",
            headers={"Cookie": "session=eval(x)"}
        )
        # The endpoint itself may return 404 or 405, but not 400 from middleware
        assert response.status_code != 400

    def test_empty_body_allowed(self):
        """POST with empty body should be allowed."""
        response = client.post("/test/echo", json={})
        
        assert response.status_code == 200
        assert response.json() == {"received": {}}

    def test_large_valid_json_body_passes(self):
        """POST with large valid JSON body should pass through intact."""
        large_payload = {"data": "x" * 10000, "count": 100}
        response = client.post("/test/echo", json=large_payload)
        
        assert response.status_code == 200
        assert response.json() == {"received": large_payload}
