"""Bank account Pydantic v2 schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.account import ACCOUNT_TYPES


class BankAccountCreate(BaseModel):
    account_name: str = Field(..., min_length=1, max_length=255)
    bank_name: str = Field(..., min_length=1, max_length=255)
    account_number: Optional[str] = Field(None, max_length=100)
    account_type: str
    balance: Decimal = Field(default=Decimal("0.00"))
    currency: str = Field(default="USD", min_length=3, max_length=3)
    credit_limit: Optional[Decimal] = Field(None, ge=0)
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    purpose: Optional[str] = None
    notes: Optional[str] = None
    is_primary: bool = False

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, v: str) -> str:
        if v not in ACCOUNT_TYPES:
            raise ValueError(f"account_type must be one of: {ACCOUNT_TYPES}")
        return v

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()


class BankAccountUpdate(BaseModel):
    account_name: Optional[str] = Field(None, min_length=1, max_length=255)
    balance: Optional[Decimal] = None
    credit_limit: Optional[Decimal] = Field(None, ge=0)
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    purpose: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None


class BankAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    account_name: str
    bank_name: str
    account_number: Optional[str] = None
    account_type: str
    balance: Decimal
    currency: str
    credit_limit: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    is_primary: bool
    last_synced: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Enriched in API layer
    statement_count: Optional[int] = None
    latest_statement_date: Optional[str] = None


class BankAccountListResponse(BaseModel):
    accounts: List[BankAccountResponse]
    total: int
    summary: Dict[str, Any]


class AccountDeleteResponse(BaseModel):
    message: str
    deleted_account_id: int
    statements_deleted: int
