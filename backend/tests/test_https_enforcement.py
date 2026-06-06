"""Tests for the startup HTTPS endpoint-URL enforcement added in main.py."""
import os
import importlib
import pytest

from app.main import _validate_endpoint_urls, _LOCAL_HOSTS, _ENDPOINT_ENV_VARS


def test_https_url_is_accepted(monkeypatch):
    """An https:// endpoint URL must not raise."""
    monkeypatch.setenv("BEDROCK_ENDPOINT", "https://bedrock.us-east-1.amazonaws.com")
    # Should not raise
    _validate_endpoint_urls()


def test_http_non_local_url_raises(monkeypatch):
    """A plain http:// URL pointing to a non-local host must raise ValueError."""
    monkeypatch.setenv("BEDROCK_ENDPOINT", "http://bedrock.us-east-1.amazonaws.com")
    with pytest.raises(ValueError, match="plain HTTP URL"):
        _validate_endpoint_urls()


def test_http_localhost_is_exempt(monkeypatch):
    """http://localhost is a local address and must be accepted without error."""
    monkeypatch.setenv("API_BASE_URL", "http://localhost:8080")
    # Should not raise
    _validate_endpoint_urls()


def test_http_loopback_ip_is_exempt(monkeypatch):
    """http://127.0.0.1 is a loopback address and must be accepted without error."""
    monkeypatch.setenv("INTERNAL_API_URL", "http://127.0.0.1:9000/api")
    # Should not raise
    _validate_endpoint_urls()


def test_unset_env_var_is_skipped(monkeypatch):
    """An unset endpoint env var must not cause any error."""
    for var in _ENDPOINT_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    # Should not raise
    _validate_endpoint_urls()


def test_error_message_names_the_variable(monkeypatch):
    """The ValueError message must include the name of the offending env var."""
    monkeypatch.setenv("GITHUB_API_URL", "http://internal-github.corp.example.com")
    with pytest.raises(ValueError, match="GITHUB_API_URL"):
        _validate_endpoint_urls()
