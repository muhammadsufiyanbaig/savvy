"""Qurbani savings endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.qurbani import (
    QurbaniSavingsCreate, QurbaniSavingsUpdate, QurbaniSavingsResponse,
    QurbaniListResponse, QurbaniContributeRequest,
)
from app.schemas.common import MessageResponse
from app.services import qurbani_service

router = APIRouter(prefix="/qurbani", tags=["Qurbani"])


@router.get("/prices")
def get_prices(currency: str = Query("PKR")):
    """Approximate animal prices — no auth required."""
    return qurbani_service.get_animal_prices(currency)


@router.post("", response_model=QurbaniSavingsResponse, status_code=status.HTTP_201_CREATED)
def create(
    data: QurbaniSavingsCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return qurbani_service.create(db, user_id, data)


@router.get("", response_model=QurbaniListResponse)
def list_all(
    animal_type: Optional[str] = Query(None),
    target_year: Optional[int] = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    records = qurbani_service.list_all(db, user_id, animal_type=animal_type, target_year=target_year)
    summary = qurbani_service.summary(records)
    return QurbaniListResponse(savings=records, total=len(records), summary=summary)


@router.get("/{record_id}", response_model=QurbaniSavingsResponse)
def get(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = qurbani_service.get(db, user_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Qurbani savings record not found")
    return record


@router.put("/{record_id}", response_model=QurbaniSavingsResponse)
def update(
    record_id: int,
    data: QurbaniSavingsUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = qurbani_service.get(db, user_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Qurbani savings record not found")
    return qurbani_service.update(db, record, data)


@router.post("/{record_id}/contribute", response_model=QurbaniSavingsResponse)
def contribute(
    record_id: int,
    req: QurbaniContributeRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = qurbani_service.get(db, user_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Qurbani savings record not found")
    return qurbani_service.contribute(db, record, req)


@router.delete("/{record_id}", response_model=MessageResponse)
def delete(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = qurbani_service.get(db, user_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Qurbani savings record not found")
    qurbani_service.delete(db, record)
    return MessageResponse(message="Qurbani savings record deleted successfully")
