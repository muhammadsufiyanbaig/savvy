"""Bank statement endpoints."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.statement import (
    StatementUploadResponse, StatementResponse,
    StatementListResponse, StatementDownloadResponse,
)
from app.schemas.common import MessageResponse
from app.services import account_service, statement_service

router = APIRouter(prefix="/statements", tags=["Bank Statements"])

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.post(
    "/upload",
    response_model=StatementUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_statement(
    file: UploadFile = File(...),
    account_id: int = Form(...),
    statement_period_start: Optional[date] = Form(None),
    statement_period_end: Optional[date] = Form(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Upload bank statement (PDF / CSV / Excel). Max 50 MB."""
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: PDF, CSV, Excel.",
        )
    if file.size and file.size > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file.size // (1024*1024)} MB). Maximum allowed is 50 MB.",
        )

    # Verify account belongs to user
    account = account_service.get_account(db, user_id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    if not account.is_active:
        raise HTTPException(status_code=400, detail="Cannot upload to an inactive account")

    record = statement_service.upload_statement(
        db, user_id, account_id, file,
        statement_period_start=statement_period_start,
        statement_period_end=statement_period_end,
    )

    # Inject presigned URL (non-fatal if S3 unavailable)
    resp = StatementUploadResponse.model_validate(record)
    if record.s3_key:
        from app.services import s3_service
        resp.download_url = s3_service.generate_presigned_url(record.s3_key)
    return resp


@router.get("", response_model=StatementListResponse)
def list_statements(
    account_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    rows, total = statement_service.list_statements(
        db, user_id,
        account_id=account_id, status=status,
        start_date=start_date, end_date=end_date,
        limit=limit, offset=offset,
    )
    return StatementListResponse(statements=rows, total=total)


@router.get("/{statement_id}", response_model=StatementResponse)
def get_statement(
    statement_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = statement_service.get_statement(db, user_id, statement_id)
    if not record:
        raise HTTPException(status_code=404, detail="Statement not found")
    return record


@router.get("/{statement_id}/download", response_model=StatementDownloadResponse)
def download_statement(
    statement_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Generate presigned S3 URL for statement download (expires in 1 hour)."""
    record = statement_service.get_statement(db, user_id, statement_id)
    if not record:
        raise HTTPException(status_code=404, detail="Statement not found")
    return statement_service.get_download_url(record)


@router.delete("/{statement_id}", response_model=MessageResponse)
def delete_statement(
    statement_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = statement_service.get_statement(db, user_id, statement_id)
    if not record:
        raise HTTPException(status_code=404, detail="Statement not found")
    statement_service.delete_statement(db, record)
    return MessageResponse(message="Statement deleted successfully")
