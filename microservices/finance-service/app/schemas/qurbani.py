from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.qurbani import ANIMAL_TYPES, QURBANI_STATUSES


class QurbaniSavingsCreate(BaseModel):
    target_year: int = Field(..., ge=2020, le=2100)
    hijri_year: Optional[str] = None
    target_amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    animal_type: Optional[str] = None
    animal_shares: int = Field(1, ge=1, le=7)
    estimated_cost_per_share: Optional[Decimal] = Field(None, gt=0)
    monthly_contribution: Optional[Decimal] = Field(None, gt=0)
    auto_save_enabled: bool = False
    group_purchase: bool = False
    notes: Optional[str] = None

    @field_validator("animal_type")
    @classmethod
    def validate_animal(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ANIMAL_TYPES:
            raise ValueError(f"animal_type must be one of: {ANIMAL_TYPES}")
        return v


class QurbaniSavingsUpdate(BaseModel):
    target_amount: Optional[Decimal] = Field(None, gt=0)
    animal_type: Optional[str] = None
    animal_shares: Optional[int] = Field(None, ge=1, le=7)
    estimated_cost_per_share: Optional[Decimal] = Field(None, gt=0)
    monthly_contribution: Optional[Decimal] = Field(None, gt=0)
    auto_save_enabled: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in QURBANI_STATUSES:
            raise ValueError(f"status must be one of: {QURBANI_STATUSES}")
        return v


class QurbaniContributeRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None


class QurbaniSavingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    target_year: int
    hijri_year: Optional[str] = None
    target_amount: Decimal
    current_amount: Decimal
    progress: Decimal
    currency: str
    animal_type: Optional[str] = None
    animal_shares: int
    estimated_cost_per_share: Optional[Decimal] = None
    monthly_contribution: Optional[Decimal] = None
    auto_save_enabled: bool
    status: str
    completed_date: Optional[date] = None
    group_purchase: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class QurbaniListResponse(BaseModel):
    savings: List[QurbaniSavingsResponse]
    total: int
    summary: Dict[str, Any]
