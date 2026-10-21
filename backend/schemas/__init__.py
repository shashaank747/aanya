"""
Pydantic schemas and standard response contracts for Aanya.
"""
from typing import Generic, TypeVar, Optional, Any, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class StandardResponse(BaseModel, Generic[DataT]):
    """Standardized envelope for all API responses."""
    success: bool = Field(default=True, description="Indicates if the request succeeded")
    data: Optional[DataT] = Field(default=None, description="Payload data")
    error: Optional[str] = Field(default=None, description="Error message if any")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of response generation",
    )


class HealthResponse(BaseModel):
    """Schema for health status endpoint."""
    status: str = Field(..., description="'ok' when healthy, 'degraded' when dependencies fail")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Running environment")
    database: str = Field(..., description="'connected' or failure description")
    scheduler: Dict[str, Any] if "Dict" in globals() else Any
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModulePlaceholderResponse(BaseModel):
    """Generic response for planned feature endpoints."""
    module: str
    status: str = "planned"
    message: str
    capabilities_planned: list[str]
