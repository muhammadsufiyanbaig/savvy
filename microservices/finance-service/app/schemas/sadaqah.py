from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.sadaqah import SADAQAH_CATEGORIES


class SadaqahCreate(BaseModel):
    amount:    Decimal = Field(..., gt=0)
    currency:  str = "USD"
    category:  str
    recipient: Optional[str] = None
    date:      date
    notes:     Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in SADAQAH_CATEGORIES:
            raise ValueError(f"category must be one of: {SADAQAH_CATEGORIES}")
        return v

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()

    @field_validator("date")
    @classmethod
    def not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("date cannot be in the future")
        return v


class SadaqahUpdate(BaseModel):
    amount:    Optional[Decimal] = Field(None, gt=0)
    currency:  Optional[str] = None
    category:  Optional[str] = None
    recipient: Optional[str] = None
    date:      Optional[date] = None
    notes:     Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is not None and v not in SADAQAH_CATEGORIES:
            raise ValueError(f"category must be one of: {SADAQAH_CATEGORIES}")
        return v


class SadaqahResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         int
    user_id:    int
    amount:     Decimal
    currency:   str
    category:   str
    recipient:  Optional[str] = None
    date:       date
    notes:      Optional[str] = None
    created_at: datetime


class SadaqahListResponse(BaseModel):
    records: List[SadaqahResponse]
    total:   int


class CategoryTotal(BaseModel):
    category: str
    label:    str
    total:    float
    count:    int


class SadaqahSummary(BaseModel):
    total_all_time:    float
    total_this_year:   float
    total_this_month:  float
    by_category:       List[CategoryTotal]
    monthly_trend:     List[dict]   # [{month, total}]
