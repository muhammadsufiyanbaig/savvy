"""Cash savings service."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.cash_savings import CashSavings
from app.schemas.cash_savings import CashSavingsCreate, CashSavingsUpdate

logger = logging.getLogger(__name__)


def create(db: Session, user_id: int, data: CashSavingsCreate) -> CashSavings:
    from datetime import date
    record = CashSavings(
        user_id=user_id,
        amount=data.amount,
        currency=data.currency.upper(),
        location=data.location,
        location_description=data.location_description,
        description=data.description,
        purpose=data.purpose,
        last_counted_date=data.last_counted_date or date.today(),
        denomination_breakdown=data.denomination_breakdown,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get(db: Session, user_id: int, record_id: int) -> Optional[CashSavings]:
    return db.query(CashSavings).filter(
        CashSavings.id == record_id, CashSavings.user_id == user_id
    ).first()


def list_all(
    db: Session, user_id: int,
    location: Optional[str] = None,
    purpose: Optional[str] = None,
) -> List[CashSavings]:
    q = db.query(CashSavings).filter(CashSavings.user_id == user_id)
    if location:
        q = q.filter(CashSavings.location == location)
    if purpose:
        q = q.filter(CashSavings.purpose == purpose)
    return q.order_by(CashSavings.created_at.desc()).all()


def update(db: Session, record: CashSavings, data: CashSavingsUpdate) -> CashSavings:
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(record, field, val)
    db.commit()
    db.refresh(record)
    return record


def delete(db: Session, record: CashSavings) -> None:
    db.delete(record)
    db.commit()


def summary(records: List[CashSavings]) -> Dict[str, Any]:
    total = sum(float(r.amount) for r in records)
    return {"total_cash": total, "locations": len(set(r.location for r in records if r.location))}
