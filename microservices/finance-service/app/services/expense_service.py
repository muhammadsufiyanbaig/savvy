"""
Expense service — CRUD + budget/spending-limit side-effects.
"""
from __future__ import annotations

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.utils.calculations import calc_next_occurrence, pct

logger = logging.getLogger(__name__)


# ── CRUD ─────────────────────────────────────────────────────────────────────

def create_expense(db: Session, user_id: int, data: ExpenseCreate) -> Expense:
    next_occ = None
    if data.is_recurring and data.recurrence_pattern:
        next_occ = calc_next_occurrence(
            data.transaction_date.date(), data.recurrence_pattern
        )

    expense = Expense(
        user_id=user_id,
        amount=data.amount,
        currency=data.currency,
        category=data.category,
        expense_type=data.expense_type,
        description=data.description,
        merchant_name=data.merchant_name,
        payment_method=data.payment_method,
        transaction_date=data.transaction_date,
        is_recurring=data.is_recurring,
        recurrence_pattern=data.recurrence_pattern,
        recurrence_day=data.recurrence_day,
        next_occurrence_date=next_occ,
        tags=data.tags or [],
        created_from=data.created_from,
        receipt_image_url=data.receipt_image_url,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    # Side-effects (non-fatal)
    _update_budget_on_expense(db, user_id, data.category, data.amount, data.transaction_date)
    _update_spending_limit_on_expense(db, user_id, data.amount)

    # Kafka
    from app.events.producer import publish_expense_created
    publish_expense_created(user_id, {
        "expense_id": expense.id,
        "amount": float(expense.amount),
        "currency": expense.currency,
        "category": expense.category,
        "expense_type": expense.expense_type,
        "transaction_date": expense.transaction_date.isoformat(),
        "is_recurring": expense.is_recurring,
    })

    logger.info("Expense created: id=%s user=%s amount=%s", expense.id, user_id, expense.amount)
    return expense


def get_expense(db: Session, user_id: int, expense_id: int) -> Optional[Expense]:
    return db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == user_id,
        Expense.deleted_at.is_(None),
    ).first()


def list_expenses(
    db: Session,
    user_id: int,
    category: Optional[str] = None,
    expense_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    is_recurring: Optional[bool] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    payment_method: Optional[str] = None,
    sort_by: str = "transaction_date",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Expense], int]:
    q = db.query(Expense).filter(
        Expense.user_id == user_id, Expense.deleted_at.is_(None)
    )
    if category:
        q = q.filter(Expense.category == category)
    if expense_type:
        q = q.filter(Expense.expense_type == expense_type)
    if start_date:
        q = q.filter(Expense.transaction_date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        q = q.filter(Expense.transaction_date <= datetime.combine(end_date, datetime.max.time()))
    if is_recurring is not None:
        q = q.filter(Expense.is_recurring == is_recurring)
    if min_amount is not None:
        q = q.filter(Expense.amount >= min_amount)
    if max_amount is not None:
        q = q.filter(Expense.amount <= max_amount)
    if payment_method:
        q = q.filter(Expense.payment_method == payment_method)

    total = q.count()
    col = getattr(Expense, sort_by, Expense.transaction_date)
    q = q.order_by(col.asc() if sort_order == "asc" else col.desc())
    return q.limit(limit).offset(offset).all(), total


def update_expense(db: Session, expense: Expense, data: ExpenseUpdate) -> Expense:
    old_amount = expense.amount
    old_category = expense.category
    changed = data.model_dump(exclude_unset=True)
    for field, val in changed.items():
        setattr(expense, field, val)
    db.commit()
    db.refresh(expense)

    # Adjust budget if amount or category changed
    if "amount" in changed or "category" in changed:
        _adjust_budget_on_update(
            db, expense.user_id, old_category, old_amount,
            expense.category, expense.amount, expense.transaction_date,
        )

    from app.events.producer import publish_expense_updated
    publish_expense_updated(expense.user_id, {"expense_id": expense.id, "updated_fields": changed})
    return expense


def delete_expense(db: Session, expense: Expense) -> None:
    """Soft delete."""
    expense.deleted_at = datetime.utcnow()
    db.commit()

    # Subtract from budget
    _update_budget_on_expense(
        db, expense.user_id, expense.category,
        -expense.amount, expense.transaction_date,
    )

    from app.events.producer import publish_expense_deleted
    publish_expense_deleted(expense.user_id, expense.id)


def get_expense_summary(
    db: Session, user_id: int, start_date: date, end_date: date
) -> Dict[str, Any]:
    rows: List[Expense] = db.query(Expense).filter(
        and_(
            Expense.user_id == user_id,
            Expense.transaction_date >= datetime.combine(start_date, datetime.min.time()),
            Expense.transaction_date <= datetime.combine(end_date, datetime.max.time()),
            Expense.deleted_at.is_(None),
        )
    ).all()

    total = sum(float(e.amount) for e in rows)
    count = len(rows)

    by_cat: Dict[str, Any] = {}
    by_type: Dict[str, Any] = {}
    by_method: Dict[str, Any] = {}

    for e in rows:
        # by category
        by_cat.setdefault(e.category, {"amount": 0.0, "count": 0})
        by_cat[e.category]["amount"] += float(e.amount)
        by_cat[e.category]["count"] += 1

        # by type
        by_type.setdefault(e.expense_type, {"amount": 0.0})
        by_type[e.expense_type]["amount"] += float(e.amount)

        # by payment
        if e.payment_method:
            by_method.setdefault(e.payment_method, {"amount": 0.0})
            by_method[e.payment_method]["amount"] += float(e.amount)

    for d in (by_cat, by_type, by_method):
        for k in d:
            d[k]["percentage"] = pct(d[k]["amount"], total)

    recurring = [e for e in rows if e.is_recurring]
    # Determine dominant currency (first row, fallback to "USD")
    currency = rows[0].currency if rows else "USD"
    return {
        "period": "custom",
        "start_date": start_date,
        "end_date": end_date,
        "currency": currency,
        "total_expenses": total,
        "expense_count": count,
        "average_expense": round(total / count, 2) if count else 0.0,
        "by_category": by_cat,
        "by_type": by_type,
        "by_payment_method": by_method,
        "recurring_expenses": {
            "total": sum(float(e.amount) for e in recurring),
            "count": len(recurring),
        },
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _update_budget_on_expense(
    db: Session, user_id: int, category: str, amount: Decimal, tx_date: datetime
) -> None:
    try:
        from app.services import budget_service
        budget_service.apply_expense_to_budgets(db, user_id, category, amount, tx_date)
    except Exception as exc:
        logger.error("Budget update failed (non-fatal): %s", exc)


def _update_spending_limit_on_expense(db: Session, user_id: int, amount: Decimal) -> None:
    try:
        from app.services import spending_limit_service
        spending_limit_service.add_spending(db, user_id, amount)
    except Exception as exc:
        logger.error("SpendingLimit update failed (non-fatal): %s", exc)


def _adjust_budget_on_update(
    db: Session, user_id: int,
    old_cat: str, old_amt: Decimal,
    new_cat: str, new_amt: Decimal,
    tx_date: datetime,
) -> None:
    try:
        from app.services import budget_service
        # Reverse old
        budget_service.apply_expense_to_budgets(db, user_id, old_cat, -old_amt, tx_date)
        # Apply new
        budget_service.apply_expense_to_budgets(db, user_id, new_cat, new_amt, tx_date)
    except Exception as exc:
        logger.error("Budget adjust on update failed (non-fatal): %s", exc)
