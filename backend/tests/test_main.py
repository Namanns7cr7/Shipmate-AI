import logging
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app, _get_client_ip

client = TestClient(app)


def test_get_client_ip_config_disabled():
    with patch("app.main._get_config_value", return_value=False):
        ip = _get_client_ip({"REMOTE_ADDR": "192.168.1.1"})
        assert ip == "192.168.1.1"


def test_get_client_ip_config_enabled_single_ip():
    with patch("app.main._get_config_value", return_value=True):
        ip = _get_client_ip({"X-Forwarded-For": "203.0.113.5", "REMOTE_ADDR": "192.168.1.1"})
        assert ip == "203.0.113.5"


def test_get_client_ip_config_enabled_multiple_ips():
    with patch("app.main._get_config_value", return_value=True):
        ip = _get_client_ip({"X-Forwarded-For": "203.0.113.5, 70.41.3.18, 150.172.238.178", "REMOTE_ADDR": "192.168.1.1"})
        assert ip == "203.0.113.5"


def test_get_client_ip_config_enabled_no_x_forwarded_for():
    with patch("app.main._get_config_value", return_value=True):
        ip = _get_client_ip({"REMOTE_ADDR": "192.168.1.1"})
        assert ip == "192.168.1.1"


def test_get_client_ip_logging(caplog):
    with patch("app.main._get_config_value", return_value=True):
        with caplog.at_level(logging.INFO):
            ip = _get_client_ip({"X-Forwarded-For": "203.0.113.5", "REMOTE_ADDR": "192.168.1.1"})
            assert ip == "203.0.113.5"
            assert any("Client IP" in record.message for record in caplog.records)
