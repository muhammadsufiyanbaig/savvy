from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CashSavingsCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    location: Optional[str] = None
    location_description: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    last_counted_date: Optional[date] = None
    denomination_breakdown: Optional[Dict[str, int]] = None

    @classmethod
    def _upper_currency(cls, v: str) -> str:
        return v.upper()


class CashSavingsUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = None
    location: Optional[str] = None
    location_description: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    last_counted_date: Optional[date] = None
    denomination_breakdown: Optional[Dict[str, int]] = None


class CashSavingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    amount: Decimal
    currency: str
    location: Optional[str] = None
    location_description: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    last_counted_date: Optional[date] = None
    denomination_breakdown: Optional[Dict[str, int]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class CashSavingsListResponse(BaseModel):
    cash_savings: List[CashSavingsResponse]
    total: int
    summary: Dict[str, Any]
