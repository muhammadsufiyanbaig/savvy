from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.liability import LIABILITY_CATEGORIES


class LiabilityCreate(BaseModel):
    name:               str = Field(..., min_length=1, max_length=255)
    category:           str
    currency:           str = "USD"
    original_amount:    Optional[Decimal] = Field(None, ge=0)
    amount_owed:        Decimal = Field(..., ge=0)
    monthly_payment:    Optional[Decimal] = Field(None, ge=0)
    due_date:           Optional[date] = None
    lender:             Optional[str] = None
    is_interest_bearing: bool = False
    notes:              Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in LIABILITY_CATEGORIES:
            raise ValueError(f"category must be one of: {LIABILITY_CATEGORIES}")
        return v

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()


class LiabilityUpdate(BaseModel):
    name:               Optional[str] = Field(None, min_length=1, max_length=255)
    amount_owed:        Optional[Decimal] = Field(None, ge=0)
    monthly_payment:    Optional[Decimal] = Field(None, ge=0)
    due_date:           Optional[date] = None
    lender:             Optional[str] = None
    is_interest_bearing: Optional[bool] = None
    notes:              Optional[str] = None
    is_active:          Optional[bool] = None


class LiabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 int
    user_id:            int
    name:               str
    category:           str
    currency:           str
    original_amount:    Optional[Decimal] = None
    amount_owed:        Decimal
    monthly_payment:    Optional[Decimal] = None
    due_date:           Optional[date] = None
    lender:             Optional[str] = None
    is_interest_bearing: bool
    notes:              Optional[str] = None
    is_active:          bool
    created_at:         datetime


class LiabilityListResponse(BaseModel):
    liabilities: List[LiabilityResponse]
    total:       int


class NetWorthResponse(BaseModel):
    total_assets:        float
    total_liabilities:   float
    net_worth:           float
    assets_by_category:  List[dict]
    liabilities_by_category: List[dict]
    riba_debt_total:     float
    halal_debt_total:    float
