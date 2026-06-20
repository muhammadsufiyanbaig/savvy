"""Budget service with auto-spending tracking and alert detection."""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.utils.calculations import days_between, pct

logger = logging.getLogger(__name__)


def create_budget(db: Session, user_id: int, data: BudgetCreate) -> Budget:
    budget = Budget(
        user_id=user_id,
        category=data.category,
        allocated_amount=data.allocated_amount,
        spent_amount=Decimal("0.00"),
        remaining_amount=data.allocated_amount,
        currency=data.currency,
        period=data.period,
        period_start_date=data.period_start_date,
        period_end_date=data.period_end_date,
        alert_threshold=data.alert_threshold,
        rollover_enabled=data.rollover_enabled,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)

    from app.events.producer import publish_budget_created
    publish_budget_created(user_id, {
        "budget_id": budget.id, "category": budget.category,
        "allocated_amount": float(budget.allocated_amount),
        "period": budget.period,
    })
    return budget


def get_budget(db: Session, user_id: int, budget_id: int) -> Optional[Budget]:
    return db.query(Budget).filter(
        Budget.id == budget_id, Budget.user_id == user_id
    ).first()


def list_budgets(
    db: Session, user_id: int,
    period: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_period_only: bool = True,
) -> List[Budget]:
    q = db.query(Budget).filter(Budget.user_id == user_id)
    if period:
        q = q.filter(Budget.period == period)
    if category:
        q = q.filter(Budget.category == category)
    if status:
        q = q.filter(Budget.status == status)
    if current_period_only:
        today = date.today()
        q = q.filter(
            and_(Budget.period_start_date <= today, Budget.period_end_date >= today)
        )
    return q.order_by(Budget.category).all()


def update_budget(db: Session, budget: Budget, data: BudgetUpdate) -> Budget:
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(budget, field, val)
    # Recalculate remaining
    if budget.allocated_amount and budget.spent_amount is not None:
        budget.remaining_amount = budget.allocated_amount - budget.spent_amount
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(db: Session, budget: Budget) -> None:
    db.delete(budget)
    db.commit()


def apply_expense_to_budgets(
    db: Session, user_id: int, category: str, amount: Decimal, tx_date: datetime
) -> None:
    """
    Find active budgets for this category+date and update spent_amount.
    Positive amount = expense, negative = reversal (delete/update).
    """
    tx_date_only = tx_date.date() if hasattr(tx_date, "date") else tx_date
    budgets = db.query(Budget).filter(
        and_(
            Budget.user_id == user_id,
            Budget.category == category,
            Budget.period_start_date <= tx_date_only,
            Budget.period_end_date >= tx_date_only,
            Budget.status != "completed",
        )
    ).all()

    for b in budgets:
        b.spent_amount = (b.spent_amount or Decimal("0")) + amount
        b.remaining_amount = b.allocated_amount - b.spent_amount

        # Check alert threshold
        if b.allocated_amount > 0:
            used_pct = float(b.spent_amount / b.allocated_amount * 100)
            if used_pct >= float(b.alert_threshold) and not b.alert_sent:
                b.alert_sent = True
                b.alert_sent_at = datetime.utcnow()
                logger.info("Budget alert: user=%s category=%s at %.1f%%", user_id, category, used_pct)

            # Check exceeded
            if b.spent_amount > b.allocated_amount and not b.exceeded:
                b.exceeded = True
                b.exceeded_at = datetime.utcnow()
                b.status = "exceeded"
                from app.events.producer import publish_budget_exceeded
                publish_budget_exceeded(user_id, {
                    "budget_id": b.id, "category": b.category,
                    "allocated_amount": float(b.allocated_amount),
                    "spent_amount": float(b.spent_amount),
                    "exceeded_by": float(b.spent_amount - b.allocated_amount),
                })

    db.commit()


def get_budget_status(db: Session, user_id: int, period: str = "monthly") -> Dict[str, Any]:
    today = date.today()
    budgets = db.query(Budget).filter(
        and_(
            Budget.user_id == user_id,
            Budget.period == period,
            Budget.period_start_date <= today,
            Budget.period_end_date >= today,
        )
    ).all()

    if not budgets:
        return {
            "period": period,
            "period_start": today,
            "period_end": today,
            "days_elapsed": 0,
            "days_remaining": 0,
            "total_allocated": 0.0,
            "total_spent": 0.0,
            "total_remaining": 0.0,
            "percentage_used": 0.0,
            "daily_average_spent": 0.0,
            "recommended_daily_spend": 0.0,
            "on_track": True,
            "categories": [],
            "alerts": [],
        }

    start = min(b.period_start_date for b in budgets)
    end = max(b.period_end_date for b in budgets)
    total_alloc = sum(float(b.allocated_amount) for b in budgets)
    total_spent = sum(float(b.spent_amount or 0) for b in budgets)
    elapsed = days_between(start, today)
    remaining_days = days_between(today, end)

    categories = []
    alerts = []

    for b in budgets:
        spent = float(b.spent_amount or 0)
        alloc = float(b.allocated_amount)
        perc = pct(spent, alloc) if alloc else 0

        stat = "on_track"
        if spent > alloc:
            stat = "exceeded"
        elif perc >= float(b.alert_threshold):
            stat = "warning"

        categories.append({
            "category": b.category, "allocated": alloc, "spent": spent,
            "remaining": alloc - spent, "percentage": perc, "status": stat,
        })

        if stat == "exceeded":
            alerts.append({"category": b.category,
                           "message": f"Budget exceeded by {spent - alloc:.2f} {b.currency}",
                           "severity": "high"})
        elif stat == "warning":
            alerts.append({"category": b.category,
                           "message": f"Budget is {perc:.0f}% utilized",
                           "severity": "medium"})

    daily_avg = total_spent / elapsed if elapsed > 0 else 0
    rec_daily = (total_alloc - total_spent) / remaining_days if remaining_days > 0 else 0

    return {
        "period": period, "period_start": start, "period_end": end,
        "days_elapsed": elapsed, "days_remaining": remaining_days,
        "total_allocated": total_alloc, "total_spent": total_spent,
        "total_remaining": total_alloc - total_spent,
        "percentage_used": pct(total_spent, total_alloc),
        "daily_average_spent": round(daily_avg, 2),
        "recommended_daily_spend": round(rec_daily, 2),
        "on_track": total_spent <= (total_alloc * elapsed / days_between(start, end))
            if days_between(start, end) > 0 else True,
        "categories": categories, "alerts": alerts,
    }
