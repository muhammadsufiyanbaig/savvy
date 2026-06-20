from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.expense import (
    EXPENSE_CATEGORIES, EXPENSE_TYPES, PAYMENT_METHODS, RECURRENCE_PATTERNS,
)


class ExpenseCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    category: str
    expense_type: str
    description: Optional[str] = None
    merchant_name: Optional[str] = None
    payment_method: Optional[str] = None
    transaction_date: datetime
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    recurrence_day: Optional[int] = Field(None, ge=1, le=31)
    tags: List[str] = []
    created_from: str = "manual"
    receipt_image_url: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of: {EXPENSE_CATEGORIES}")
        return v

    @field_validator("expense_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in EXPENSE_TYPES:
            raise ValueError(f"expense_type must be one of: {EXPENSE_TYPES}")
        return v

    @field_validator("payment_method")
    @classmethod
    def validate_payment(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of: {PAYMENT_METHODS}")
        return v

    @field_validator("recurrence_pattern")
    @classmethod
    def validate_recurrence(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in RECURRENCE_PATTERNS:
            raise ValueError(f"recurrence_pattern must be one of: {RECURRENCE_PATTERNS}")
        return v

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()


class ExpenseUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = None
    category: Optional[str] = None
    expense_type: Optional[str] = None
    description: Optional[str] = None
    merchant_name: Optional[str] = None
    payment_method: Optional[str] = None
    transaction_date: Optional[datetime] = None
    tags: Optional[List[str]] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of: {EXPENSE_CATEGORIES}")
        return v


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    amount: Decimal
    currency: str
    category: str
    expense_type: str
    description: Optional[str] = None
    merchant_name: Optional[str] = None
    payment_method: Optional[str] = None
    transaction_date: datetime
    is_recurring: bool
    recurrence_pattern: Optional[str] = None
    recurrence_day: Optional[int] = None
    next_occurrence_date: Optional[date] = None
    tags: Optional[List[str]] = []
    created_from: str
    receipt_image_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ExpenseListResponse(BaseModel):
    expenses: List[ExpenseResponse]
    total: int
    limit: int
    offset: int
    summary: Dict[str, Any]


class ExpenseSummaryResponse(BaseModel):
    period: str
    start_date: date
    end_date: date
    total_expenses: float
    currency: str
    expense_count: int
    average_expense: float
    by_category: Dict[str, Any]
    by_type: Dict[str, Any]
    by_payment_method: Dict[str, Any]
    recurring_expenses: Dict[str, Any]


class CategoryInfo(BaseModel):
    name: str
    icon: str
    color: str
    description: str
