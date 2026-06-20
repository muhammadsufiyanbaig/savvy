from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, Date, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

PLAN_TYPES    = ["hajj", "umrah"]
PACKAGE_TYPES = ["economy", "standard", "premium", "vip"]


class HajjUmrahPlan(Base):
    __tablename__ = "hajj_umrah_plans"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, nullable=False, index=True)

    plan_type       = Column(String(20), nullable=False)   # hajj | umrah
    title           = Column(String(255))                  # custom label
    target_year     = Column(Integer, nullable=False)
    num_persons     = Column(Integer, default=1)
    departure_city  = Column(String(100))
    package_type    = Column(String(20), default="standard")

    estimated_cost  = Column(Numeric(15, 2), nullable=False)
    current_amount  = Column(Numeric(15, 2), default=0)
    currency        = Column(String(10), default="USD")

    notes           = Column(Text)
    is_active       = Column(Boolean, default=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at      = Column(DateTime(timezone=True))


class HajjUmrahDeposit(Base):
    __tablename__ = "hajj_umrah_deposits"

    id         = Column(Integer, primary_key=True, index=True)
    plan_id    = Column(Integer, ForeignKey("hajj_umrah_plans.id", ondelete="CASCADE"), nullable=False)
    user_id    = Column(Integer, nullable=False, index=True)

    amount     = Column(Numeric(15, 2), nullable=False)
    note       = Column(String(255))
    date       = Column(Date, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
