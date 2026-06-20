"""Cash savings endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.cash_savings import (
    CashSavingsCreate, CashSavingsUpdate, CashSavingsResponse, CashSavingsListResponse,
)
from app.schemas.common import MessageResponse
from app.services import cash_savings_service

router = APIRouter(prefix="/cash-savings", tags=["Cash Savings"])


@router.post("", response_model=CashSavingsResponse, status_code=status.HTTP_201_CREATED)
def create(
    data: CashSavingsCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return cash_savings_service.create(db, user_id, data)


@router.get("", response_model=CashSavingsListResponse)
def list_all(
    location: Optional[str] = Query(None),
    purpose: Optional[str] = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    records = cash_savings_service.list_all(db, user_id, location=location, purpose=purpose)
    summary = cash_savings_service.summary(records)
    return CashSavingsListResponse(cash_savings=records, total=len(records), summary=summary)


@router.get("/{record_id}", response_model=CashSavingsResponse)
def get(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = cash_savings_service.get(db, user_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Cash savings record not found")
    return record


@router.put("/{record_id}", response_model=CashSavingsResponse)
def update(
    record_id: int,
    data: CashSavingsUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = cash_savings_service.get(db, user_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Cash savings record not found")
    return cash_savings_service.update(db, record, data)


@router.delete("/{record_id}", response_model=MessageResponse)
def delete(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = cash_savings_service.get(db, user_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Cash savings record not found")
    cash_savings_service.delete(db, record)
    return MessageResponse(message="Cash savings record deleted successfully")
