from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, Date
from sqlalchemy.sql import func
from app.core.database import Base

ASSET_CATEGORIES = [
    "equities",
    "fixed_income",
    "cash_equivalents",
    "real_estate",
    "commodities",
    "alternatives",
    "crypto",
]

ASSET_CATEGORY_LABELS = {
    "equities":         "Equities (Stocks)",
    "fixed_income":     "Fixed Income (Bonds)",
    "cash_equivalents": "Cash & Cash Equivalents",
    "real_estate":      "Real Estate",
    "commodities":      "Commodities",
    "alternatives":     "Alternative Investments",
    "crypto":           "Cryptocurrencies",
}


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Identity
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    ticker_symbol = Column(String(20))          # AAPL, BTC, XAU etc.
    currency = Column(String(10), default="USD")

    # Purchase
    purchase_date = Column(Date, nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False, default=1)
    purchase_price_per_unit = Column(Numeric(20, 4), nullable=False)  # price at purchase

    # Current valuation (user updates manually or auto-fetched later)
    current_price_per_unit = Column(Numeric(20, 4), nullable=False)   # latest known price
    last_price_updated = Column(DateTime(timezone=True))

    # Location details
    location = Column(String(255))       # "HBL Bank", "Binance", "DHA Phase 5", "Home Safe"
    location_detail = Column(Text)       # account no, wallet addr, property address, etc.

    # Notes
    notes = Column(Text)
    is_active = Column(Boolean, default=True)  # False = sold/closed

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))  # soft delete
