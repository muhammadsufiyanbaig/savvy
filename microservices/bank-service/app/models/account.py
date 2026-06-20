"""BankAccount ORM model."""
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean,
    DateTime, Text, ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

ACCOUNT_TYPES = ["checking", "savings", "credit_card", "investment", "loan"]
ACCOUNT_STATUSES = ["active", "inactive", "closed"]


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Identity
    account_name = Column(String(255), nullable=False)
    bank_name = Column(String(255), nullable=False)
    account_number = Column(String(100))        # masked: ****1234

    # Classification
    account_type = Column(String(50), nullable=False, index=True)  # checking | savings | credit_card | investment | loan

    # Financial
    balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    credit_limit = Column(Numeric(15, 2))       # for credit_card
    interest_rate = Column(Numeric(5, 2))        # for savings / loan

    # Metadata
    purpose = Column(Text)
    notes = Column(Text)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_primary = Column(Boolean, default=False, nullable=False)

    last_synced = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    statements = relationship(
        "BankStatement",
        back_populates="account",
        cascade="all, delete-orphan",
    )
