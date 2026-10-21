"""
Unit tests for the Health check endpoint.
"""
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_health_check_healthy():
    """Verify health endpoint when database is connected."""
    with patch("backend.app.check_db_connection", return_value=(True, "connected")):
        response = client.get("/api/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["status"] == "ok"
        assert payload["data"]["database"] == "connected"
        assert "scheduler" in payload["data"]


def test_health_check_degraded():
    """Verify health endpoint when database connection fails."""
    with patch("backend.app.check_db_connection", return_value=(False, "Connection refused")):
        response = client.get("/api/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is False
        assert payload["data"]["status"] == "degraded"
        assert "Connection refused" in payload["data"]["database"]
        assert payload["error"] is not None
