"""Spending limits endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.spending_limit import (
    SpendingLimitCreate, SpendingLimitUpdate, SpendingLimitResponse, SpendingLimitStatusResponse,
)
from app.schemas.common import MessageResponse
from app.services import spending_limit_service

router = APIRouter(prefix="/spending-limits", tags=["Spending Limits"])


@router.post("", response_model=SpendingLimitResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_limits(
    data: SpendingLimitCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create or overwrite spending limits for the user."""
    return spending_limit_service.create_or_update(db, user_id, data)


@router.get("", response_model=SpendingLimitResponse)
def get_limits(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = spending_limit_service.get_or_create(db, user_id)
    return record


@router.patch("", response_model=SpendingLimitResponse)
def update_limits(
    data: SpendingLimitUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Partially update spending limits."""
    return spending_limit_service.update_limits(db, user_id, data)


@router.get("/status", response_model=SpendingLimitStatusResponse)
def get_status(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get current spending vs limits with alerts."""
    return spending_limit_service.get_status(db, user_id)


@router.delete("", response_model=MessageResponse)
def delete_limits(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    spending_limit_service.delete_limits(db, user_id)
    return MessageResponse(message="Spending limits deleted successfully")
