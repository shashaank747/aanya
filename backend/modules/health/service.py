"""
Business logic and persistence service for the Health Tracker module.
Handles profile settings, meal CRUD, deterministic SQL daily metrics,
and local rule-based calorie estimation with mandatory confirmation.
"""
from typing import Optional, List, Tuple
from datetime import date, datetime, timezone
from decimal import Decimal
import re

from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import Session

from backend.modules.health.models import HealthProfile, MealLog, MealType
from backend.modules.health.schemas import (
    HealthProfileUpdate,
    MealCreate,
    MealUpdate,
    MealResponse,
    DailyHealthSummary,
    MealTypeSummary,
    MealEstimateResponse,
    EstimatedItemDetail,
)
from backend.modules.health.food_database import (
    find_food_in_reference,
    extract_quantity_and_multiplier,
)


def get_or_create_profile(db: Session) -> HealthProfile:
    """
    Retrieve user health profile or initialize with safe provisional defaults.
    Notice: Default target (2000 kcal) is explicitly flagged target_is_provisional=True.
    """
    profile = db.execute(select(HealthProfile).order_by(HealthProfile.id.asc())).scalars().first()
    if not profile:
        profile = HealthProfile(
            daily_calorie_target=2000,
            target_is_provisional=True,
            notes="Default provisional profile initialized.",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_profile(db: Session, profile_in: HealthProfileUpdate) -> HealthProfile:
    """
    Update health profile and calorie targets.
    If the user customizes daily_calorie_target and did not explicitly specify target_is_provisional,
    the provisional flag is cleared to reflect a user-calibrated target.
    """
    profile = get_or_create_profile(db)

    update_data = profile_in.model_dump(exclude_unset=True)

    # If target is explicitly updated by the user and provisional flag not set, clear provisional
    if "daily_calorie_target" in update_data and "target_is_provisional" not in update_data:
        update_data["target_is_provisional"] = False

    for field, value in update_data.items():
        setattr(profile, field, value)

    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile


def create_meal(db: Session, meal_in: MealCreate) -> MealLog:
    """
    Persist a user-confirmed meal log to the backend database.
    """
    meal_data = meal_in.model_dump()
    meal = MealLog(**meal_data)
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return meal


def get_meal(db: Session, meal_id: int) -> Optional[MealLog]:
    """Retrieve a single meal by ID."""
    return db.execute(select(MealLog).where(MealLog.id == meal_id)).scalars().first()


def update_meal(db: Session, meal_id: int, meal_in: MealUpdate) -> Optional[MealLog]:
    """Update fields of an existing meal log entry."""
    meal = get_meal(db, meal_id)
    if not meal:
        return None

    update_data = meal_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meal, field, value)

    meal.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(meal)
    return meal


def delete_meal(db: Session, meal_id: int) -> bool:
    """Delete a meal log entry by ID."""
    meal = get_meal(db, meal_id)
    if not meal:
        return False

    db.delete(meal)
    db.commit()
    return True


def list_meals(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    meal_type: Optional[MealType] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[MealLog], int]:
    """
    Retrieve paginated list of meal logs matching filters.
    """
    query = select(MealLog)
    conditions = []

    if start_date:
        conditions.append(MealLog.meal_date >= start_date)
    if end_date:
        conditions.append(MealLog.meal_date <= end_date)
    if meal_type:
        conditions.append(MealLog.meal_type == meal_type)

    if conditions:
        query = query.where(and_(*conditions))

    # Total count query
    count_query = select(func.count(MealLog.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = db.execute(count_query).scalar_one()

    # Pagination and sorting
    offset = (page - 1) * page_size
    query = query.order_by(desc(MealLog.meal_date), desc(MealLog.id)).offset(offset).limit(page_size)

    items = db.execute(query).scalars().all()
    return list(items), total


def get_daily_summary(db: Session, client_date: Optional[date] = None) -> DailyHealthSummary:
    """
    Compute daily health and nutrition totals deterministically from the database.
    The user's local date (client_date) strictly determines the evaluation window.
    """
    target_date = client_date or date.today()
    profile = get_or_create_profile(db)
    calorie_target = profile.daily_calorie_target
    target_is_provisional = profile.target_is_provisional

    # Compute daily aggregate sums
    stmt = select(
        func.coalesce(func.sum(MealLog.calories), 0).label("total_calories"),
        func.coalesce(func.sum(MealLog.protein_g), 0.0).label("total_protein"),
        func.coalesce(func.sum(MealLog.carbs_g), 0.0).label("total_carbs"),
        func.coalesce(func.sum(MealLog.fat_g), 0.0).label("total_fat"),
    ).where(MealLog.meal_date == target_date)

    row = db.execute(stmt).one()
    calories_consumed = int(row.total_calories)
    total_protein = Decimal(str(row.total_protein)).quantize(Decimal("0.01"))
    total_carbs = Decimal(str(row.total_carbs)).quantize(Decimal("0.01"))
    total_fat = Decimal(str(row.total_fat)).quantize(Decimal("0.01"))

    calories_remaining = max(0, calorie_target - calories_consumed)
    percentage = round((calories_consumed / calorie_target) * 100, 1) if calorie_target > 0 else 0.0

    # Meal type breakdown
    type_stmt = (
        select(
            MealLog.meal_type,
            func.coalesce(func.sum(MealLog.calories), 0).label("type_calories"),
            func.count(MealLog.id).label("type_count"),
        )
        .where(MealLog.meal_date == target_date)
        .group_by(MealLog.meal_type)
    )
    type_rows = db.execute(type_stmt).all()
    breakdown_map = {r.meal_type.value if hasattr(r.meal_type, "value") else str(r.meal_type): (int(r.type_calories), int(r.type_count)) for r in type_rows}

    # Standard order of meal categories
    standard_types = [MealType.BREAKFAST.value, MealType.LUNCH.value, MealType.DINNER.value, MealType.SNACK.value]
    meal_type_breakdown = [
        MealTypeSummary(
            meal_type=m_type,
            calories=breakdown_map.get(m_type, (0, 0))[0],
            meal_count=breakdown_map.get(m_type, (0, 0))[1],
        )
        for m_type in standard_types
    ]

    # Fetch all meals for that day
    meals_stmt = select(MealLog).where(MealLog.meal_date == target_date).order_by(MealLog.id.asc())
    today_meals = [MealResponse.model_validate(m) for m in db.execute(meals_stmt).scalars().all()]

    return DailyHealthSummary(
        client_date=target_date,
        calorie_target=calorie_target,
        target_is_provisional=target_is_provisional,
        calories_consumed=calories_consumed,
        calories_remaining=calories_remaining,
        percentage_consumed=percentage,
        total_protein_g=total_protein,
        total_carbs_g=total_carbs,
        total_fat_g=total_fat,
        meal_type_breakdown=meal_type_breakdown,
        today_meals=today_meals,
    )


def infer_meal_type_from_text(text: str) -> MealType:
    """Infer meal type from text keywords or current local time."""
    text_lower = text.lower()
    if any(k in text_lower for k in ["breakfast", "morning", "nashta", "idli", "dosa", "poha", "upma", "cereal"]):
        return MealType.BREAKFAST
    if any(k in text_lower for k in ["lunch", "afternoon", "dopahar"]):
        return MealType.LUNCH
    if any(k in text_lower for k in ["dinner", "night", "supper", "shaam ka khana"]):
        return MealType.DINNER
    if any(k in text_lower for k in ["snack", "tea", "chai", "coffee", "biscuit", "samosa", "evening"]):
        return MealType.SNACK

    # Fallback based on current UTC/local hour
    current_hour = datetime.now().hour
    if 5 <= current_hour < 11:
        return MealType.BREAKFAST
    elif 11 <= current_hour < 16:
        return MealType.LUNCH
    elif 16 <= current_hour < 19:
        return MealType.SNACK
    else:
        return MealType.DINNER


def estimate_meal_from_text(
    text: str,
    meal_type: Optional[MealType] = None,
    meal_date: Optional[date] = None,
) -> MealEstimateResponse:
    """
    Estimate calories and portions locally from verified reference dataset.
    Flags unsupported foods or uncertain estimates.
    Requires explicit user confirmation before persistence.
    """
    raw_text = text.strip()
    target_date = meal_date or date.today()
    inferred_type = meal_type or infer_meal_type_from_text(raw_text)

    # Split text into food clauses by commas, 'and', 'with', 'plus', '&', '+'
    clauses = re.split(r",|\band\b|\bwith\b|\bplus\b|&|\+", raw_text, flags=re.IGNORECASE)
    cleaned_clauses = [c.strip() for c in clauses if c.strip()]

    items: List[EstimatedItemDetail] = []
    unsupported_items: List[str] = []
    total_calories = 0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    portion_notes_parts: List[str] = []

    for clause in cleaned_clauses:
        # Ignore pure filler words
        if clause.lower() in ["for breakfast", "for lunch", "for dinner", "as a snack", "today", "yesterday"]:
            continue

        match_res = find_food_in_reference(clause)
        if match_res:
            food_item, alias = match_res
            multiplier, portion_desc = extract_quantity_and_multiplier(
                clause, alias, food_item.standard_portion_desc
            )
            item_cal = round(food_item.calories * multiplier)
            item_p = round(food_item.protein_g * multiplier, 1)
            item_c = round(food_item.carbs_g * multiplier, 1)
            item_f = round(food_item.fat_g * multiplier, 1)

            total_calories += item_cal
            total_protein += item_p
            total_carbs += item_c
            total_fat += item_f

            portion_notes_parts.append(f"{food_item.name}: {portion_desc}")
            items.append(
                EstimatedItemDetail(
                    raw_item_text=clause,
                    matched_food_name=food_item.name,
                    is_supported=True,
                    assumed_portion=portion_desc,
                    calories=item_cal,
                    protein_g=item_p,
                    carbs_g=item_c,
                    fat_g=item_f,
                    notes=f"Reference verified ({food_item.category})",
                )
            )
        else:
            # Unsupported food clause
            unsupported_items.append(clause)
            portion_notes_parts.append(f"'{clause}': portion unknown (unsupported)")
            items.append(
                EstimatedItemDetail(
                    raw_item_text=clause,
                    matched_food_name=None,
                    is_supported=False,
                    assumed_portion="Not found in reference database",
                    calories=0,
                    protein_g=0.0,
                    carbs_g=0.0,
                    fat_g=0.0,
                    notes="Unsupported item: please enter calorie value manually.",
                )
            )

    has_unsupported = len(unsupported_items) > 0

    if has_unsupported:
        message = (
            f"Estimated {total_calories} kcal for recognized items. "
            f"Note: Could not find reference data for {', '.join(repr(u) for u in unsupported_items)}. "
            "Please review portion assumptions and enter any missing calories before confirming."
        )
    elif items:
        message = (
            f"Estimated {total_calories} kcal based on standard portions for {len(items)} item(s). "
            "Please review and confirm to save this meal."
        )
    else:
        message = (
            "Could not detect recognizable food items. "
            "Please enter calories and food details manually."
        )

    interpreted = MealCreate(
        meal_type=inferred_type,
        food_items=raw_text,
        portion_notes="; ".join(portion_notes_parts) if portion_notes_parts else None,
        calories=total_calories,
        protein_g=Decimal(str(round(total_protein, 2))),
        carbs_g=Decimal(str(round(total_carbs, 2))),
        fat_g=Decimal(str(round(total_fat, 2))),
        meal_date=target_date,
        meal_time=datetime.now().strftime("%H:%M"),
        is_estimated=True,
        estimation_notes=message,
    )

    return MealEstimateResponse(
        interpreted=interpreted,
        items=items,
        has_unsupported_items=has_unsupported,
        unsupported_items=unsupported_items,
        total_calories=total_calories,
        requires_confirmation=True,
        message=message,
    )
