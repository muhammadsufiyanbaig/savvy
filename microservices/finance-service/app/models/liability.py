from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, Date
from sqlalchemy.sql import func
from app.core.database import Base

LIABILITY_CATEGORIES = [
    "personal_loan", "car_loan", "home_loan", "student_loan",
    "credit_card", "business_loan", "family_loan", "other",
]

LIABILITY_CATEGORY_LABELS = {
    "personal_loan":  "Personal Loan",
    "car_loan":       "Car / Auto Loan",
    "home_loan":      "Home / Mortgage",
    "student_loan":   "Student Loan",
    "credit_card":    "Credit Card",
    "business_loan":  "Business Loan",
    "family_loan":    "Family / Friend Loan",
    "other":          "Other",
}


class Liability(Base):
    __tablename__ = "liabilities"

    id                = Column(Integer, primary_key=True, index=True)
    user_id           = Column(Integer, nullable=False, index=True)

    name              = Column(String(255), nullable=False)
    category          = Column(String(50), nullable=False, index=True)
    currency          = Column(String(10), default="USD")

    original_amount   = Column(Numeric(15, 2))          # amount when taken
    amount_owed       = Column(Numeric(15, 2), nullable=False)  # current balance
    monthly_payment   = Column(Numeric(15, 2))
    due_date          = Column(Date)                     # final payoff / maturity date

    lender            = Column(String(255))
    is_interest_bearing = Column(Boolean, default=False) # riba flag
    notes             = Column(Text)
    is_active         = Column(Boolean, default=True)

    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at        = Column(DateTime(timezone=True))
