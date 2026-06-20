from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date
from sqlalchemy.sql import func
from app.core.database import Base


class SpendingLimit(Base):
    __tablename__ = "spending_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)  # one per user

    # Limits (None = no limit set)
    daily_limit = Column(Numeric(15, 2))
    weekly_limit = Column(Numeric(15, 2))
    monthly_limit = Column(Numeric(15, 2))
    currency = Column(String(10), default="USD")

    # Current period spending (reset on new period)
    daily_spent = Column(Numeric(15, 2), default=0.00)
    weekly_spent = Column(Numeric(15, 2), default=0.00)
    monthly_spent = Column(Numeric(15, 2), default=0.00)

    # Last reset dates — used to detect when to auto-reset counters
    daily_reset_date = Column(Date, server_default=func.current_date())
    weekly_reset_date = Column(Date, server_default=func.current_date())
    monthly_reset_date = Column(Date, server_default=func.current_date())

    # AI recommendation flag
    ai_recommended = Column(Boolean, default=False)
    ai_recommendation_date = Column(DateTime(timezone=True))

    # Alert preferences
    alert_on_approach = Column(Boolean, default=True)   # 80% threshold
    alert_on_exceed = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
