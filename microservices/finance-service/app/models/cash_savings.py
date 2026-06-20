from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Date, JSON
from sqlalchemy.sql import func
from app.core.database import Base

CASH_LOCATIONS = ["home_safe", "wallet", "piggy_bank", "hidden", "other"]
CASH_PURPOSES = ["emergency", "daily_use", "savings", "specific_goal", "other"]


class CashSavings(Base):
    __tablename__ = "cash_savings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="USD")

    location = Column(String(255), index=True)       # home_safe, wallet, etc.
    location_description = Column(Text)

    description = Column(Text)
    purpose = Column(String(100), index=True)         # emergency, daily_use, etc.

    last_counted_date = Column(Date)
    denomination_breakdown = Column(JSON)             # {"100": 5, "50": 3, ...}

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
