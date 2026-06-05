import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_sanitize_input_middleware_authorization_header_not_scanned():
    """
    Test that Authorization headers containing dangerous patterns are NOT rejected.
    This confirms the intentional exclusion of 'authorization' from header scanning
    does not accidentally block legitimate tokens that happen to contain patterns
    like 'eval('.
    """
    client = TestClient(app)
    
    # Bearer token that contains the string 'eval(' but is a valid token
    bearer_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eval(test).signature"
    
    response = client.get(
        "/health",
        headers={"Authorization": bearer_token}
    )
    
    # Should return 200 (not 400), confirming Authorization header was not scanned
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "agents": 4}
