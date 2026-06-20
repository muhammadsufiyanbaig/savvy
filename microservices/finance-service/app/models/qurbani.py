from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy.sql import func
from app.core.database import Base

ANIMAL_TYPES = ["goat", "sheep", "cow", "camel"]
QURBANI_STATUSES = ["saving", "ready", "completed", "cancelled"]


class QurbaniSavings(Base):
    __tablename__ = "qurbani_savings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    target_year = Column(Integer, nullable=False, index=True)
    hijri_year = Column(String(20))

    target_amount = Column(Numeric(15, 2), nullable=False)
    current_amount = Column(Numeric(15, 2), default=0.00)
    progress = Column(Numeric(5, 2), default=0.00)

    animal_type = Column(String(50))          # goat | sheep | cow | camel
    animal_shares = Column(Integer, default=1)
    estimated_cost_per_share = Column(Numeric(15, 2))

    status = Column(String(50), default="saving", index=True)
    completed_date = Column(Date)

    monthly_contribution = Column(Numeric(15, 2))
    auto_save_enabled = Column(Boolean, default=False)

    currency = Column(String(10), default="USD")
    notes = Column(Text)
    group_purchase = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
