from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ZakatCalculationRequest(BaseModel):
    calculation_date: date
    hijri_year: Optional[str] = None
    # Assets
    cash_in_hand: Decimal = Field(0, ge=0)
    bank_balance: Decimal = Field(0, ge=0)
    gold_value: Decimal = Field(0, ge=0)
    silver_value: Decimal = Field(0, ge=0)
    investments: Decimal = Field(0, ge=0)
    business_assets: Decimal = Field(0, ge=0)
    receivables: Decimal = Field(0, ge=0)
    other_assets: Decimal = Field(0, ge=0)
    # Liabilities
    immediate_debts: Decimal = Field(0, ge=0)
    other_liabilities: Decimal = Field(0, ge=0)
    # Reference
    nisab_threshold: Decimal = Field(..., gt=0)
    currency: str = "USD"
    notes: Optional[str] = None


class ZakatPaymentUpdate(BaseModel):
    amount_paid: Decimal = Field(..., gt=0)
    payment_date: date
    payment_status: str  # pending | partially_paid | paid


class ZakatRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    calculation_date: date
    hijri_year: Optional[str] = None
    # Assets
    cash_in_hand: Decimal
    bank_balance: Decimal
    gold_value: Decimal
    silver_value: Decimal
    investments: Decimal
    business_assets: Decimal
    receivables: Decimal
    other_assets: Decimal
    total_assets: Decimal
    # Liabilities
    immediate_debts: Decimal
    other_liabilities: Decimal
    total_liabilities: Decimal
    # Results
    zakatable_amount: Decimal
    nisab_threshold: Decimal
    nisab_met: bool
    zakat_rate: Decimal
    zakat_due: Decimal
    # Payment
    payment_status: str
    amount_paid: Decimal
    payment_date: Optional[date] = None
    currency: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ZakatListResponse(BaseModel):
    records: List[ZakatRecordResponse]
    total: int
    summary: Dict[str, Any]


class NisabResponse(BaseModel):
    date: date
    currency: str
    gold_nisab: Dict[str, Any]
    silver_nisab: Dict[str, Any]
    recommended_nisab: str
    threshold: float
    note: str
