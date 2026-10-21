"""
Service layer for the Finance Tracker module.
Executes deterministic SQL aggregations, transaction CRUD, and natural-language parsing.
"""
from typing import Optional, List, Tuple, Dict, Any
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import calendar
import re
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from backend.modules.finance.models import FinanceTransaction, TransactionType
from backend.modules.finance.schemas import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    CategorySummary,
    FinanceDashboardSummary,
    NaturalLanguageParseResponse,
    STANDARD_CATEGORIES,
    STANDARD_PAYMENT_METHODS,
)


def create_transaction(db: Session, data: TransactionCreate) -> FinanceTransaction:
    """Create and persist a new financial transaction."""
    tx = FinanceTransaction(
        type=data.type,
        amount=data.amount,
        category=data.category,
        description=data.description,
        transaction_date=data.transaction_date,
        payment_method=data.payment_method,
        notes=data.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def get_transaction(db: Session, transaction_id: int) -> Optional[FinanceTransaction]:
    """Retrieve transaction by ID."""
    return db.query(FinanceTransaction).filter(FinanceTransaction.id == transaction_id).first()


def update_transaction(
    db: Session, transaction_id: int, data: TransactionUpdate
) -> Optional[FinanceTransaction]:
    """Partially or fully update an existing transaction."""
    tx = get_transaction(db, transaction_id)
    if not tx:
        return None

    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(tx, field, value)

    tx.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, transaction_id: int) -> bool:
    """Delete a transaction by ID. Returns True if deleted, False if not found."""
    tx = get_transaction(db, transaction_id)
    if not tx:
        return False
    db.delete(tx)
    db.commit()
    return True


def list_transactions(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    type_: Optional[TransactionType] = None,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[FinanceTransaction], int]:
    """
    List filtered, paginated transactions ordered by date descending.
    Returns (items, total_count).
    """
    query = db.query(FinanceTransaction)

    if start_date:
        query = query.filter(FinanceTransaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(FinanceTransaction.transaction_date <= end_date)
    if type_:
        query = query.filter(FinanceTransaction.type == type_)
    if category:
        query = query.filter(FinanceTransaction.category == category)

    total_count = query.count()

    # Pagination
    offset = max(0, (page - 1) * page_size)
    items = (
        query.order_by(
            FinanceTransaction.transaction_date.desc(),
            FinanceTransaction.id.desc(),
        )
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return items, total_count


def get_dashboard_summary(
    db: Session,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
) -> FinanceDashboardSummary:
    """
    Compute authoritative, deterministic dashboard metrics.
    Monetary totals are calculated directly via SQL sum aggregations.
    """
    today = date.today()

    # Current calendar month boundaries
    month_start = today.replace(day=1)
    _, last_day = calendar.monthrange(today.year, today.month)
    month_end = today.replace(day=last_day)

    # 1. Authoritative calculations for current calendar month
    month_income = db.query(
        func.coalesce(func.sum(FinanceTransaction.amount), Decimal("0.00"))
    ).filter(
        FinanceTransaction.type == TransactionType.INCOME,
        FinanceTransaction.transaction_date >= month_start,
        FinanceTransaction.transaction_date <= month_end,
    ).scalar() or Decimal("0.00")

    month_expenses = db.query(
        func.coalesce(func.sum(FinanceTransaction.amount), Decimal("0.00"))
    ).filter(
        FinanceTransaction.type == TransactionType.EXPENSE,
        FinanceTransaction.transaction_date >= month_start,
        FinanceTransaction.transaction_date <= month_end,
    ).scalar() or Decimal("0.00")

    month_net = Decimal(month_income) - Decimal(month_expenses)

    # 2. Selected period boundaries (defaults to current month if not specified)
    effective_start = period_start or month_start
    effective_end = period_end or month_end

    period_income = db.query(
        func.coalesce(func.sum(FinanceTransaction.amount), Decimal("0.00"))
    ).filter(
        FinanceTransaction.type == TransactionType.INCOME,
        FinanceTransaction.transaction_date >= effective_start,
        FinanceTransaction.transaction_date <= effective_end,
    ).scalar() or Decimal("0.00")

    period_expenses = db.query(
        func.coalesce(func.sum(FinanceTransaction.amount), Decimal("0.00"))
    ).filter(
        FinanceTransaction.type == TransactionType.EXPENSE,
        FinanceTransaction.transaction_date >= effective_start,
        FinanceTransaction.transaction_date <= effective_end,
    ).scalar() or Decimal("0.00")

    period_net = Decimal(period_income) - Decimal(period_expenses)

    # 3. Category breakdown for expenses in selected period
    cat_query = db.query(
        FinanceTransaction.category,
        func.sum(FinanceTransaction.amount).label("total_amt"),
        func.count(FinanceTransaction.id).label("tx_count"),
    ).filter(
        FinanceTransaction.type == TransactionType.EXPENSE,
        FinanceTransaction.transaction_date >= effective_start,
        FinanceTransaction.transaction_date <= effective_end,
    ).group_by(
        FinanceTransaction.category
    ).order_by(
        desc("total_amt")
    ).all()

    category_summaries: List[CategorySummary] = []
    total_exp_decimal = Decimal(period_expenses)

    for cat_name, cat_total, cat_count in cat_query:
        amt = Decimal(cat_total)
        pct = float(round((amt / total_exp_decimal) * 100, 1)) if total_exp_decimal > 0 else 0.0
        category_summaries.append(
            CategorySummary(
                category=cat_name,
                total_amount=round(amt, 2),
                transaction_count=cat_count,
                percentage_of_total=pct,
            )
        )

    # 4. Recent transactions (latest 5 across all types)
    recent_records = (
        db.query(FinanceTransaction)
        .order_by(FinanceTransaction.transaction_date.desc(), FinanceTransaction.id.desc())
        .limit(5)
        .all()
    )

    recent_pydantic = [
        TransactionResponse.model_validate(tx) for tx in recent_records
    ]

    return FinanceDashboardSummary(
        currency_symbol="₹",
        total_income_this_month=round(Decimal(month_income), 2),
        total_expenses_this_month=round(Decimal(month_expenses), 2),
        net_balance_this_month=round(Decimal(month_net), 2),
        period_start=effective_start,
        period_end=effective_end,
        period_total_income=round(Decimal(period_income), 2),
        period_total_expenses=round(Decimal(period_expenses), 2),
        period_net_balance=round(Decimal(period_net), 2),
        category_breakdown=category_summaries,
        recent_transactions=recent_pydantic,
    )


# Heuristic Natural Language Interpretation Engine
_CATEGORY_KEYWORDS = {
    "Food & Dining": ["dinner", "lunch", "breakfast", "restaurant", "swiggy", "zomato", "cafe", "coffee", "pizza", "burger", "food", "eat", "biryani"],
    "Groceries": ["groceries", "grocery", "supermarket", "vegetables", "fruits", "milk", "bread", "ration", "blinkit", "zepto", "instamart"],
    "Housing & Rent": ["rent", "maintenance", "house", "apartment", "deposit", "flat"],
    "Utilities & Bills": ["electricity", "water", "wifi", "internet", "bill", "recharge", "gas", "cylinder", "broadband", "dth"],
    "Transportation": ["uber", "ola", "auto", "petrol", "diesel", "fuel", "flight", "ticket", "train", "metro", "bus", "cab", "parking", "toll"],
    "Shopping": ["shopping", "amazon", "flipkart", "myntra", "clothes", "shoes", "electronics", "gadget"],
    "Healthcare": ["doctor", "medicine", "pharmacy", "clinic", "hospital", "test", "dentist"],
    "Entertainment": ["movie", "cinema", "theatre", "netflix", "spotify", "prime", "game", "party", "outing"],
    "Education": ["course", "tuition", "school", "books", "class", "udemy"],
    "Salary": ["salary", "stipend", "paycheck"],
    "Freelance & Consulting": ["freelance", "client", "consulting", "gig", "contract"],
    "Investments": ["stocks", "mutual fund", "sip", "dividend", "interest", "crypto"],
}

_INCOME_KEYWORDS = {"received", "earned", "salary", "credited", "got", "income", "stipend", "refund", "freelance"}
_EXPENSE_KEYWORDS = {"spent", "paid", "bought", "purchased", "expense", "bill", "given", "debited", "ordered"}


def parse_natural_language_input(text: str) -> NaturalLanguageParseResponse:
    """
    Deterministic rule-based extractor for natural-language expense and income entries.
    Extracts:
      - Amount (handles ₹, Rs, INR, comma separators, decimals)
      - Transaction Type (income vs expense)
      - Category (via keyword clustering)
      - Date (relative terms like 'yesterday', 'today', or defaults to current date)
      - Payment method (UPI, cash, card)

    Always sets requires_confirmation=True for user validation before persisting.
    """
    clean_text = text.strip()
    lower_text = clean_text.lower()
    parsed_elements: Dict[str, Any] = {}

    # 1. Extract Amount
    # Matches patterns like: ₹180, ₹ 5,000, Rs. 1,200, 450, 75000.50
    amount_match = re.search(
        r"(?:₹|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
        lower_text,
    )
    extracted_amount = Decimal("0.00")
    if amount_match:
        raw_num = amount_match.group(1).replace(",", "")
        try:
            val = Decimal(raw_num)
            if val > 0:
                extracted_amount = round(val, 2)
                parsed_elements["raw_amount"] = amount_match.group(0)
        except Exception:
            pass

    if extracted_amount == 0:
        extracted_amount = Decimal("100.00")  # safe fallback placeholder

    # 2. Extract Type
    detected_type = TransactionType.EXPENSE
    confidence = 0.70

    is_income = any(kw in lower_text for kw in _INCOME_KEYWORDS)
    is_expense = any(kw in lower_text for kw in _EXPENSE_KEYWORDS)

    if is_income and not is_expense:
        detected_type = TransactionType.INCOME
        confidence += 0.15
    elif is_expense:
        detected_type = TransactionType.EXPENSE
        confidence += 0.15

    parsed_elements["type"] = detected_type.value

    # 3. Extract Date
    tx_date = date.today()
    if "yesterday" in lower_text:
        tx_date = tx_date - timedelta(days=1)
        parsed_elements["date_relative"] = "yesterday"
    elif "day before yesterday" in lower_text:
        tx_date = tx_date - timedelta(days=2)
        parsed_elements["date_relative"] = "day before yesterday"
    elif "today" in lower_text:
        parsed_elements["date_relative"] = "today"

    parsed_elements["transaction_date"] = str(tx_date)

    # 4. Extract Payment Method
    payment_method = "UPI"
    if "cash" in lower_text:
        payment_method = "Cash"
    elif "credit card" in lower_text:
        payment_method = "Credit Card"
    elif "debit card" in lower_text:
        payment_method = "Debit Card"
    elif "net banking" in lower_text or "netbanking" in lower_text:
        payment_method = "Net Banking"
    parsed_elements["payment_method"] = payment_method

    # 5. Extract Category
    matched_category = "Salary" if detected_type == TransactionType.INCOME and "salary" in lower_text else None
    if not matched_category and detected_type == TransactionType.INCOME:
        if any(w in lower_text for w in ["freelance", "client", "gig"]):
            matched_category = "Freelance & Consulting"
        elif any(w in lower_text for w in ["dividend", "interest", "stock", "crypto"]):
            matched_category = "Investments"
        else:
            matched_category = "Other"

    if not matched_category:
        for cat, kw_list in _CATEGORY_KEYWORDS.items():
            if any(kw in lower_text for kw in kw_list):
                matched_category = cat
                confidence += 0.10
                break

    if not matched_category:
        matched_category = "Other"

    parsed_elements["category"] = matched_category

    # 6. Extract Description
    # Look for "on <topic>", "for <topic>", "from <topic>"
    desc_match = re.search(r"\b(?:on|for|from|towards)\s+([a-zA-Z0-9\s,&'-]+?)(?:\s+(?:yesterday|today|via|by|with|\.|$))", lower_text)
    if desc_match:
        description = desc_match.group(1).strip().capitalize()
    else:
        # Fallback to cleaning up sentence
        description = clean_text[:60].capitalize()

    if len(description) < 3:
        description = f"{matched_category} entry"

    parsed_elements["description"] = description

    confidence = min(0.95, round(confidence, 2))

    interpreted_tx = TransactionCreate(
        type=detected_type,
        amount=extracted_amount,
        category=matched_category,
        description=description,
        transaction_date=tx_date,
        payment_method=payment_method,
        notes=f"Parsed from: \"{clean_text}\"",
    )

    return NaturalLanguageParseResponse(
        interpreted=interpreted_tx,
        confidence=confidence,
        raw_text=clean_text,
        parsed_elements=parsed_elements,
        requires_confirmation=True,
        message="Please review and confirm the interpreted transaction before saving.",
    )
