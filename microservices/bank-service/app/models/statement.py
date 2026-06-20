"""BankStatement ORM model."""
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean,
    DateTime, Date, Text, ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

PROCESSING_STATUSES = ["uploaded", "processing", "processed", "failed"]
ALLOWED_FILE_TYPES = ["pdf", "csv", "xlsx", "xls"]


class BankStatement(Base):
    __tablename__ = "bank_statements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    account_id = Column(
        Integer,
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File info
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)   # S3 key
    file_type = Column(String(50), nullable=False)    # pdf | csv | xlsx | xls
    file_size = Column(Integer)                        # bytes

    # Statement period
    statement_period_start = Column(Date)
    statement_period_end = Column(Date)
    statement_month = Column(String(7), index=True)   # YYYY-MM

    # Processing
    processing_status = Column(String(50), default="uploaded", nullable=False, index=True)
    processing_error = Column(Text)

    # Summary (populated by Statement Analysis Service)
    total_transactions = Column(Integer, default=0)
    total_income = Column(Numeric(15, 2), default=0.00)
    total_expenses = Column(Numeric(15, 2), default=0.00)

    # S3 metadata
    s3_bucket = Column(String(255))
    s3_key = Column(String(500))

    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True))

    # Relationship
    account = relationship("BankAccount", back_populates="statements")
