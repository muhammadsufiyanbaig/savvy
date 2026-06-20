from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator


# ── Requests ──────────────────────────────────────────────────────────────────

class InvestmentRequest(BaseModel):
    user_id: int
    available_amount: float
    risk_tolerance: str = "medium"
    time_horizon: str = "long"
    country: str = "USA"
    city: Optional[str] = None
    shariah_compliant: bool = False
    preferred_sectors: List[str] = []

    @field_validator("risk_tolerance")
    @classmethod
    def valid_risk(cls, v: str) -> str:
        if v not in ("low", "medium", "high"):
            return "medium"
        return v

    @field_validator("time_horizon")
    @classmethod
    def valid_horizon(cls, v: str) -> str:
        if v not in ("short", "medium", "long"):
            return "long"
        return v


class ShariahInvestmentRequest(BaseModel):
    user_id: int
    available_amount: float
    country: str = "USA"
    risk_tolerance: str = "low"


# ── Response objects ──────────────────────────────────────────────────────────

class Investment(BaseModel):
    id: str
    investment_type: str
    asset_name: str
    asset_symbol: Optional[str] = None
    recommended_amount: float
    current_price: Optional[float] = None
    target_price: Optional[float] = None
    expected_return: float
    risk_level: str
    time_horizon: str
    is_shariah_compliant: bool = False
    sector: Optional[str] = None
    analysis: str
    pros: List[str] = []
    cons: List[str] = []
    confidence_score: float = 0.0


class MarketSummary(BaseModel):
    trend: str = "neutral"
    sp500_ytd: float = 0.0
    recommendation_basis: str = ""


class InvestmentResponse(BaseModel):
    investments: List[Investment]
    market_summary: MarketSummary
    generated_at: str
    total_count: int


class ShariahInvestmentResponse(BaseModel):
    investments: List[Investment]
    shariah_screening_note: str
    excluded_categories: List[str]
    generated_at: str
