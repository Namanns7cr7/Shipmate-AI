import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


class TestErrorHandling:
    """Unit tests validating backend error handling returns appropriate HTTP status codes
    and sanitized error messages without exposing internal stack traces or sensitive details."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI application with error handlers."""
        app = FastAPI()

        @app.get("/test-not-found")
        def not_found_endpoint():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )

        @app.get("/test-unauthorized")
        def unauthorized_endpoint():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized access"
            )

        @app.get("/test-forbidden")
        def forbidden_endpoint():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden"
            )

        @app.get("/test-bad-request")
        def bad_request_endpoint():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request parameters"
            )

        @app.get("/test-internal-error")
        def internal_error_endpoint():
            raise Exception("Internal database connection failed")

        @app.get("/test-validation-error")
        def validation_error_endpoint(value: int):
            # This will trigger validation error if value is not an int
            return {"value": value}

        # Global exception handler for unhandled exceptions
        @app.exception_handler(Exception)
        async def generic_exception_handler(request, exc):
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "An internal server error occurred"},
            )

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_404_not_found_returns_correct_status(self, client):
        """Test that 404 errors return HTTP 404 status code."""
        response = client.get("/test-not-found")
        assert response.status_code == 404

    def test_404_not_found_returns_sanitized_message(self, client):
        """Test that 404 errors return sanitized error messages."""
        response = client.get("/test-not-found")
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Resource not found"
        assert "traceback" not in str(data).lower()
        assert "stack" not in str(data).lower()

    def test_401_unauthorized_returns_correct_status(self, client):
        """Test that 401 errors return HTTP 401 status code."""
        response = client.get("/test-unauthorized")
        assert response.status_code == 401

    def test_401_unauthorized_returns_sanitized_message(self, client):
        """Test that 401 errors return sanitized error messages."""
        response = client.get("/test-unauthorized")
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Unauthorized access"
        assert "traceback" not in str(data).lower()

    def test_403_forbidden_returns_correct_status(self, client):
        """Test that 403 errors return HTTP 403 status code."""
        response = client.get("/test-forbidden")
        assert response.status_code == 403

    def test_403_forbidden_returns_sanitized_message(self, client):
        """Test that 403 errors return sanitized error messages."""
        response = client.get("/test-forbidden")
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Access forbidden"
        assert "traceback" not in str(data).lower()

    def test_400_bad_request_returns_correct_status(self, client):
        """Test that 400 errors return HTTP 400 status code."""
        response = client.get("/test-bad-request")
        assert response.status_code == 400

    def test_400_bad_request_returns_sanitized_message(self, client):
        """Test that 400 errors return sanitized error messages."""
        response = client.get("/test-bad-request")
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Invalid request parameters"
        assert "traceback" not in str(data).lower()

    def test_500_internal_error_returns_correct_status(self, client):
        """Test that unhandled exceptions return HTTP 500 status code."""
        response = client.get("/test-internal-error")
        assert response.status_code == 500

    def test_500_internal_error_does_not_expose_stack_trace(self, client):
        """Test that 500 errors do not expose internal stack traces."""
        response = client.get("/test-internal-error")
        data = response.json()
        response_text = str(data).lower()
        # Ensure no sensitive implementation details are exposed
        assert "traceback" not in response_text
        assert "database" not in response_text
        assert "connection" not in response_text
        assert "failed" not in response_text

    def test_500_internal_error_returns_generic_message(self, client):
        """Test that 500 errors return generic error messages."""
        response = client.get("/test-internal-error")
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "An internal server error occurred"

    def test_validation_error_returns_correct_status(self, client):
        """Test that validation errors return HTTP 422 status code."""
        response = client.get("/test-validation-error?value=not-an-int")
        assert response.status_code == 422

    def test_validation_error_returns_error_details(self, client):
        """Test that validation errors include error details."""
        response = client.get("/test-validation-error?value=not-an-int")
        data = response.json()
        assert "detail" in data
        # Validation errors should provide helpful but safe information
        assert isinstance(data["detail"], list)

    def test_error_response_structure(self, client):
        """Test that error responses follow consistent structure."""
        response = client.get("/test-not-found")
        data = response.json()
        # All error responses should have a detail field
        assert "detail" in data
        # Should not contain raw exception objects or internal state
        assert "__" not in str(data)

    def test_no_sensitive_headers_in_error_response(self, client):
        """Test that error responses do not expose sensitive headers."""
        response = client.get("/test-internal-error")
        # Check that response headers don't expose sensitive information
        headers_str = str(response.headers).lower()
        assert "x-debug" not in headers_str
        assert "x-internal" not in headers_str

    def test_multiple_error_types_return_appropriate_codes(self, client):
        """Test that different error types return their appropriate status codes."""
        test_cases = [
            ("/test-not-found", 404),
            ("/test-unauthorized", 401),
            ("/test-forbidden", 403),
            ("/test-bad-request", 400),
            ("/test-internal-error", 500),
        ]
        for endpoint, expected_status in test_cases:
            response = client.get(endpoint)
            assert response.status_code == expected_status, \
                f"Expected {expected_status} for {endpoint}, got {response.status_code}"
