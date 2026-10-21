"""
Automated test suite for the Finance Tracker module.
Tests CRUD operations, input validation, deterministic SQL calculations,
category distributions, pagination, and natural-language interpretation.
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
from backend.modules.finance.models import FinanceTransaction, TransactionType

# In-memory SQLite for isolated, fast, deterministic testing
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



def test_create_income_and_expense_transaction():
    """Verify transaction creation with NUMERIC precision."""
    # 1. Create Income
    income_data = {
        "type": "income",
        "amount": 75000.50,
        "category": "Salary",
        "description": "October Monthly Salary",
        "transaction_date": str(date.today()),
        "payment_method": "Net Banking",
        "notes": "Direct bank deposit",
    }
    res = client.post("/api/finance/transactions", json=income_data)
    assert res.status_code == 201
    json_data = res.json()["data"]
    assert json_data["id"] is not None
    assert json_data["type"] == "income"
    assert Decimal(str(json_data["amount"])) == Decimal("75000.50")
    assert json_data["category"] == "Salary"

    # 2. Create Expense
    expense_data = {
        "type": "expense",
        "amount": 450.00,
        "category": "Food & Dining",
        "description": "Lunch with team",
        "transaction_date": str(date.today()),
        "payment_method": "UPI",
    }
    res2 = client.post("/api/finance/transactions", json=expense_data)
    assert res2.status_code == 201
    assert res2.json()["data"]["type"] == "expense"
    assert Decimal(str(res2.json()["data"]["amount"])) == Decimal("450.00")


def test_transaction_input_validation():
    """Verify backend enforces positive amounts and non-empty descriptions."""
    # Negative amount
    res = client.post(
        "/api/finance/transactions",
        json={
            "type": "expense",
            "amount": -50.00,
            "category": "Food & Dining",
            "description": "Invalid negative",
        },
    )
    assert res.status_code == 422

    # Zero amount
    res = client.post(
        "/api/finance/transactions",
        json={
            "type": "expense",
            "amount": 0.00,
            "category": "Food & Dining",
            "description": "Zero amount",
        },
    )
    assert res.status_code == 422

    # Whitespace-only description
    res = client.post(
        "/api/finance/transactions",
        json={
            "type": "expense",
            "amount": 100.00,
            "category": "Food & Dining",
            "description": "   ",
        },
    )
    assert res.status_code == 422


def test_get_update_delete_transaction():
    """Verify single transaction retrieval, partial update, and deletion."""
    # Create
    res = client.post(
        "/api/finance/transactions",
        json={
            "type": "expense",
            "amount": 1200.00,
            "category": "Utilities & Bills",
            "description": "Electricity bill",
            "payment_method": "UPI",
        },
    )
    tx_id = res.json()["data"]["id"]

    # Read
    get_res = client.get(f"/api/finance/transactions/{tx_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["description"] == "Electricity bill"

    # Update
    update_res = client.put(
        f"/api/finance/transactions/{tx_id}",
        json={"amount": 1350.50, "notes": "Revised after surcharge"},
    )
    assert update_res.status_code == 200
    assert Decimal(str(update_res.json()["data"]["amount"])) == Decimal("1350.50")
    assert update_res.json()["data"]["notes"] == "Revised after surcharge"

    # Delete
    del_res = client.delete(f"/api/finance/transactions/{tx_id}")
    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted"] is True

    # Confirm 404 after deletion
    get_after = client.get(f"/api/finance/transactions/{tx_id}")
    assert get_after.status_code == 404


def test_deterministic_dashboard_calculations():
    """Verify authoritative SQL-calculated totals and category percentages."""
    today = date.today()
    # Populate known values:
    # Income: ₹50,000 (Salary) + ₹10,000 (Freelance) = ₹60,000
    # Expense: ₹3,000 (Utilities) + ₹2,000 (Food & Dining) = ₹5,000
    # Net Balance: ₹55,000
    records = [
        {"type": "income", "amount": 50000.00, "category": "Salary", "description": "Job Salary", "transaction_date": str(today)},
        {"type": "income", "amount": 10000.00, "category": "Freelance & Consulting", "description": "Web Gig", "transaction_date": str(today)},
        {"type": "expense", "amount": 3000.00, "category": "Utilities & Bills", "description": "Broadband & Power", "transaction_date": str(today)},
        {"type": "expense", "amount": 2000.00, "category": "Food & Dining", "description": "Groceries & Dine", "transaction_date": str(today)},
    ]
    for r in records:
        res = client.post("/api/finance/transactions", json=r)
        assert res.status_code == 201

    dash_res = client.get("/api/finance/dashboard")
    assert dash_res.status_code == 200
    data = dash_res.json()["data"]

    # Verify authoritative totals
    assert Decimal(str(data["total_income_this_month"])) == Decimal("60000.00")
    assert Decimal(str(data["total_expenses_this_month"])) == Decimal("5000.00")
    assert Decimal(str(data["net_balance_this_month"])) == Decimal("55000.00")
    assert data["currency_symbol"] == "₹"

    # Verify category distribution
    breakdown = data["category_breakdown"]
    assert len(breakdown) == 2
    # Utilities: 3000 / 5000 = 60.0%
    assert breakdown[0]["category"] == "Utilities & Bills"
    assert Decimal(str(breakdown[0]["total_amount"])) == Decimal("3000.00")
    assert breakdown[0]["percentage_of_total"] == 60.0

    # Food & Dining: 2000 / 5000 = 40.0%
    assert breakdown[1]["category"] == "Food & Dining"
    assert Decimal(str(breakdown[1]["total_amount"])) == Decimal("2000.00")
    assert breakdown[1]["percentage_of_total"] == 40.0


def test_list_transactions_filtering_and_pagination():
    """Verify date filtering, type filtering, and pagination logic."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)

    client.post("/api/finance/transactions", json={"type": "income", "amount": 1000.00, "category": "Salary", "description": "Inc 1", "transaction_date": str(today)})
    client.post("/api/finance/transactions", json={"type": "expense", "amount": 200.00, "category": "Food & Dining", "description": "Exp 1", "transaction_date": str(yesterday)})
    client.post("/api/finance/transactions", json={"type": "expense", "amount": 500.00, "category": "Shopping", "description": "Exp 2", "transaction_date": str(last_week)})

    # Filter by type=expense
    res_exp = client.get("/api/finance/transactions?type=expense")
    assert res_exp.status_code == 200
    assert res_exp.json()["data"]["total"] == 2

    # Filter by date range (yesterday to today)
    res_date = client.get(f"/api/finance/transactions?start_date={yesterday}&end_date={today}")
    assert res_date.status_code == 200
    assert res_date.json()["data"]["total"] == 2

    # Test pagination
    res_page = client.get("/api/finance/transactions?page=1&page_size=2")
    assert res_page.status_code == 200
    pdata = res_page.json()["data"]
    assert len(pdata["items"]) == 2
    assert pdata["total"] == 3
    assert pdata["total_pages"] == 2


def test_natural_language_parsing():
    """Verify natural-language statements parse with requires_confirmation=True."""
    # Test Expense with ₹ symbol
    res1 = client.post(
        "/api/finance/parse-natural-language",
        json={"text": "I spent ₹180 on dinner"},
    )
    assert res1.status_code == 200
    d1 = res1.json()["data"]
    assert d1["requires_confirmation"] is True
    assert d1["interpreted"]["type"] == "expense"
    assert Decimal(str(d1["interpreted"]["amount"])) == Decimal("180.00")
    assert d1["interpreted"]["category"] == "Food & Dining"

    # Test Income with freelance keyword
    res2 = client.post(
        "/api/finance/parse-natural-language",
        json={"text": "I received ₹5,000 from freelance work"},
    )
    assert res2.status_code == 200
    d2 = res2.json()["data"]
    assert d2["requires_confirmation"] is True
    assert d2["interpreted"]["type"] == "income"
    assert Decimal(str(d2["interpreted"]["amount"])) == Decimal("5000.00")
    assert d2["interpreted"]["category"] == "Freelance & Consulting"

    # Test Expense with 'yesterday' relative date
    res3 = client.post(
        "/api/finance/parse-natural-language",
        json={"text": "I paid ₹1,200 for electricity yesterday"},
    )
    assert res3.status_code == 200
    d3 = res3.json()["data"]
    assert d3["requires_confirmation"] is True
    assert d3["interpreted"]["type"] == "expense"
    assert Decimal(str(d3["interpreted"]["amount"])) == Decimal("1200.00")
    assert d3["interpreted"]["category"] == "Utilities & Bills"
    expected_yesterday = str(date.today() - timedelta(days=1))
    assert str(d3["interpreted"]["transaction_date"]) == expected_yesterday
