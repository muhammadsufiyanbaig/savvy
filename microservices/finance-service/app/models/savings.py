from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, Date, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

GOAL_TYPES = [
    "emergency_fund", "vacation", "purchase", "investment",
    "education", "wedding", "retirement", "house", "car", "other",
]

GOAL_STATUSES = ["active", "completed", "paused", "cancelled"]
AUTO_DEPOSIT_FREQUENCIES = ["daily", "weekly", "monthly"]
TRANSACTION_TYPES = ["deposit", "withdrawal"]


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    name = Column(String(255), nullable=False)
    goal_type = Column(String(50), nullable=False, index=True)
    description = Column(Text)

    target_amount = Column(Numeric(15, 2), nullable=False)
    current_amount = Column(Numeric(15, 2), default=0.00)
    currency = Column(String(10), default="USD")

    progress = Column(Numeric(5, 2), default=0.00)  # 0–100

    target_date = Column(Date)
    start_date = Column(Date, server_default=func.current_date())
    completed_date = Column(Date)

    status = Column(String(50), default="active", index=True)

    # Auto-save
    auto_deposit_enabled = Column(Boolean, default=False)
    auto_deposit_amount = Column(Numeric(15, 2))
    auto_deposit_frequency = Column(String(50))
    last_auto_deposit_date = Column(Date)

    # UI hints
    icon = Column(String(50))
    color = Column(String(20))
    priority = Column(Integer, default=0)  # 0=low, 1=medium, 2=high

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    transactions = relationship(
        "SavingsTransaction", back_populates="goal", cascade="all, delete-orphan"
    )


class SavingsTransaction(Base):
    __tablename__ = "savings_transactions"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("savings_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    amount = Column(Numeric(15, 2), nullable=False)
    transaction_type = Column(String(50), nullable=False, index=True)  # deposit | withdrawal

    description = Column(Text)
    notes = Column(Text)
    source = Column(String(100))  # salary, bonus, refund, etc.

    transaction_date = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    goal = relationship("SavingsGoal", back_populates="transactions")
