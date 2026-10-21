"""
Coordinator Routing Boundary for Aanya.

Acts as the architectural gateway for incoming assistant requests.
In future iterations, this coordinator will incorporate intent classification
(via rule engine, embedding similarity, or LLM router) and dispatch requests
to the respective feature modules (jobs, finance, ocr, math_logic, reminders).

Notice: No autonomous agent loops or external LLM connections are implemented
in this initial foundation phase.
"""
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Categorized assistant intents corresponding to feature modules."""
    JOBS = "jobs"
    FINANCE = "finance"
    HEALTH = "health"
    OCR = "ocr"
    MATH_LOGIC = "math_logic"
    REMINDERS = "reminders"
    GENERAL = "general"
    UNKNOWN = "unknown"



class AssistantRequest(BaseModel):
    """Normalized payload representing an incoming user interaction."""
    text: str = Field(..., description="Raw text of the user query or command")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session or device context")


class RoutingDecision(BaseModel):
    """Routing resolution output by the coordinator."""
    intent: IntentType
    target_module: str
    confidence: float
    explanation: str


class Coordinator:
    """
    Coordinator interface that maps incoming user inputs to feature modules.
    Currently provides deterministic baseline matching and structural contracts.
    """

    # Keyword mappings for placeholder heuristic routing
    _KEYWORD_MAP = {
        "job": IntentType.JOBS,
        "application": IntentType.JOBS,
        "resume": IntentType.JOBS,
        "interview": IntentType.JOBS,
        "expense": IntentType.FINANCE,
        "spent": IntentType.FINANCE,
        "paid": IntentType.FINANCE,
        "received": IntentType.FINANCE,
        "salary": IntentType.FINANCE,
        "budget": IntentType.FINANCE,
        "money": IntentType.FINANCE,
        "rupee": IntentType.FINANCE,
        "₹": IntentType.FINANCE,
        "calorie": IntentType.HEALTH,
        "calories": IntentType.HEALTH,
        "kcal": IntentType.HEALTH,
        "nutrition": IntentType.HEALTH,
        "diet": IntentType.HEALTH,
        "meal": IntentType.HEALTH,
        "ate": IntentType.HEALTH,
        "breakfast": IntentType.HEALTH,
        "food": IntentType.HEALTH,
        "groceries": IntentType.FINANCE,
        "bill": IntentType.FINANCE,
        "scan": IntentType.OCR,
        "ocr": IntentType.OCR,
        "extract": IntentType.OCR,
        "document": IntentType.OCR,
        "calculate": IntentType.MATH_LOGIC,
        "math": IntentType.MATH_LOGIC,
        "sum": IntentType.MATH_LOGIC,
        "remind": IntentType.REMINDERS,
        "alarm": IntentType.REMINDERS,
        "timer": IntentType.REMINDERS,
    }

    def classify_intent(self, text: str) -> IntentType:
        """
        Lightweight heuristic classifier using word boundary regex.
        Will be replaced or augmented by an intent classification model in future phases.
        """
        import re
        lower_text = text.lower()
        for keyword, intent in self._KEYWORD_MAP.items():
            pattern = rf"\b{re.escape(keyword)}\b" if keyword.isalnum() else re.escape(keyword)
            if re.search(pattern, lower_text):
                return intent
        return IntentType.GENERAL if text.strip() else IntentType.UNKNOWN


    def route(self, request: AssistantRequest) -> RoutingDecision:
        """
        Determine which module should handle the assistant request.
        """
        intent = self.classify_intent(request.text)
        
        module_target_map = {
            IntentType.JOBS: "backend.modules.jobs",
            IntentType.FINANCE: "backend.modules.finance",
            IntentType.HEALTH: "backend.modules.health",
            IntentType.OCR: "backend.modules.ocr",
            IntentType.MATH_LOGIC: "backend.modules.math_logic",
            IntentType.REMINDERS: "backend.modules.reminders",
            IntentType.GENERAL: "backend.core.coordinator",
            IntentType.UNKNOWN: "backend.core.coordinator",
        }

        return RoutingDecision(
            intent=intent,
            target_module=module_target_map.get(intent, "backend.core.coordinator"),
            confidence=0.85 if intent not in (IntentType.GENERAL, IntentType.UNKNOWN) else 0.5,
            explanation=f"Heuristic pattern matched to {intent.value} capability module.",
        )


coordinator = Coordinator()
