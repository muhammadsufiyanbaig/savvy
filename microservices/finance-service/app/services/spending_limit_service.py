"""Spending limits service — one record per user, lazy reset on read."""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.spending_limit import SpendingLimit
from app.schemas.spending_limit import SpendingLimitCreate, SpendingLimitUpdate
from app.utils.calculations import get_current_week_start, get_current_month_start, pct

logger = logging.getLogger(__name__)


def _reset_if_needed(limit: SpendingLimit) -> bool:
    """Lazy-reset counters when period crosses a day/week/month boundary."""
    today = date.today()
    week_start = get_current_week_start()
    month_start = get_current_month_start()
    changed = False

    if limit.daily_reset_date and limit.daily_reset_date < today:
        limit.daily_spent = Decimal("0.00")
        limit.daily_reset_date = today
        changed = True
    if limit.weekly_reset_date and limit.weekly_reset_date < week_start:
        limit.weekly_spent = Decimal("0.00")
        limit.weekly_reset_date = week_start
        changed = True
    if limit.monthly_reset_date and limit.monthly_reset_date < month_start:
        limit.monthly_spent = Decimal("0.00")
        limit.monthly_reset_date = month_start
        changed = True

    return changed


def get_or_create(db: Session, user_id: int) -> SpendingLimit:
    record = db.query(SpendingLimit).filter(SpendingLimit.user_id == user_id).first()
    if not record:
        record = SpendingLimit(user_id=user_id)
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


def create_or_update(db: Session, user_id: int, data: SpendingLimitCreate) -> SpendingLimit:
    record = db.query(SpendingLimit).filter(SpendingLimit.user_id == user_id).first()
    if record:
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(record, field, val)
    else:
        record = SpendingLimit(
            user_id=user_id,
            daily_limit=data.daily_limit,
            weekly_limit=data.weekly_limit,
            monthly_limit=data.monthly_limit,
            currency=data.currency,
            alert_on_approach=data.alert_on_approach,
            alert_on_exceed=data.alert_on_exceed,
        )
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_limits(db: Session, user_id: int, data: SpendingLimitUpdate) -> SpendingLimit:
    record = get_or_create(db, user_id)
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(record, field, val)
    db.commit()
    db.refresh(record)
    return record


def delete_limits(db: Session, user_id: int) -> None:
    db.query(SpendingLimit).filter(SpendingLimit.user_id == user_id).delete()
    db.commit()


def add_spending(db: Session, user_id: int, amount: Decimal) -> None:
    """Add to daily/weekly/monthly counters. Called on every expense creation."""
    record = db.query(SpendingLimit).filter(SpendingLimit.user_id == user_id).first()
    if not record:
        return  # No limits set; nothing to track

    _reset_if_needed(record)

    record.daily_spent = (record.daily_spent or Decimal("0")) + amount
    record.weekly_spent = (record.weekly_spent or Decimal("0")) + amount
    record.monthly_spent = (record.monthly_spent or Decimal("0")) + amount
    db.commit()


def get_status(db: Session, user_id: int) -> Dict[str, Any]:
    record = db.query(SpendingLimit).filter(SpendingLimit.user_id == user_id).first()
    if not record:
        return {
            "daily_limit": None, "weekly_limit": None, "monthly_limit": None,
            "daily_spent": 0.0, "weekly_spent": 0.0, "monthly_spent": 0.0,
            "alerts": [],
        }

    _reset_if_needed(record)
    db.commit()

    def _pct(spent, limit):
        return pct(float(spent or 0), float(limit)) if limit else None

    def _remaining(spent, limit):
        return float(limit) - float(spent or 0) if limit else None

    alerts: List[Dict[str, Any]] = []

    def _check(label, spent, limit):
        if not limit:
            return
        perc = pct(float(spent or 0), float(limit))
        if perc >= 100:
            alerts.append({"type": label, "message": f"{label.capitalize()} spending limit exceeded", "severity": "high"})
        elif perc >= 80:
            alerts.append({"type": label, "message": f"{label.capitalize()} spending at {perc:.0f}%", "severity": "medium"})

    _check("daily", record.daily_spent, record.daily_limit)
    _check("weekly", record.weekly_spent, record.weekly_limit)
    _check("monthly", record.monthly_spent, record.monthly_limit)

    return {
        "daily_limit": float(record.daily_limit) if record.daily_limit else None,
        "weekly_limit": float(record.weekly_limit) if record.weekly_limit else None,
        "monthly_limit": float(record.monthly_limit) if record.monthly_limit else None,
        "daily_spent": float(record.daily_spent or 0),
        "weekly_spent": float(record.weekly_spent or 0),
        "monthly_spent": float(record.monthly_spent or 0),
        "daily_remaining": _remaining(record.daily_spent, record.daily_limit),
        "weekly_remaining": _remaining(record.weekly_spent, record.weekly_limit),
        "monthly_remaining": _remaining(record.monthly_spent, record.monthly_limit),
        "daily_percentage": _pct(record.daily_spent, record.daily_limit),
        "weekly_percentage": _pct(record.weekly_spent, record.weekly_limit),
        "monthly_percentage": _pct(record.monthly_spent, record.monthly_limit),
        "alerts": alerts,
    }
