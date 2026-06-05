"""Tests for CORS origin validation (SEC-004)."""
import pytest
from app.main import _validate_origin


def test_valid_https_origin_is_accepted():
    assert _validate_origin("https://app.shipmate.ai") == "https://app.shipmate.ai"


def test_valid_http_localhost_is_accepted():
    assert _validate_origin("http://localhost:5173") == "http://localhost:5173"


def test_valid_http_with_port_is_accepted():
    assert _validate_origin("http://127.0.0.1:3000") == "http://127.0.0.1:3000"


def test_bare_wildcard_is_rejected():
    with pytest.raises(ValueError, match="wildcard"):
        _validate_origin("*")


def test_wildcard_in_subdomain_is_rejected():
    with pytest.raises(ValueError, match="wildcard"):
        _validate_origin("https://*.shipmate.ai")


def test_ftp_scheme_is_rejected():
    with pytest.raises(ValueError, match="invalid scheme"):
        _validate_origin("ftp://shipmate.ai")


def test_no_scheme_is_rejected():
    with pytest.raises(ValueError):
        _validate_origin("shipmate.ai")


def test_empty_netloc_is_rejected():
    with pytest.raises(ValueError, match="empty host"):
        _validate_origin("https://")


def test_trailing_space_stripped_origin_is_valid():
    # Simulates what the list comprehension does: strip before calling validate
    origin = "  https://app.shipmate.ai  ".strip()
    assert _validate_origin(origin) == "https://app.shipmate.ai"
