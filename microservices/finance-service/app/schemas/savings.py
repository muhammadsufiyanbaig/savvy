from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.savings import GOAL_TYPES, GOAL_STATUSES, AUTO_DEPOSIT_FREQUENCIES, TRANSACTION_TYPES


class SavingsGoalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    goal_type: str
    description: Optional[str] = None
    target_amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    target_date: Optional[date] = None
    auto_deposit_enabled: bool = False
    auto_deposit_amount: Optional[Decimal] = Field(None, gt=0)
    auto_deposit_frequency: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    priority: int = Field(0, ge=0, le=2)

    @field_validator("goal_type")
    @classmethod
    def validate_goal_type(cls, v: str) -> str:
        if v not in GOAL_TYPES:
            raise ValueError(f"goal_type must be one of: {GOAL_TYPES}")
        return v

    @field_validator("auto_deposit_frequency")
    @classmethod
    def validate_frequency(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in AUTO_DEPOSIT_FREQUENCIES:
            raise ValueError(f"auto_deposit_frequency must be one of: {AUTO_DEPOSIT_FREQUENCIES}")
        return v

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    target_amount: Optional[Decimal] = Field(None, gt=0)
    target_date: Optional[date] = None
    status: Optional[str] = None
    auto_deposit_enabled: Optional[bool] = None
    auto_deposit_amount: Optional[Decimal] = Field(None, gt=0)
    auto_deposit_frequency: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=2)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in GOAL_STATUSES:
            raise ValueError(f"status must be one of: {GOAL_STATUSES}")
        return v


class SavingsGoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    goal_type: str
    description: Optional[str] = None
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    progress: Decimal
    target_date: Optional[date] = None
    start_date: Optional[date] = None
    completed_date: Optional[date] = None
    status: str
    auto_deposit_enabled: bool
    auto_deposit_amount: Optional[Decimal] = None
    auto_deposit_frequency: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    priority: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    source: Optional[str] = None


class WithdrawRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    goal_id: int
    amount: Decimal
    transaction_type: str
    description: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    transaction_date: datetime
    created_at: datetime


class TransactionWithGoalUpdate(BaseModel):
    transaction_id: int
    goal_id: int
    amount: Decimal
    transaction_type: str
    description: Optional[str] = None
    source: Optional[str] = None
    transaction_date: datetime
    goal_updated: Dict[str, Any]


class SavingsGoalListResponse(BaseModel):
    goals: List[SavingsGoalResponse]
    total: int
    summary: Dict[str, Any]


class TransactionListResponse(BaseModel):
    goal_id: int
    goal_name: str
    transactions: List[TransactionResponse]
    total: int
    summary: Dict[str, Any]
