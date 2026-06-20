from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy.sql import func
from app.core.database import Base

PAYMENT_STATUSES = ["pending", "partially_paid", "paid"]


class ZakatRecord(Base):
    __tablename__ = "zakat_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    calculation_date = Column(Date, nullable=False, index=True)
    hijri_year = Column(String(20), index=True)  # e.g. "1447"

    # Assets
    cash_in_hand = Column(Numeric(15, 2), default=0.00)
    bank_balance = Column(Numeric(15, 2), default=0.00)
    gold_value = Column(Numeric(15, 2), default=0.00)
    silver_value = Column(Numeric(15, 2), default=0.00)
    investments = Column(Numeric(15, 2), default=0.00)
    business_assets = Column(Numeric(15, 2), default=0.00)
    receivables = Column(Numeric(15, 2), default=0.00)
    other_assets = Column(Numeric(15, 2), default=0.00)
    total_assets = Column(Numeric(15, 2), nullable=False)

    # Liabilities
    immediate_debts = Column(Numeric(15, 2), default=0.00)
    other_liabilities = Column(Numeric(15, 2), default=0.00)
    total_liabilities = Column(Numeric(15, 2), default=0.00)

    # Calculation results
    zakatable_amount = Column(Numeric(15, 2), nullable=False)
    nisab_threshold = Column(Numeric(15, 2), nullable=False)
    nisab_met = Column(Boolean, nullable=False)
    zakat_rate = Column(Numeric(5, 2), default=2.5)
    zakat_due = Column(Numeric(15, 2), nullable=False)

    # Payment tracking
    payment_status = Column(String(50), default="pending", index=True)
    amount_paid = Column(Numeric(15, 2), default=0.00)
    payment_date = Column(Date)

    currency = Column(String(10), default="USD")
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
