"""
Pydantic schemas for the Health Tracker module.
Defines contracts for health profiles, meal logging, deterministic daily aggregations,
and estimation drafts requiring explicit user confirmation.
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from backend.modules.health.models import MealType


class HealthProfileBase(BaseModel):
    """Base fields for personal health profile and calorie targets."""
    daily_calorie_target: int = Field(
        default=2000,
        gt=0,
        le=10000,
        description="Daily caloric target in kcal. Note: Defaults are provisional until explicitly calibrated.",
    )
    target_is_provisional: bool = Field(
        default=True,
        description="Flag indicating if the target is a provisional default rather than a personalized target.",
    )
    height_cm: Optional[Decimal] = Field(default=None, gt=Decimal("30.0"), lt=Decimal("300.0"), description="Height in cm")
    weight_kg: Optional[Decimal] = Field(default=None, gt=Decimal("10.0"), lt=Decimal("500.0"), description="Weight in kg")
    age: Optional[int] = Field(default=None, gt=0, lt=130, description="Age in years")
    gender: Optional[str] = Field(default=None, max_length=20, description="Gender identity")
    activity_level: Optional[str] = Field(default=None, max_length=50, description="Sedentary, Light, Moderate, Active, etc.")
    dietary_preferences: Optional[str] = Field(default=None, max_length=255, description="Vegetarian, Vegan, Keto, etc.")
    notes: Optional[str] = Field(default=None, max_length=1000, description="Personal health/diet notes")


class HealthProfileUpdate(BaseModel):
    """Schema for updating the health profile and calorie targets."""
    daily_calorie_target: Optional[int] = Field(default=None, gt=0, le=10000)
    target_is_provisional: Optional[bool] = Field(
        default=None,
        description="Explicitly set provisional flag. If not provided and target is updated, becomes False.",
    )
    height_cm: Optional[Decimal] = Field(default=None, gt=Decimal("30.0"), lt=Decimal("300.0"))
    weight_kg: Optional[Decimal] = Field(default=None, gt=Decimal("10.0"), lt=Decimal("500.0"))
    age: Optional[int] = Field(default=None, gt=0, lt=130)
    gender: Optional[str] = Field(default=None, max_length=20)
    activity_level: Optional[str] = Field(default=None, max_length=50)
    dietary_preferences: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=1000)


class HealthProfileResponse(HealthProfileBase):
    """Response schema for health profile."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MealBase(BaseModel):
    """Base fields for a logged meal."""
    meal_type: MealType = Field(..., description="breakfast, lunch, dinner, or snack")
    food_items: str = Field(..., min_length=1, max_length=500, description="List or description of foods eaten")
    portion_notes: Optional[str] = Field(default=None, max_length=500, description="Assumed or specified portion sizes")
    calories: int = Field(..., ge=0, le=10000, description="Energy intake in kcal")
    protein_g: Optional[Decimal] = Field(default=None, ge=Decimal("0.0"), decimal_places=2, max_digits=6)
    carbs_g: Optional[Decimal] = Field(default=None, ge=Decimal("0.0"), decimal_places=2, max_digits=6)
    fat_g: Optional[Decimal] = Field(default=None, ge=Decimal("0.0"), decimal_places=2, max_digits=6)
    meal_date: date = Field(default_factory=date.today, description="User's local calendar date (YYYY-MM-DD)")
    meal_time: Optional[str] = Field(default=None, max_length=8, description="Time of meal in HH:MM format")
    notes: Optional[str] = Field(default=None, max_length=1000, description="Optional meal notes")
    is_estimated: bool = Field(default=False, description="Whether calorie count was derived from automated estimation")
    estimation_notes: Optional[str] = Field(default=None, max_length=1000, description="Portion assumptions & estimation flags")

    @field_validator("food_items")
    @classmethod
    def validate_food_items(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("food_items cannot be empty or whitespace only.")
        return v_stripped


class MealCreate(MealBase):
    """Schema for persisting a confirmed meal."""
    pass


class MealUpdate(BaseModel):
    """Schema for modifying an existing meal log entry."""
    meal_type: Optional[MealType] = None
    food_items: Optional[str] = Field(default=None, min_length=1, max_length=500)
    portion_notes: Optional[str] = Field(default=None, max_length=500)
    calories: Optional[int] = Field(default=None, ge=0, le=10000)
    protein_g: Optional[Decimal] = Field(default=None, ge=Decimal("0.0"), decimal_places=2, max_digits=6)
    carbs_g: Optional[Decimal] = Field(default=None, ge=Decimal("0.0"), decimal_places=2, max_digits=6)
    fat_g: Optional[Decimal] = Field(default=None, ge=Decimal("0.0"), decimal_places=2, max_digits=6)
    meal_date: Optional[date] = None
    meal_time: Optional[str] = Field(default=None, max_length=8)
    notes: Optional[str] = Field(default=None, max_length=1000)
    is_estimated: Optional[bool] = None
    estimation_notes: Optional[str] = Field(default=None, max_length=1000)


class MealResponse(MealBase):
    """API response schema for logged meals."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedMealsResponse(BaseModel):
    """Paginated collection of logged meals."""
    items: List[MealResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EstimatedItemDetail(BaseModel):
    """Detailed portion assumption and reference lookup for an individual food item."""
    raw_item_text: str
    matched_food_name: Optional[str] = None
    is_supported: bool = True
    assumed_portion: str
    calories: int = 0
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    notes: Optional[str] = None


class MealEstimateRequest(BaseModel):
    """User input text for estimating calorie content and portion sizes."""
    text: str = Field(..., min_length=2, max_length=500, description="Natural meal description, e.g., '2 rotis and 1 bowl dal'")
    meal_type: Optional[MealType] = Field(default=None, description="Optional override for meal category")
    meal_date: Optional[date] = Field(default=None, description="Optional local calendar date")


class MealEstimateResponse(BaseModel):
    """
    Structured estimation draft.
    Explicitly requires user confirmation before saving to the database.
    """
    interpreted: MealCreate
    items: List[EstimatedItemDetail]
    has_unsupported_items: bool
    unsupported_items: List[str]
    total_calories: int
    requires_confirmation: bool = Field(default=True, description="Always true: user must confirm before persistence")
    message: str


class MealTypeSummary(BaseModel):
    """Meal-type breakdown summary."""
    meal_type: str
    calories: int
    meal_count: int


class DailyHealthSummary(BaseModel):
    """
    Authoritative daily summary computed deterministically from the database
    for the user's local calendar date.
    """
    client_date: date
    calorie_target: int
    target_is_provisional: bool
    calories_consumed: int
    calories_remaining: int
    percentage_consumed: float
    total_protein_g: Decimal
    total_carbs_g: Decimal
    total_fat_g: Decimal
    meal_type_breakdown: List[MealTypeSummary]
    today_meals: List[MealResponse]
