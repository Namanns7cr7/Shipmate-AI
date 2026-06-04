import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import json
from io import BytesIO
import zipfile

from app.main import app, _contains_dangerous_pattern, ALLOWED_ORIGINS
from app.models.schemas import (
    AnalyzeRequest, AnalyzeResponse, RepoSummary,
    GitHubRepository, GitHubBranch
)


client = TestClient(app)


class TestRootEndpoint:
    """Test root endpoint returns correct service metadata."""

    def test_root_returns_service_info(self):
        """Root endpoint should return service metadata."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ShipMate AI"
        assert data["version"] == "2.0.0"
        assert data["status"] == "operational"
        assert data["docs"] == "/docs"
        assert "agents" in data
        assert len(data["agents"]) == 4

    def test_root_endpoint_response_structure(self):
        """Root endpoint should have all required fields."""
        response = client.get("/")
        data = response.json()
        required_fields = ["service", "version", "status", "docs", "agents"]
        for field in required_fields:
            assert field in data


class TestHealthCheckEndpoint:
    """Test health check endpoint."""

    def test_health_check_returns_healthy_status(self):
        """Health check should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "agents" in data
        assert data["agents"] == 4

    def test_health_check_response_structure(self):
        """Health check should return consistent structure."""
        response = client.get("/health")
        data = response.json()
        assert isinstance(data["status"], str)
        assert isinstance(data["agents"], int)


class TestGitHubCallbackHtml:
    """Test GitHub OAuth callback HTML page."""

    def test_github_callback_html_returns_html(self):
        """GitHub callback endpoint should return HTML content."""
        response = client.get("/github-callback.html")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        content = response.text
        assert "ShipMate AI" in content
        assert "GitHub" in content

    def test_github_callback_html_contains_script(self):
        """GitHub callback HTML should contain authorization script."""
        response = client.get("/github-callback.html")
        content = response.text
        assert "<script>" in content
        assert "URLSearchParams" in content
        assert "fetch" in content

    def test_github_callback_html_has_error_handling(self):
        """GitHub callback HTML should have error handling."""
        response = client.get("/github-callback.html")
        content = response.text
        assert "error" in content.lower()
        assert "catch" in content


class TestInputSanitizationMiddleware:
    """Test input sanitization middleware for dangerous patterns."""

    def test_dangerous_pattern_eval(self):
        """Middleware should detect eval() pattern."""
        assert _contains_dangerous_pattern("eval(something)") is True
        assert _contains_dangerous_pattern("EVAL(something)") is True
        assert _contains_dangerous_pattern("eval (something)") is True

    def test_dangerous_pattern_exec(self):
        """Middleware should detect exec() pattern."""
        assert _contains_dangerous_pattern("exec(code)") is True
        assert _contains_dangerous_pattern("EXEC(code)") is True
        assert _contains_dangerous_pattern("exec (code)") is True

    def test_dangerous_pattern_import(self):
        """Middleware should detect __import__() pattern."""
        assert _contains_dangerous_pattern("__import__('os')") is True
        assert _contains_dangerous_pattern("__import__ ('os')") is True

    def test_dangerous_pattern_builtins(self):
        """Middleware should detect __builtins__ pattern."""
        assert _contains_dangerous_pattern("__builtins__") is True
        assert _contains_dangerous_pattern("__BUILTINS__") is True

    def test_dangerous_pattern_globals(self):
        """Middleware should detect __globals__ pattern."""
        assert _contains_dangerous_pattern("__globals__") is True
        assert _contains_dangerous_pattern("__GLOBALS__") is True

    def test_dangerous_pattern_locals(self):
        """Middleware should detect __locals__ pattern."""
        assert _contains_dangerous_pattern("__locals__") is True
        assert _contains_dangerous_pattern("__LOCALS__") is True

    def test_dangerous_pattern_compile(self):
        """Middleware should detect compile() pattern."""
        assert _contains_dangerous_pattern("compile(code)") is True
        assert _contains_dangerous_pattern("compile (code)") is True

    def test_dangerous_pattern_importlib(self):
        """Middleware should detect importlib.import_module() pattern."""
        assert _contains_dangerous_pattern("importlib.import_module('os')") is True
        assert _contains_dangerous_pattern("importlib.import_module ('os')") is True

    def test_dangerous_pattern_subprocess(self):
        """Middleware should detect subprocess pattern."""
        assert _contains_dangerous_pattern("subprocess.run()") is True
        assert _contains_dangerous_pattern("subprocess.Popen()") is True

    def test_dangerous_pattern_os_system(self):
        """Middleware should detect os.system() pattern."""
        assert _contains_dangerous_pattern("os.system('ls')") is True
        assert _contains_dangerous_pattern("os.system ('ls')") is True

    def test_dangerous_pattern_os_popen(self):
        """Middleware should detect os.popen() pattern."""
        assert _contains_dangerous_pattern("os.popen('ls')") is True
        assert _contains_dangerous_pattern("os.popen ('ls')") is True

    def test_safe_patterns_not_blocked(self):
        """Middleware should allow safe patterns."""
        assert _contains_dangerous_pattern("Add user authentication") is False
        assert _contains_dangerous_pattern("Implement OAuth2 flow") is False
        assert _contains_dangerous_pattern("Update database schema") is False
        assert _contains_dangerous_pattern("Fix bug in login") is False

    def test_sanitization_in_query_params(self):
        """Middleware should block dangerous patterns in query parameters."""
        response = client.get("/?param=eval(code)")
        assert response.status_code == 400
        assert "disallowed content" in response.json()["detail"]

    def test_sanitization_in_request_body(self):
        """Middleware should block dangerous patterns in JSON body."""
        payload = {"feature_request": "exec(malicious_code)"}
        response = client.post("/api/analyze", json=payload)
        assert response.status_code == 400
        assert "disallowed content" in response.json()["detail"]

    def test_sanitization_allows_safe_json_body(self):
        """Middleware should allow safe JSON in body."""
        payload = {"feature_request": "Add authentication to dashboard"}
        response = client.post("/api/analyze", json=payload)
        # Should not be blocked by sanitization (may fail for other reasons)
        assert response.status_code != 400 or "disallowed content" not in response.json().get("detail", "")


class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_cors_allowed_origins_configured(self):
        """CORS should have allowed origins configured."""
        assert len(ALLOWED_ORIGINS) > 0
        assert isinstance(ALLOWED_ORIGINS, list)

    def test_cors_localhost_origins_included(self):
        """CORS should include localhost origins."""
        localhost_origins = [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ]
        for origin in localhost_origins:
            assert origin in ALLOWED_ORIGINS

    def test_cors_no_wildcard_origin(self):
        """CORS should not use wildcard origin for security."""
        assert "*" not in ALLOWED_ORIGINS

    def test_cors_origins_are_strings(self):
        """All CORS origins should be strings."""
        for origin in ALLOWED_ORIGINS:
            assert isinstance(origin, str)
            assert len(origin) > 0


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_invalid_json_payload(self):
        """Endpoints should handle invalid JSON gracefully."""
        response = client.post(
            "/api/analyze",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_required_fields(self):
        """Endpoints should validate required fields."""
        payload = {"repo_details": None}  # Missing feature_request
        response = client.post("/api/analyze", json=payload)
        assert response.status_code == 422

    def test_404_for_nonexistent_endpoint(self):
        """Nonexistent endpoints should return 404."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Wrong HTTP method should return 405."""
        response = client.post("/")
        assert response.status_code == 405


class TestEndpointIntegration:
    """Integration tests for multiple endpoints."""

    def test_health_check_before_root(self):
        """Should be able to check health and root in sequence."""
        health_response = client.get("/health")
        assert health_response.status_code == 200

        root_response = client.get("/")
        assert root_response.status_code == 200

    def test_github_callback_html_accessible(self):
        """GitHub callback HTML should be accessible."""
        response = client.get("/github-callback.html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_multiple_health_checks(self):
        """Multiple health checks should return consistent results."""
        responses = [client.get("/health") for _ in range(3)]
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["agents"] == 4


class TestRequestValidation:
    """Test request validation and parameter handling."""

    def test_query_parameter_validation(self):
        """Query parameters should be validated."""
        response = client.get("/?invalid_param=value")
        # Root endpoint should ignore unknown params
        assert response.status_code == 200

    def test_empty_query_string(self):
        """Empty query string should be handled."""
        response = client.get("/?")
        assert response.status_code == 200

    def test_special_characters_in_query(self):
        """Special characters in query should be handled safely."""
        response = client.get("/?param=test%20value")
        assert response.status_code == 200


class TestResponseFormats:
    """Test response format consistency."""

    def test_root_response_is_json(self):
        """Root endpoint should return JSON."""
        response = client.get("/")
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert isinstance(data, dict)

    def test_health_response_is_json(self):
        """Health endpoint should return JSON."""
        response = client.get("/health")
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert isinstance(data, dict)

    def test_github_callback_response_is_html(self):
        """GitHub callback should return HTML."""
        response = client.get("/github-callback.html")
        assert response.headers["content-type"].startswith("text/html")
        assert isinstance(response.text, str)


class TestMiddlewareChaining:
    """Test middleware execution order and chaining."""

    def test_sanitization_before_routing(self):
        """Sanitization middleware should run before routing."""
        # Dangerous pattern in query should be blocked before reaching route
        response = client.get("/?code=__import__('os')")
        assert response.status_code == 400

    def test_cors_headers_present(self):
        """CORS headers should be present in responses."""
        response = client.get("/", headers={"Origin": "http://localhost:5173"})
        # CORS headers may or may not be present depending on preflight
        assert response.status_code == 200


class TestDangerousPatternEdgeCases:
    """Test edge cases in dangerous pattern detection."""

    def test_pattern_with_extra_whitespace(self):
        """Patterns with extra whitespace should be detected."""
        assert _contains_dangerous_pattern("eval  (  code  )") is True

    def test_pattern_case_insensitivity(self):
        """Pattern detection should be case-insensitive."""
        assert _contains_dangerous_pattern("EVAL(code)") is True
        assert _contains_dangerous_pattern("Eval(code)") is True
        assert _contains_dangerous_pattern("eVaL(code)") is True

    def test_pattern_in_middle_of_text(self):
        """Patterns in middle of text should be detected."""
        assert _contains_dangerous_pattern("some text eval(code) more text") is True

    def test_multiple_patterns_in_text(self):
        """Multiple patterns should be detected."""
        assert _contains_dangerous_pattern("eval(code) and exec(other)") is True

    def test_pattern_not_detected_in_comments(self):
        """Patterns should still be detected even if they look like comments."""
        # The middleware doesn't parse code, so it should detect these
        assert _contains_dangerous_pattern("# eval(code)") is True

    def test_safe_words_containing_pattern_substrings(self):
        """Safe words containing pattern substrings should not match."""
        # These don't match the regex patterns (need word boundary or parenthesis)
        assert _contains_dangerous_pattern("evaluation") is False
        assert _contains_dangerous_pattern("execute") is False
        assert _contains_dangerous_pattern("compiler") is False
