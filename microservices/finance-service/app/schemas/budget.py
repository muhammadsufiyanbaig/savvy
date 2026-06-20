from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.models.budget import BUDGET_PERIODS


class BudgetCreate(BaseModel):
    category: str
    allocated_amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    period: str
    period_start_date: date
    period_end_date: date
    alert_threshold: Decimal = Field(80.00, ge=0, le=100)
    rollover_enabled: bool = False

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        if v not in BUDGET_PERIODS:
            raise ValueError(f"period must be one of: {BUDGET_PERIODS}")
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "BudgetCreate":
        if self.period_end_date < self.period_start_date:
            raise ValueError("period_end_date must be >= period_start_date")
        return self


class BudgetUpdate(BaseModel):
    allocated_amount: Optional[Decimal] = Field(None, gt=0)
    alert_threshold: Optional[Decimal] = Field(None, ge=0, le=100)
    rollover_enabled: Optional[bool] = None
    status: Optional[str] = None


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category: str
    allocated_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Optional[Decimal] = None
    currency: str
    period: str
    period_start_date: date
    period_end_date: date
    alert_threshold: Decimal
    alert_sent: bool
    status: str
    exceeded: bool
    ai_recommended: bool
    rollover_enabled: bool
    rollover_amount: Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None


class BudgetListResponse(BaseModel):
    budgets: List[BudgetResponse]
    total: int
    summary: Dict[str, Any]


class BudgetStatusResponse(BaseModel):
    period: str
    period_start: date
    period_end: date
    days_elapsed: int
    days_remaining: int
    total_allocated: float
    total_spent: float
    total_remaining: float
    percentage_used: float
    daily_average_spent: float
    recommended_daily_spend: float
    on_track: bool
    categories: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]
