from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SpendingLimitCreate(BaseModel):
    daily_limit: Optional[Decimal] = Field(None, gt=0)
    weekly_limit: Optional[Decimal] = Field(None, gt=0)
    monthly_limit: Optional[Decimal] = Field(None, gt=0)
    currency: str = "USD"
    alert_on_approach: bool = True
    alert_on_exceed: bool = True


class SpendingLimitUpdate(BaseModel):
    daily_limit: Optional[Decimal] = Field(None, gt=0)
    weekly_limit: Optional[Decimal] = Field(None, gt=0)
    monthly_limit: Optional[Decimal] = Field(None, gt=0)
    alert_on_approach: Optional[bool] = None
    alert_on_exceed: Optional[bool] = None


class SpendingLimitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    daily_limit: Optional[Decimal] = None
    weekly_limit: Optional[Decimal] = None
    monthly_limit: Optional[Decimal] = None
    currency: str
    daily_spent: Decimal
    weekly_spent: Decimal
    monthly_spent: Decimal
    daily_reset_date: Optional[date] = None
    weekly_reset_date: Optional[date] = None
    monthly_reset_date: Optional[date] = None
    alert_on_approach: bool
    alert_on_exceed: bool
    ai_recommended: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class SpendingLimitStatusResponse(BaseModel):
    daily_limit: Optional[float] = None
    weekly_limit: Optional[float] = None
    monthly_limit: Optional[float] = None
    daily_spent: float
    weekly_spent: float
    monthly_spent: float
    daily_remaining: Optional[float] = None
    weekly_remaining: Optional[float] = None
    monthly_remaining: Optional[float] = None
    daily_percentage: Optional[float] = None
    weekly_percentage: Optional[float] = None
    monthly_percentage: Optional[float] = None
    alerts: List[Dict[str, Any]]
