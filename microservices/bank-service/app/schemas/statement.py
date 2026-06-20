"""Bank statement Pydantic v2 schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StatementUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    account_id: int
    file_name: str
    file_type: str
    file_size: Optional[int] = None
    file_path: str
    statement_period_start: Optional[date] = None
    statement_period_end: Optional[date] = None
    statement_month: Optional[str] = None
    processing_status: str
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None
    uploaded_at: datetime
    download_url: Optional[str] = None  # injected by API layer


class StatementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    account_id: int
    file_name: str
    file_type: str
    file_size: Optional[int] = None
    file_path: str
    statement_period_start: Optional[date] = None
    statement_period_end: Optional[date] = None
    statement_month: Optional[str] = None
    processing_status: str
    processing_error: Optional[str] = None
    total_transactions: int = 0
    total_income: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None


class StatementListResponse(BaseModel):
    statements: List[StatementResponse]
    total: int


class StatementDownloadResponse(BaseModel):
    download_url: str
    expires_in: int
    file_name: str
    file_type: str
    file_size: Optional[int] = None


class StatementStatusUpdate(BaseModel):
    """Used internally by consumer to update processing result."""
    processing_status: str
    processing_error: Optional[str] = None
    total_transactions: Optional[int] = None
    total_income: Optional[Decimal] = None
    total_expenses: Optional[Decimal] = None
