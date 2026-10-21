"""
Automated test suite for the Health Tracker module.
Tests:
- Health profile configuration and provisional default target behavior
- Meal logging CRUD operations and validation
- Deterministic SQL daily summaries and client local date timezone evaluation
- Reference dataset portion estimations, macro scaling, and unsupported food flagging
- Separation of estimation from persistence (mandatory user confirmation)
- Coordinator routing to health module
"""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import app
from backend.core.database import Base, get_db
from backend.modules.health.models import MealType, HealthProfile, MealLog
from backend.core.coordinator import coordinator, IntentType

# In-memory SQLite engine for fast, isolated test execution
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Create fresh schema before each test and drop after."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.pop(get_db, None)



def test_health_module_info():
    """Verify health module info endpoint reports active status and key capabilities."""
    res = client.get("/api/health-tracker")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["module"] == "health"
    assert data["data"]["status"] == "active"
    assert len(data["data"]["capabilities_planned"]) >= 4


def test_health_profile_defaults_and_provisional_flag():
    """Verify default calorie target is clearly flagged as provisional."""
    res = client.get("/api/health-tracker/profile")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["daily_calorie_target"] == 2000
    assert data["target_is_provisional"] is True


def test_health_profile_update_clears_provisional():
    """Verify updating the target sets target_is_provisional=False when customized."""
    update_payload = {
        "daily_calorie_target": 2250,
        "weight_kg": 72.5,
        "height_cm": 178.0,
        "age": 28,
        "activity_level": "Moderate (gym 4x/week)",
        "dietary_preferences": "High protein vegetarian",
    }
    res = client.put("/api/health-tracker/profile", json=update_payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["daily_calorie_target"] == 2250
    assert data["target_is_provisional"] is False
    assert float(data["weight_kg"]) == 72.5
    assert float(data["height_cm"]) == 178.0
    assert data["age"] == 28


def test_create_and_validate_meal():
    """Verify meal logging with positive calories and validation guards."""
    valid_meal = {
        "meal_type": "lunch",
        "food_items": "2 rotis, 1 bowl dal, mixed salad",
        "portion_notes": "2 rotis (~80g), 1 bowl dal (~150g), 1 bowl salad (~150g)",
        "calories": 408,
        "protein_g": 16.7,
        "carbs_g": 73.0,
        "fat_g": 5.8,
        "meal_date": str(date.today()),
        "meal_time": "13:30",
        "notes": "Home cooked lunch",
        "is_estimated": False,
    }
    res = client.post("/api/health-tracker/meals", json=valid_meal)
    assert res.status_code == 201
    meal = res.json()["data"]
    assert meal["id"] > 0
    assert meal["calories"] == 408
    assert meal["meal_type"] == "lunch"

    # Validation: negative calories rejected
    invalid_meal = valid_meal.copy()
    invalid_meal["calories"] = -50
    res_err = client.post("/api/health-tracker/meals", json=invalid_meal)
    assert res_err.status_code == 422

    # Validation: empty food_items rejected
    empty_items = valid_meal.copy()
    empty_items["food_items"] = "   "
    res_empty = client.post("/api/health-tracker/meals", json=empty_items)
    assert res_empty.status_code == 422


def test_meal_crud_operations():
    """Verify get, update, and delete operations on meal logs."""
    # 1. Create
    meal_data = {
        "meal_type": "breakfast",
        "food_items": "Oatmeal with almonds",
        "calories": 210,
        "protein_g": 7.5,
        "carbs_g": 27.5,
        "fat_g": 8.5,
        "meal_date": str(date.today()),
    }
    create_res = client.post("/api/health-tracker/meals", json=meal_data)
    meal_id = create_res.json()["data"]["id"]

    # 2. Get by ID
    get_res = client.get(f"/api/health-tracker/meals/{meal_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["calories"] == 210

    # 3. Update
    update_res = client.put(
        f"/api/health-tracker/meals/{meal_id}",
        json={"calories": 250, "notes": "Added half sliced banana"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["calories"] == 250
    assert update_res.json()["data"]["notes"] == "Added half sliced banana"

    # 4. Delete
    del_res = client.delete(f"/api/health-tracker/meals/{meal_id}")
    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted"] is True

    # 5. Verify deleted
    not_found = client.get(f"/api/health-tracker/meals/{meal_id}")
    assert not_found.status_code == 404


def test_deterministic_daily_summary_and_timezone_local_date():
    """
    Verify daily summary calculations are deterministic and strictly bounded
    by the client's local calendar date.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Log 2 meals today
    client.post(
        "/api/health-tracker/meals",
        json={
            "meal_type": "breakfast",
            "food_items": "2 eggs and toast",
            "calories": 228,
            "protein_g": 15.1,
            "carbs_g": 15.8,
            "fat_g": 11.0,
            "meal_date": str(today),
        },
    )
    client.post(
        "/api/health-tracker/meals",
        json={
            "meal_type": "lunch",
            "food_items": "Rice and dal with curd",
            "calories": 455,
            "protein_g": 18.0,
            "carbs_g": 72.0,
            "fat_g": 10.0,
            "meal_date": str(today),
        },
    )

    # Log 1 meal yesterday (should NOT be counted in today's summary)
    client.post(
        "/api/health-tracker/meals",
        json={
            "meal_type": "dinner",
            "food_items": "Paneer curry and roti",
            "calories": 528,
            "protein_g": 21.0,
            "carbs_g": 34.0,
            "fat_g": 26.5,
            "meal_date": str(yesterday),
        },
    )

    # Fetch daily summary for today
    res = client.get(f"/api/health-tracker/daily-summary?client_date={today}")
    assert res.status_code == 200
    summary = res.json()["data"]

    # Target default is 2000
    assert summary["calorie_target"] == 2000
    assert summary["target_is_provisional"] is True
    # Consumed today = 228 + 455 = 683
    assert summary["calories_consumed"] == 683
    # Remaining = 2000 - 683 = 1317
    assert summary["calories_remaining"] == 1317
    assert summary["percentage_consumed"] == round((683 / 2000) * 100, 1)

    # Total macros today
    assert float(summary["total_protein_g"]) == pytest.approx(15.1 + 18.0, 0.01)
    assert float(summary["total_carbs_g"]) == pytest.approx(15.8 + 72.0, 0.01)
    assert float(summary["total_fat_g"]) == pytest.approx(11.0 + 10.0, 0.01)

    # Verify only today's 2 meals are included
    assert len(summary["today_meals"]) == 2

    # Verify meal type breakdown
    b_down = {item["meal_type"]: item["calories"] for item in summary["meal_type_breakdown"]}
    assert b_down["breakfast"] == 228
    assert b_down["lunch"] == 455
    assert b_down["dinner"] == 0
    assert b_down["snack"] == 0


def test_meal_estimate_with_reference_dataset_and_confirmation_requirement():
    """
    Verify portion estimation against verified reference dataset.
    Confirms that estimation produces a draft requiring explicit confirmation
    and DOES NOT automatically persist to the database.
    """
    # 1. Request estimation
    estimate_req = {
        "text": "2 rotis and 1 bowl dal",
        "meal_type": "lunch",
    }
    res = client.post("/api/health-tracker/estimate-meal", json=estimate_req)
    assert res.status_code == 200
    draft = res.json()["data"]

    # Roti is 104 kcal each -> 2x = 208 kcal
    # Dal is 165 kcal for 1 bowl -> 1x = 165 kcal
    # Total = 373 kcal
    assert draft["total_calories"] == 373
    assert draft["requires_confirmation"] is True
    assert draft["has_unsupported_items"] is False

    # Check item details and portion notes
    items = draft["items"]
    assert len(items) == 2
    assert items[0]["matched_food_name"] == "Roti / Chapati"
    assert "2x" in items[0]["assumed_portion"]
    assert items[1]["matched_food_name"] == "Yellow Dal / Dal Tadka"

    # 2. Verify nothing has been saved to the database yet!
    db_meals = client.get("/api/health-tracker/meals")
    assert db_meals.json()["data"]["total"] == 0

    # 3. Explicitly confirm and save
    save_res = client.post("/api/health-tracker/meals", json=draft["interpreted"])
    assert save_res.status_code == 201
    assert save_res.json()["data"]["calories"] == 373

    # Now database has 1 meal
    db_meals_after = client.get("/api/health-tracker/meals")
    assert db_meals_after.json()["data"]["total"] == 1


def test_meal_estimate_with_unsupported_food():
    """Verify unsupported foods are cleanly flagged and not given invented precision."""
    estimate_req = {
        "text": "2 rotis and 1 bowl celestial moon stew",
    }
    res = client.post("/api/health-tracker/estimate-meal", json=estimate_req)
    assert res.status_code == 200
    draft = res.json()["data"]

    assert draft["has_unsupported_items"] is True
    assert any("moon stew" in u.lower() for u in draft["unsupported_items"])
    assert draft["requires_confirmation"] is True
    # 2 rotis estimated (208 kcal), unsupported item has 0 kcal
    assert draft["total_calories"] == 208
    assert "Could not find reference data" in draft["message"]


def test_list_meals_filtering_and_pagination():
    """Verify meal list filtering by date range, meal type, and pagination."""
    today = date.today()
    for i in range(5):
        client.post(
            "/api/health-tracker/meals",
            json={
                "meal_type": "snack" if i % 2 == 0 else "breakfast",
                "food_items": f"Snack item {i}",
                "calories": 100 + i * 10,
                "meal_date": str(today - timedelta(days=i)),
            },
        )

    # Filter by snack
    res_snack = client.get("/api/health-tracker/meals?meal_type=snack")
    assert res_snack.status_code == 200
    assert res_snack.json()["data"]["total"] == 3

    # Paginate with page_size=2
    res_paged = client.get("/api/health-tracker/meals?page=1&page_size=2")
    assert res_paged.status_code == 200
    p_data = res_paged.json()["data"]
    assert len(p_data["items"]) == 2
    assert p_data["total"] == 5
    assert p_data["total_pages"] == 3


def test_coordinator_routes_health_queries():
    """Verify coordinator properly classifies health and calorie intents."""
    assert coordinator.classify_intent("Log my meal of 2 rotis and dal") == IntentType.HEALTH
    assert coordinator.classify_intent("How many calories did I eat today?") == IntentType.HEALTH
    assert coordinator.classify_intent("What is my daily calorie target?") == IntentType.HEALTH

    res = client.post(
        "/api/coordinator/route",
        json={"text": "Log 350 kcal for lunch", "context": {}},
    )
    assert res.status_code == 200
    payload = res.json()["data"]
    assert payload["intent"] == "health"
    assert payload["target_module"] == "backend.modules.health"
