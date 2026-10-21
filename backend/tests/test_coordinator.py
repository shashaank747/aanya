"""
Unit tests for the Coordinator routing boundary.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.core.coordinator import coordinator, IntentType, AssistantRequest

client = TestClient(app)


def test_coordinator_classification():
    """Verify intent heuristic classification rules."""
    assert coordinator.classify_intent("I want to track a job application at Apple") == IntentType.JOBS
    assert coordinator.classify_intent("Log an expense of $45 for lunch") == IntentType.FINANCE
    assert coordinator.classify_intent("Scan this receipt image with OCR") == IntentType.OCR
    assert coordinator.classify_intent("Calculate monthly compound interest") == IntentType.MATH_LOGIC
    assert coordinator.classify_intent("Remind me to call the doctor tomorrow") == IntentType.REMINDERS
    assert coordinator.classify_intent("What is the capital of France?") == IntentType.GENERAL
    assert coordinator.classify_intent("") == IntentType.UNKNOWN


def test_coordinator_route_method():
    """Verify route method returns valid RoutingDecision."""
    decision = coordinator.route(AssistantRequest(text="Check my resume"))
    assert decision.intent == IntentType.JOBS
    assert decision.target_module == "backend.modules.jobs"
    assert decision.confidence > 0.0


def test_coordinator_route_api_endpoint():
    """Verify POST /api/coordinator/route endpoint."""
    response = client.post(
        "/api/coordinator/route",
        json={"text": "Remind me at 5 PM", "context": {}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["intent"] == "reminders"
    assert payload["data"]["target_module"] == "backend.modules.reminders"
