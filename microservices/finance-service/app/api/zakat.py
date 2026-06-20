"""Zakat endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.zakat import (
    ZakatCalculationRequest, ZakatPaymentUpdate,
    ZakatRecordResponse, ZakatListResponse, NisabResponse,
)
from app.schemas.common import MessageResponse
from app.services import zakat_service

router = APIRouter(prefix="/zakat", tags=["Zakat"])


@router.get("/nisab", response_model=NisabResponse)
def get_nisab(currency: str = Query("USD")):
    """Current nisab threshold — no auth required."""
    return zakat_service.get_nisab_threshold(currency)


@router.post("/calculate", response_model=ZakatRecordResponse, status_code=status.HTTP_201_CREATED)
def calculate_zakat(
    data: ZakatCalculationRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Calculate zakat and persist the record."""
    return zakat_service.calculate(db, user_id, data)


@router.get("", response_model=ZakatListResponse)
def list_records(
    year: Optional[int] = Query(None, description="Calendar year filter"),
    paid: Optional[bool] = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    records = zakat_service.list_records(db, user_id, year=year, paid=paid)
    total_due = sum(float(r.zakat_due or 0) for r in records)
    total_paid = sum(float(r.amount_paid or 0) for r in records)
    summary = {
        "total_calculated": len(records),
        "total_zakat_due": total_due,
        "total_paid": total_paid,
        "outstanding": round(total_due - total_paid, 2),
    }
    return ZakatListResponse(records=records, total=len(records), summary=summary)


@router.get("/{record_id}", response_model=ZakatRecordResponse)
def get_record(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = zakat_service.get_record(db, user_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Zakat record not found")
    return record


@router.patch("/{record_id}/payment", response_model=ZakatRecordResponse)
def update_payment(
    record_id: int,
    data: ZakatPaymentUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update payment details for a zakat record."""
    record = zakat_service.get_record(db, user_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Zakat record not found")
    return zakat_service.update_payment(db, record, data)


@router.delete("/{record_id}", response_model=MessageResponse)
def delete_record(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = zakat_service.get_record(db, user_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Zakat record not found")
    zakat_service.delete_record(db, record)
    return MessageResponse(message="Zakat record deleted successfully")
