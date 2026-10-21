"""
SQLAlchemy models for the Health Tracker module.
Stores personal health configuration and meal logs.
All health data remains exclusively in the backend database.
"""
import enum
from datetime import datetime, date, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    Time,
    DateTime,
    Boolean,
    Text,
    Enum as SQLEnum,
    CheckConstraint,
    Index,
)
from backend.core.database import Base


class MealType(str, enum.Enum):
    """Categorized meal types."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class HealthProfile(Base):
    """
    User health profile and calorie targets.
    Notice: Default targets are explicitly flagged as provisional (target_is_provisional=True)
    to avoid presenting uncalibrated values as medical recommendations.
    """
    __tablename__ = "health_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    daily_calorie_target = Column(Integer, nullable=False, default=2000)
    target_is_provisional = Column(Boolean, nullable=False, default=True)

    height_cm = Column(Numeric(5, 2), nullable=True)
    weight_kg = Column(Numeric(5, 2), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    activity_level = Column(String(50), nullable=True)
    dietary_preferences = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("daily_calorie_target > 0", name="check_positive_calorie_target"),
    )


class MealLog(Base):
    """
    Log of individual meals and food intake.
    Maintains assumed portions and estimation metadata separately from raw calories.
    """
    __tablename__ = "health_meals"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    meal_type = Column(SQLEnum(MealType, name="meal_type_enum"), nullable=False, index=True)
    food_items = Column(Text, nullable=False)
    portion_notes = Column(Text, nullable=True)  # Assumed portion sizes (e.g., '2 rotis (~80g), 1 cup dal (~150g)')
    calories = Column(Integer, nullable=False)  # Calorie energy in kcal

    protein_g = Column(Numeric(6, 2), nullable=True)
    carbs_g = Column(Numeric(6, 2), nullable=True)
    fat_g = Column(Numeric(6, 2), nullable=True)

    meal_date = Column(Date, nullable=False, default=date.today, index=True)
    meal_time = Column(String(8), nullable=True)  # HH:MM format in user's local timezone
    notes = Column(Text, nullable=True)

    is_estimated = Column(Boolean, nullable=False, default=False)
    estimation_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("calories >= 0", name="check_non_negative_calories"),
        Index("ix_health_meals_date_type", "meal_date", "meal_type"),
    )
