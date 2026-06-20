from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.hajj_umrah import PLAN_TYPES, PACKAGE_TYPES


class HajjUmrahPlanCreate(BaseModel):
    plan_type:      str
    title:          Optional[str] = None
    target_year:    int = Field(..., ge=2026)
    num_persons:    int = Field(1, ge=1, le=20)
    departure_city: Optional[str] = None
    package_type:   str = "standard"
    estimated_cost: Decimal = Field(..., gt=0)
    current_amount: Optional[Decimal] = Field(Decimal(0), ge=0)
    currency:       str = "USD"
    notes:          Optional[str] = None

    @field_validator("plan_type")
    @classmethod
    def validate_plan_type(cls, v: str) -> str:
        if v not in PLAN_TYPES:
            raise ValueError(f"plan_type must be one of: {PLAN_TYPES}")
        return v

    @field_validator("package_type")
    @classmethod
    def validate_package(cls, v: str) -> str:
        if v not in PACKAGE_TYPES:
            raise ValueError(f"package_type must be one of: {PACKAGE_TYPES}")
        return v

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()


class HajjUmrahPlanUpdate(BaseModel):
    title:          Optional[str] = None
    target_year:    Optional[int] = Field(None, ge=2024)
    num_persons:    Optional[int] = Field(None, ge=1, le=20)
    departure_city: Optional[str] = None
    package_type:   Optional[str] = None
    estimated_cost: Optional[Decimal] = Field(None, gt=0)
    notes:          Optional[str] = None
    is_active:      Optional[bool] = None


class DepositCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    note:   Optional[str] = None
    date:   date

    @field_validator("date")
    @classmethod
    def not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("date cannot be in the future")
        return v


class DepositResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    plan_id:    int
    amount:     Decimal
    note:       Optional[str] = None
    date:       date
    created_at: datetime


class HajjUmrahPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             int
    user_id:        int
    plan_type:      str
    title:          Optional[str] = None
    target_year:    int
    num_persons:    int
    departure_city: Optional[str] = None
    package_type:   str
    estimated_cost: Decimal
    current_amount: Decimal
    currency:       str
    notes:          Optional[str] = None
    is_active:      bool
    created_at:     datetime

    # Computed
    progress_pct:       float = 0.0
    remaining_amount:   Decimal = Decimal(0)
    months_remaining:   int = 0
    monthly_target:     Decimal = Decimal(0)


class HajjUmrahListResponse(BaseModel):
    plans: List[HajjUmrahPlanResponse]
    total: int
