"""
SQLAlchemy models for the Finance Tracker module.
"""
import enum
from datetime import datetime, date, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    DateTime,
    Text,
    Enum as SQLEnum,
    CheckConstraint,
    Index,
)
from backend.core.database import Base


class TransactionType(str, enum.Enum):
    """Transaction type enumeration: income or expense."""
    INCOME = "income"
    EXPENSE = "expense"


class FinanceTransaction(Base):
    """
    Financial transaction model storing incomes and expenses.
    Monetary amounts use PostgreSQL NUMERIC(12, 2) for exact decimal math.
    """
    __tablename__ = "finance_transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    type = Column(SQLEnum(TransactionType, name="transaction_type_enum"), nullable=False, index=True)
    amount = Column(Numeric(precision=12, scale=2), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    transaction_date = Column(Date, nullable=False, default=date.today, index=True)
    payment_method = Column(String(50), nullable=False, default="UPI")
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
        CheckConstraint("amount > 0", name="check_positive_amount"),
        Index("ix_finance_tx_date_type", "transaction_date", "type"),
    )
