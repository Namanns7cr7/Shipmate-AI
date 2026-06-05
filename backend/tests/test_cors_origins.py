import os
import pytest
from unittest.mock import patch


def test_allowed_origins_parsed_from_env_excludes_empty_strings():
    """
    Test that ALLOWED_ORIGINS parsing filters out empty strings.
    
    This test verifies that when ALLOWED_ORIGINS env var contains trailing/leading
    commas or multiple consecutive commas (e.g., ',http://localhost:5173,,'),
    the resulting list contains no empty strings. This is critical because an
    empty string origin would be treated as a wildcard by CORSMiddleware,
    silently breaking the security model that explicitly forbids '*'.
    """
    # Simulate a misconfigured env var with leading comma, trailing comma, and double commas
    malformed_origins = ",http://localhost:5173,,http://localhost:3000,"
    
    with patch.dict(os.environ, {"ALLOWED_ORIGINS": malformed_origins}):
        # Re-import to pick up the patched env var
        import importlib
        import app.main
        importlib.reload(app.main)
        
        # Verify no empty strings in the parsed list
        assert "" not in app.main.ALLOWED_ORIGINS
        # Verify valid origins are preserved
        assert "http://localhost:5173" in app.main.ALLOWED_ORIGINS
        assert "http://localhost:3000" in app.main.ALLOWED_ORIGINS
        # Verify the list has exactly 2 entries (no empty strings)
        assert len(app.main.ALLOWED_ORIGINS) == 2
