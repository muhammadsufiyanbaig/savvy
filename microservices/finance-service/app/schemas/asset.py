from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.models.asset import ASSET_CATEGORIES


class AssetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str
    ticker_symbol: Optional[str] = None
    currency: str = "USD"
    purchase_date: date
    quantity: Decimal = Field(..., gt=0)
    purchase_price_per_unit: Decimal = Field(..., ge=0)
    current_price_per_unit: Decimal = Field(..., ge=0)
    location: Optional[str] = None
    location_detail: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in ASSET_CATEGORIES:
            raise ValueError(f"category must be one of: {ASSET_CATEGORIES}")
        return v

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()

    @field_validator("purchase_date")
    @classmethod
    def purchase_date_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("purchase_date cannot be in the future")
        return v


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    ticker_symbol: Optional[str] = None
    quantity: Optional[Decimal] = Field(None, gt=0)
    current_price_per_unit: Optional[Decimal] = Field(None, ge=0)
    purchase_price_per_unit: Optional[Decimal] = Field(None, ge=0)
    purchase_date: Optional[date] = None
    location: Optional[str] = None
    location_detail: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    category: str
    ticker_symbol: Optional[str] = None
    currency: str
    purchase_date: date
    quantity: Decimal
    purchase_price_per_unit: Decimal
    current_price_per_unit: Decimal
    last_price_updated: Optional[datetime] = None
    location: Optional[str] = None
    location_detail: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Computed fields (populated in endpoint)
    purchase_value: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    gain_loss: Optional[Decimal] = None
    gain_loss_pct: Optional[float] = None


class AssetListResponse(BaseModel):
    assets: List[AssetResponse]
    total: int


class CategoryBreakdown(BaseModel):
    category: str
    label: str
    count: int
    current_value: float
    purchase_value: float
    gain_loss: float
    gain_loss_pct: float
    percentage_of_portfolio: float


class YearlySnapshot(BaseModel):
    year: int
    total_value: float
    total_invested: float
    gain_loss: float
    gain_loss_pct: float


class AssetAnalytics(BaseModel):
    total_current_value: float
    total_purchase_value: float
    total_gain_loss: float
    total_gain_loss_pct: float
    total_assets: int
    active_assets: int
    by_category: List[CategoryBreakdown]
    yearly_growth: List[YearlySnapshot]
    top_performer: Optional[Dict] = None
    worst_performer: Optional[Dict] = None
