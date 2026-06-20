"""Bank statement service — upload, list, download, status updates."""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.statement import BankStatement
from app.services import s3_service

logger = logging.getLogger(__name__)

_ALLOWED_TYPES = set(settings.ALLOWED_FILE_TYPES)
_CONTENT_TYPES: Dict[str, str] = {
    "pdf":  "application/pdf",
    "csv":  "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls":  "application/vnd.ms-excel",
}


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_upload(file: UploadFile) -> Tuple[str, int]:
    """
    Validate file type + size.
    Returns (ext, file_size_bytes) or raises HTTPException.
    """
    ext = _ext(file.filename or "")
    if ext not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type .{ext} not allowed. Allowed: {', '.join(sorted(_ALLOWED_TYPES))}",
        )
    file_size = s3_service.get_file_size(file.file)
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if file_size > settings.MAX_FILE_SIZE_BYTES:
        max_mb = settings.MAX_FILE_SIZE_BYTES / 1_048_576
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {max_mb:.0f} MB",
        )
    return ext, file_size


def upload_statement(
    db: Session,
    user_id: int,
    account_id: int,
    file: UploadFile,
    statement_period_start: Optional[date] = None,
    statement_period_end: Optional[date] = None,
) -> BankStatement:
    """Validate file, upload to S3 (non-fatal if unavailable), save DB record, publish event."""
    ext, file_size = validate_upload(file)

    # Build S3 key
    s3_key = s3_service.build_s3_key(user_id, file.filename)
    content_type = _CONTENT_TYPES.get(ext, "application/octet-stream")

    # Upload to S3 (non-fatal)
    file.file.seek(0)
    s3_ok = s3_service.upload_file(file.file, s3_key, content_type)

    # Derive statement month
    statement_month: Optional[str] = None
    if statement_period_start:
        statement_month = statement_period_start.strftime("%Y-%m")

    record = BankStatement(
        user_id=user_id,
        account_id=account_id,
        file_name=file.filename,
        file_path=s3_key,
        file_type=ext,
        file_size=file_size,
        statement_period_start=statement_period_start,
        statement_period_end=statement_period_end,
        statement_month=statement_month,
        processing_status="uploaded",
        s3_bucket=settings.AWS_S3_BUCKET if s3_ok else None,
        s3_key=s3_key if s3_ok else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Publish event (non-fatal)
    try:
        from app.events.producer import publish_statement_uploaded
        publish_statement_uploaded(user_id, {
            "statement_id": record.id,
            "account_id": account_id,
            "file_name": file.filename,
            "file_path": s3_key,
            "file_type": ext,
            "file_size": file_size,
            "statement_period_start": statement_period_start.isoformat() if statement_period_start else None,
            "statement_period_end": statement_period_end.isoformat() if statement_period_end else None,
        })
    except Exception as exc:
        logger.warning("Kafka publish failed (non-fatal): %s", exc)

    logger.info("Statement uploaded: id=%s user=%s account=%s", record.id, user_id, account_id)
    return record


def get_statement(db: Session, user_id: int, statement_id: int) -> Optional[BankStatement]:
    return db.query(BankStatement).filter(
        BankStatement.id == statement_id,
        BankStatement.user_id == user_id,
    ).first()


def list_statements(
    db: Session,
    user_id: int,
    account_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[BankStatement], int]:
    q = db.query(BankStatement).filter(BankStatement.user_id == user_id)
    if account_id:
        q = q.filter(BankStatement.account_id == account_id)
    if status:
        q = q.filter(BankStatement.processing_status == status)
    if start_date:
        q = q.filter(BankStatement.statement_period_start >= start_date)
    if end_date:
        q = q.filter(BankStatement.statement_period_end <= end_date)
    total = q.count()
    rows = q.order_by(BankStatement.uploaded_at.desc()).limit(limit).offset(offset).all()
    return rows, total


def get_download_url(statement: BankStatement) -> Dict[str, Any]:
    if not statement.s3_key:
        raise HTTPException(status_code=404, detail="No S3 file associated with this statement")
    url = s3_service.generate_presigned_url(statement.s3_key)
    if not url:
        raise HTTPException(status_code=503, detail="S3 unavailable — cannot generate download URL")
    return {
        "download_url": url,
        "expires_in": settings.S3_PRESIGNED_URL_EXPIRES,
        "file_name": statement.file_name,
        "file_type": statement.file_type,
        "file_size": statement.file_size,
    }


def delete_statement(db: Session, statement: BankStatement) -> None:
    if statement.s3_key:
        s3_service.delete_file(statement.s3_key)
    db.delete(statement)
    db.commit()


def update_processing_result(
    db: Session,
    statement_id: int,
    status: str,
    error: Optional[str] = None,
    total_transactions: Optional[int] = None,
    total_income: Optional[Decimal] = None,
    total_expenses: Optional[Decimal] = None,
) -> Optional[BankStatement]:
    """Called by Kafka consumer when Statement Analysis Service finishes."""
    record = db.query(BankStatement).filter(BankStatement.id == statement_id).first()
    if not record:
        return None
    record.processing_status = status
    if error:
        record.processing_error = error
    if total_transactions is not None:
        record.total_transactions = total_transactions
    if total_income is not None:
        record.total_income = total_income
    if total_expenses is not None:
        record.total_expenses = total_expenses
    if status == "processed":
        record.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record
