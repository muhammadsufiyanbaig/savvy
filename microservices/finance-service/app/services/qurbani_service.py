"""Qurbani savings service."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.qurbani import QurbaniSavings
from app.schemas.qurbani import QurbaniSavingsCreate, QurbaniSavingsUpdate, QurbaniContributeRequest

logger = logging.getLogger(__name__)

# Approximate prices per SHARE in PKR
ANIMAL_SHARE_PRICES_PKR: Dict[str, Decimal] = {
    "goat":    Decimal("25000"),   # 1 share = full goat
    "sheep":   Decimal("30000"),   # 1 share = full sheep
    "cow":     Decimal("25000"),   # 1/7 share of ~175,000 cow
    "camel":   Decimal("50000"),   # 1/7 share of ~350,000 camel
}

ANIMAL_MAX_SHARES: Dict[str, int] = {
    "goat": 1,
    "sheep": 1,
    "cow": 7,
    "camel": 7,
}


def get_animal_prices(currency: str = "PKR") -> Dict[str, Any]:
    prices = {}
    for animal, share_price_pkr in ANIMAL_SHARE_PRICES_PKR.items():
        max_shares = ANIMAL_MAX_SHARES[animal]
        full_price = share_price_pkr * max_shares
        prices[animal] = {
            "max_shares": max_shares,
            "price_per_share_pkr": float(share_price_pkr),
            "full_animal_price_pkr": float(full_price),
        }
    return {
        "currency": "PKR",
        "note": "Prices are approximate. Verify local market rates before Eid.",
        "animals": prices,
    }


def create(db: Session, user_id: int, data: QurbaniSavingsCreate) -> QurbaniSavings:
    # Calculate target amount from animal type and shares if not explicitly set
    target = data.target_amount
    estimated_per_share = data.estimated_cost_per_share
    if not estimated_per_share and data.animal_type:
        estimated_per_share = ANIMAL_SHARE_PRICES_PKR.get(data.animal_type.lower())

    record = QurbaniSavings(
        user_id=user_id,
        target_year=data.target_year,
        hijri_year=data.hijri_year,
        target_amount=target,
        current_amount=Decimal("0.00"),
        progress=Decimal("0.00"),
        currency=data.currency.upper(),
        animal_type=data.animal_type.lower() if data.animal_type else None,
        animal_shares=data.animal_shares,
        estimated_cost_per_share=estimated_per_share,
        monthly_contribution=data.monthly_contribution,
        auto_save_enabled=data.auto_save_enabled,
        group_purchase=data.group_purchase,
        status="saving",
        notes=data.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        from app.events.producer import publish_qurbani_goal_created
        publish_qurbani_goal_created(user_id, {
            "record_id": record.id,
            "animal_type": record.animal_type,
            "target_amount": float(record.target_amount),
            "currency": record.currency,
            "target_year": record.target_year,
        })
    except Exception as exc:
        logger.warning("Kafka publish failed (non-fatal): %s", exc)

    return record


def get(db: Session, user_id: int, record_id: int) -> Optional[QurbaniSavings]:
    return db.query(QurbaniSavings).filter(
        QurbaniSavings.id == record_id,
        QurbaniSavings.user_id == user_id,
    ).first()


def list_all(
    db: Session, user_id: int,
    animal_type: Optional[str] = None,
    target_year: Optional[int] = None,
) -> List[QurbaniSavings]:
    q = db.query(QurbaniSavings).filter(QurbaniSavings.user_id == user_id)
    if animal_type:
        q = q.filter(QurbaniSavings.animal_type == animal_type.lower())
    if target_year:
        q = q.filter(QurbaniSavings.target_year == target_year)
    return q.order_by(QurbaniSavings.created_at.desc()).all()


def update(db: Session, record: QurbaniSavings, data: QurbaniSavingsUpdate) -> QurbaniSavings:
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(record, field, val)
    # Recalculate progress
    if record.target_amount and record.target_amount > 0:
        record.progress = min(
            Decimal("100"),
            (record.current_amount or Decimal("0")) / record.target_amount * 100
        )
    db.commit()
    db.refresh(record)
    return record


def contribute(db: Session, record: QurbaniSavings, req: QurbaniContributeRequest) -> QurbaniSavings:
    record.current_amount = (record.current_amount or Decimal("0")) + req.amount
    if record.target_amount and record.target_amount > 0:
        record.progress = min(
            Decimal("100"),
            record.current_amount / record.target_amount * 100
        )
        if record.current_amount >= record.target_amount and record.status == "saving":
            record.status = "ready"
    if req.description:
        record.notes = req.description
    db.commit()
    db.refresh(record)
    return record


def delete(db: Session, record: QurbaniSavings) -> None:
    db.delete(record)
    db.commit()


def summary(records: List[QurbaniSavings]) -> Dict[str, Any]:
    total_target = sum(float(r.target_amount or 0) for r in records)
    total_saved = sum(float(r.current_amount or 0) for r in records)
    return {
        "total_records": len(records),
        "total_target": total_target,
        "total_saved": total_saved,
        "overall_progress": round(total_saved / total_target * 100, 2) if total_target else 0.0,
        "ready": sum(1 for r in records if r.status == "ready"),
    }
