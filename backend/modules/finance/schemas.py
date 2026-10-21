"""
Pydantic schemas for the Finance Tracker module.
Enforces strict monetary and date validation.
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from backend.modules.finance.models import TransactionType

# Standard categories for clean suggestions
STANDARD_CATEGORIES = [
    "Food & Dining",
    "Groceries",
    "Housing & Rent",
    "Utilities & Bills",
    "Transportation",
    "Shopping",
    "Healthcare",
    "Entertainment",
    "Education",
    "Salary",
    "Freelance & Consulting",
    "Investments",
    "Gifts & Donations",
    "Other",
]

# Standard payment methods
STANDARD_PAYMENT_METHODS = [
    "UPI",
    "Credit Card",
    "Debit Card",
    "Net Banking",
    "Cash",
    "Other",
]


class TransactionBase(BaseModel):
    """Base transaction fields shared across create, update, and response."""
    type: TransactionType = Field(..., description="'income' or 'expense'")
    amount: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        max_digits=12,
        description="Transaction amount in INR. Must be greater than zero.",
    )
    category: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: str = Field(..., min_length=1, max_length=255, description="Brief description")
    transaction_date: date = Field(default_factory=date.today, description="Date of transaction (YYYY-MM-DD)")
    payment_method: str = Field(default="UPI", min_length=1, max_length=50, description="Payment method used")
    notes: Optional[str] = Field(default=None, max_length=1000, description="Optional notes")

    @field_validator("category", "description", "payment_method")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Field cannot be empty or whitespace only.")
            return v_stripped
        return v

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: Decimal) -> Decimal:
        return round(v, 2)


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""
    pass


class TransactionUpdate(BaseModel):
    """Schema for updating an existing transaction (partial updates supported)."""
    type: Optional[TransactionType] = None
    amount: Optional[Decimal] = Field(default=None, gt=Decimal("0.00"), decimal_places=2, max_digits=12)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, min_length=1, max_length=255)
    transaction_date: Optional[date] = None
    payment_method: Optional[str] = Field(default=None, min_length=1, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("category", "description", "payment_method")
    @classmethod
    def strip_whitespace_if_set(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Field cannot be empty or whitespace only.")
            return v_stripped
        return v


class TransactionResponse(TransactionBase):
    """Schema for transaction API responses."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedTransactionsResponse(BaseModel):
    """Paginated collection of transactions."""
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CategorySummary(BaseModel):
    """Category-wise spending distribution."""
    category: str
    total_amount: Decimal
    transaction_count: int
    percentage_of_total: float


class FinanceDashboardSummary(BaseModel):
    """Dashboard aggregate summary with authoritative, deterministic database totals."""
    currency_symbol: str = "₹"
    # This month (current calendar month)
    total_income_this_month: Decimal
    total_expenses_this_month: Decimal
    net_balance_this_month: Decimal

    # Selected period (defaults to current month or custom filter)
    period_start: date
    period_end: date
    period_total_income: Decimal
    period_total_expenses: Decimal
    period_net_balance: Decimal

    # Visual breakdown & recent items
    category_breakdown: List[CategorySummary]
    recent_transactions: List[TransactionResponse]


class NaturalLanguageParseRequest(BaseModel):
    """User input string containing natural-language expense or income statement."""
    text: str = Field(..., min_length=2, max_length=500, description="Sentence to interpret")


class NaturalLanguageParseResponse(BaseModel):
    """
    Extracted draft transaction.
    Requires explicit user confirmation before persisting to the database.
    """
    interpreted: TransactionCreate
    confidence: float
    raw_text: str
    parsed_elements: Dict[str, Any]
    requires_confirmation: bool = Field(default=True, description="Always true: user must confirm before saving")
    message: str
