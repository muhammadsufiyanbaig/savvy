from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, Date, JSON
from sqlalchemy.sql import func
from app.core.database import Base

# Allowed expense categories (canonical list)
EXPENSE_CATEGORIES = [
    "Food", "Transport", "Healthcare", "Education", "Entertainment",
    "Shopping", "Bills", "Rent", "Utilities", "Insurance",
    "Charity", "Investment", "Debt", "Savings", "Travel", "Other",
]

# Allowed expense types
EXPENSE_TYPES = ["fixed", "variable", "event_based", "emergency"]

# Allowed payment methods
PAYMENT_METHODS = ["cash", "card", "bank_transfer", "mobile_payment", "other"]

# Allowed recurrence patterns
RECURRENCE_PATTERNS = ["daily", "weekly", "monthly", "yearly"]

# Created-from sources
CREATED_FROM = ["manual", "bank_statement", "receipt_scan", "ai_imported"]


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Amount
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="USD")

    # Classification
    category = Column(String(100), nullable=False, index=True)
    expense_type = Column(String(50), nullable=False, index=True)

    # Details
    description = Column(Text)
    merchant_name = Column(String(255))
    payment_method = Column(String(50))

    # Recurring
    is_recurring = Column(Boolean, default=False, index=True)
    recurrence_pattern = Column(String(50))  # daily | weekly | monthly | yearly
    recurrence_day = Column(Integer)          # day of month/week
    next_occurrence_date = Column(Date)

    # Transaction timing
    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Metadata
    created_from = Column(String(50), default="manual")
    receipt_image_url = Column(String(500))
    tags = Column(JSON, default=list)         # list of strings

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))  # None = not deleted (soft delete)
