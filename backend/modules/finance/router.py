"""
FastAPI router for the Finance Tracker module.
Exposes transaction CRUD, dashboard metrics, and natural-language draft interpretation.
"""
from typing import Optional, List
from datetime import date
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas import StandardResponse, ModulePlaceholderResponse
from backend.modules.finance.models import TransactionType
from backend.modules.finance.schemas import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    PaginatedTransactionsResponse,
    FinanceDashboardSummary,
    NaturalLanguageParseRequest,
    NaturalLanguageParseResponse,
    STANDARD_CATEGORIES,
    STANDARD_PAYMENT_METHODS,
)
from backend.modules.finance import service

router = APIRouter(prefix="/finance", tags=["Finance Tracker"])


@router.get("", response_model=StandardResponse[ModulePlaceholderResponse])
def get_finance_module_info():
    """Module status information endpoint."""
    return StandardResponse(
        success=True,
        data=ModulePlaceholderResponse(
            module="finance",
            status="active",
            message="Finance Tracker module active. Supports transaction CRUD, SQL metrics, and natural-language entry.",
            capabilities_planned=[
                "Income and expense tracking with NUMERIC precision",
                "Authoritative dashboard calculations (monthly totals & net balance)",
                "Category-wise spending breakdown",
                "Natural-language parsing with confirmation workflow",
            ],
        ),
    )


@router.get("/categories", response_model=StandardResponse[List[str]])
def get_categories():
    """Retrieve list of standard expense and income categories."""
    return StandardResponse(success=True, data=STANDARD_CATEGORIES)


@router.get("/payment-methods", response_model=StandardResponse[List[str]])
def get_payment_methods():
    """Retrieve list of supported payment methods."""
    return StandardResponse(success=True, data=STANDARD_PAYMENT_METHODS)


@router.get("/dashboard", response_model=StandardResponse[FinanceDashboardSummary])
def get_dashboard(
    period_start: Optional[date] = Query(None, description="Start date for summary period (YYYY-MM-DD)"),
    period_end: Optional[date] = Query(None, description="End date for summary period (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Get financial dashboard metrics.
    All monetary totals and category percentages are computed deterministically via SQL.
    """
    if period_start and period_end and period_start > period_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_start cannot be after period_end",
        )

    summary = service.get_dashboard_summary(db, period_start=period_start, period_end=period_end)
    return StandardResponse(success=True, data=summary)


@router.post("/transactions", response_model=StandardResponse[TransactionResponse], status_code=status.HTTP_201_CREATED)
def create_transaction_endpoint(
    transaction_in: TransactionCreate,
    db: Session = Depends(get_db),
):
    """Create a new income or expense transaction."""
    created = service.create_transaction(db, transaction_in)
    return StandardResponse(
        success=True,
        data=TransactionResponse.model_validate(created),
    )


@router.get("/transactions", response_model=StandardResponse[PaginatedTransactionsResponse])
def list_transactions_endpoint(
    start_date: Optional[date] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (inclusive)"),
    type: Optional[TransactionType] = Query(None, description="Filter by 'income' or 'expense'"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """List filtered, paginated transactions."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date",
        )

    items, total = service.list_transactions(
        db,
        start_date=start_date,
        end_date=end_date,
        type_=type,
        category=category,
        page=page,
        page_size=page_size,
    )

    total_pages = ceil(total / page_size) if total > 0 else 1
    items_pydantic = [TransactionResponse.model_validate(i) for i in items]

    return StandardResponse(
        success=True,
        data=PaginatedTransactionsResponse(
            items=items_pydantic,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get("/transactions/{transaction_id}", response_model=StandardResponse[TransactionResponse])
def get_transaction_endpoint(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve transaction details by ID."""
    tx = service.get_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found",
        )
    return StandardResponse(
        success=True,
        data=TransactionResponse.model_validate(tx),
    )


@router.put("/transactions/{transaction_id}", response_model=StandardResponse[TransactionResponse])
def update_transaction_endpoint(
    transaction_id: int,
    transaction_in: TransactionUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing transaction."""
    updated = service.update_transaction(db, transaction_id, transaction_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found",
        )
    return StandardResponse(
        success=True,
        data=TransactionResponse.model_validate(updated),
    )


@router.delete("/transactions/{transaction_id}", response_model=StandardResponse[dict])
def delete_transaction_endpoint(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """Delete a transaction by ID."""
    deleted = service.delete_transaction(db, transaction_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found",
        )
    return StandardResponse(
        success=True,
        data={"deleted": True, "id": transaction_id},
    )


@router.post("/parse-natural-language", response_model=StandardResponse[NaturalLanguageParseResponse])
def parse_natural_language_endpoint(
    request: NaturalLanguageParseRequest,
):
    """
    Interpret a natural-language transaction entry.
    Returns a structured draft with requires_confirmation=True for user validation.
    """
    parsed = service.parse_natural_language_input(request.text)
    return StandardResponse(
        success=True,
        data=parsed,
    )
