"""
Unit tests verifying all feature placeholder module endpoints.
"""
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_jobs_placeholder():
    response = client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["module"] == "jobs"
    assert data["status"] == "planned"


def test_finance_placeholder():
    response = client.get("/api/finance")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["module"] == "finance"
    assert data["status"] == "active"


def test_ocr_placeholder():
    response = client.get("/api/ocr")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["module"] == "ocr"
    assert data["status"] == "planned"


def test_math_logic_placeholder():
    response = client.get("/api/math-logic")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["module"] == "math_logic"
    assert data["status"] == "planned"


def test_reminders_placeholder():
    response = client.get("/api/reminders")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["module"] == "reminders"
    assert data["status"] == "planned"


def test_reminders_scheduler_status():
    response = client.get("/api/reminders/scheduler-status")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "running" in data
    assert "job_store" in data
