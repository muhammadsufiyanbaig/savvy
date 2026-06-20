from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date
from sqlalchemy.sql import func
from app.core.database import Base

BUDGET_PERIODS = ["daily", "weekly", "monthly", "yearly"]
BUDGET_STATUSES = ["active", "exceeded", "completed"]


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    category = Column(String(100), nullable=False, index=True)

    allocated_amount = Column(Numeric(15, 2), nullable=False)
    spent_amount = Column(Numeric(15, 2), default=0.00)
    remaining_amount = Column(Numeric(15, 2))
    currency = Column(String(10), default="USD")

    period = Column(String(50), nullable=False, index=True)  # daily | weekly | monthly | yearly
    period_start_date = Column(Date, nullable=False, index=True)
    period_end_date = Column(Date, nullable=False, index=True)

    # Alerts
    alert_threshold = Column(Numeric(5, 2), default=80.00)  # percent
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime(timezone=True))

    # Status
    status = Column(String(50), default="active", index=True)
    exceeded = Column(Boolean, default=False)
    exceeded_at = Column(DateTime(timezone=True))

    # AI
    ai_recommended = Column(Boolean, default=False)
    ai_confidence_score = Column(Numeric(5, 2))

    # Rollover
    rollover_enabled = Column(Boolean, default=False)
    rollover_amount = Column(Numeric(15, 2), default=0.00)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
