"""
FastAPI router for the Health Tracker module.
Exposes health profile management, meal CRUD, deterministic daily summaries,
and reference calorie estimation drafts requiring user confirmation.
"""
from typing import Optional, List
from datetime import date
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas import StandardResponse, ModulePlaceholderResponse
from backend.modules.health.models import MealType
from backend.modules.health.schemas import (
    HealthProfileResponse,
    HealthProfileUpdate,
    MealCreate,
    MealUpdate,
    MealResponse,
    PaginatedMealsResponse,
    DailyHealthSummary,
    MealEstimateRequest,
    MealEstimateResponse,
)
from backend.modules.health import service

router = APIRouter(prefix="/health-tracker", tags=["Health Tracker"])


@router.get("", response_model=StandardResponse[ModulePlaceholderResponse])
def get_health_module_info():
    """Module status information endpoint."""
    return StandardResponse(
        success=True,
        data=ModulePlaceholderResponse(
            module="health",
            status="active",
            message="Health Tracker active. Supports calorie targets, meal logging, and verified portion estimation.",
            capabilities_planned=[
                "Configurable calorie target with explicit provisional defaults",
                "Deterministic daily summary based on client local date",
                "Macronutrient tracking (protein, carbs, fat)",
                "Local reference-based meal calorie estimation with portion assumptions",
                "Strict confirmation requirement before meal persistence",
                "100% backend isolation (no external AI calls)",
            ],
        ),
    )


@router.get("/profile", response_model=StandardResponse[HealthProfileResponse])
def get_health_profile(db: Session = Depends(get_db)):
    """Retrieve user health profile and calorie target settings."""
    profile = service.get_or_create_profile(db)
    return StandardResponse(
        success=True,
        data=HealthProfileResponse.model_validate(profile),
    )


@router.put("/profile", response_model=StandardResponse[HealthProfileResponse])
def update_health_profile(
    profile_in: HealthProfileUpdate,
    db: Session = Depends(get_db),
):
    """
    Update personal health profile and daily calorie target.
    Setting an explicit calorie target clears the provisional flag unless explicitly requested otherwise.
    """
    updated = service.update_profile(db, profile_in)
    return StandardResponse(
        success=True,
        data=HealthProfileResponse.model_validate(updated),
    )


@router.get("/daily-summary", response_model=StandardResponse[DailyHealthSummary])
def get_daily_summary(
    client_date: Optional[date] = Query(None, description="User's local calendar date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Retrieve deterministic daily calorie and macronutrient summary.
    The evaluation day is strictly determined by client_date in the user's local timezone.
    """
    summary = service.get_daily_summary(db, client_date=client_date)
    return StandardResponse(
        success=True,
        data=summary,
    )


@router.post("/estimate-meal", response_model=StandardResponse[MealEstimateResponse])
def estimate_meal_endpoint(
    request: MealEstimateRequest,
):
    """
    Generate an estimated meal draft from natural-language description using verified reference data.
    Displays assumed portion sizes and flags unsupported foods.
    Requires explicit user confirmation before persisting to the database.
    """
    draft = service.estimate_meal_from_text(
        text=request.text,
        meal_type=request.meal_type,
        meal_date=request.meal_date,
    )
    return StandardResponse(
        success=True,
        data=draft,
    )


@router.post("/meals", response_model=StandardResponse[MealResponse], status_code=status.HTTP_201_CREATED)
def create_meal_endpoint(
    meal_in: MealCreate,
    db: Session = Depends(get_db),
):
    """Save a confirmed meal entry to the database."""
    created = service.create_meal(db, meal_in)
    return StandardResponse(
        success=True,
        data=MealResponse.model_validate(created),
    )


@router.get("/meals", response_model=StandardResponse[PaginatedMealsResponse])
def list_meals_endpoint(
    start_date: Optional[date] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (inclusive)"),
    meal_type: Optional[MealType] = Query(None, description="Filter by meal type"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated meal history with optional date and category filters."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date",
        )

    items, total = service.list_meals(
        db,
        start_date=start_date,
        end_date=end_date,
        meal_type=meal_type,
        page=page,
        page_size=page_size,
    )

    total_pages = ceil(total / page_size) if total > 0 else 1
    items_pydantic = [MealResponse.model_validate(i) for i in items]

    return StandardResponse(
        success=True,
        data=PaginatedMealsResponse(
            items=items_pydantic,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get("/meals/{meal_id}", response_model=StandardResponse[MealResponse])
def get_meal_endpoint(
    meal_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve details of a single meal entry by ID."""
    meal = service.get_meal(db, meal_id)
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meal with ID {meal_id} not found",
        )
    return StandardResponse(
        success=True,
        data=MealResponse.model_validate(meal),
    )


@router.put("/meals/{meal_id}", response_model=StandardResponse[MealResponse])
def update_meal_endpoint(
    meal_id: int,
    meal_in: MealUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing meal log entry."""
    updated = service.update_meal(db, meal_id, meal_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meal with ID {meal_id} not found",
        )
    return StandardResponse(
        success=True,
        data=MealResponse.model_validate(updated),
    )


@router.delete("/meals/{meal_id}", response_model=StandardResponse[dict])
def delete_meal_endpoint(
    meal_id: int,
    db: Session = Depends(get_db),
):
    """Delete a meal log entry by ID."""
    deleted = service.delete_meal(db, meal_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meal with ID {meal_id} not found",
        )
    return StandardResponse(
        success=True,
        data={"deleted": True, "id": meal_id},
    )
