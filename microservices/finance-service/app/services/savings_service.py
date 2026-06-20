"""Savings goals service."""
from __future__ import annotations

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.savings import SavingsGoal, SavingsTransaction
from app.schemas.savings import (
    SavingsGoalCreate, SavingsGoalUpdate, DepositRequest, WithdrawRequest,
)
from app.utils.calculations import calc_progress

logger = logging.getLogger(__name__)


def create_goal(db: Session, user_id: int, data: SavingsGoalCreate) -> SavingsGoal:
    goal = SavingsGoal(
        user_id=user_id,
        name=data.name,
        goal_type=data.goal_type,
        description=data.description,
        target_amount=data.target_amount,
        current_amount=Decimal("0.00"),
        currency=data.currency,
        progress=Decimal("0.00"),
        target_date=data.target_date,
        auto_deposit_enabled=data.auto_deposit_enabled,
        auto_deposit_amount=data.auto_deposit_amount,
        auto_deposit_frequency=data.auto_deposit_frequency,
        icon=data.icon,
        color=data.color,
        priority=data.priority,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    from app.events.producer import publish_savings_goal_created
    publish_savings_goal_created(user_id, {
        "goal_id": goal.id, "name": goal.name, "goal_type": goal.goal_type,
        "target_amount": float(goal.target_amount), "currency": goal.currency,
        "target_date": goal.target_date.isoformat() if goal.target_date else None,
    })
    return goal


def get_goal(db: Session, user_id: int, goal_id: int) -> Optional[SavingsGoal]:
    return db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id
    ).first()


def list_goals(
    db: Session, user_id: int,
    status: Optional[str] = None,
    goal_type: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> List[SavingsGoal]:
    q = db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id)
    if status:
        q = q.filter(SavingsGoal.status == status)
    if goal_type:
        q = q.filter(SavingsGoal.goal_type == goal_type)
    col = getattr(SavingsGoal, sort_by, SavingsGoal.created_at)
    q = q.order_by(col.asc() if sort_order == "asc" else col.desc())
    return q.all()


def update_goal(db: Session, goal: SavingsGoal, data: SavingsGoalUpdate) -> SavingsGoal:
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(goal, field, val)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal: SavingsGoal) -> None:
    db.delete(goal)
    db.commit()


def deposit(db: Session, user_id: int, goal: SavingsGoal, req: DepositRequest) -> SavingsTransaction:
    tx = SavingsTransaction(
        goal_id=goal.id, user_id=user_id,
        amount=req.amount, transaction_type="deposit",
        description=req.description, source=req.source,
    )
    db.add(tx)
    goal.current_amount = (goal.current_amount or Decimal("0")) + req.amount
    goal.progress = calc_progress(goal.current_amount, goal.target_amount)

    # Auto-complete
    if goal.progress >= 100 and goal.status == "active":
        goal.status = "completed"
        goal.completed_date = date.today()
        from app.events.producer import publish_savings_goal_completed
        publish_savings_goal_completed(user_id, {
            "goal_id": goal.id, "name": goal.name,
            "target_amount": float(goal.target_amount),
            "final_amount": float(goal.current_amount),
        })

    db.commit()
    db.refresh(tx)

    from app.events.producer import publish_savings_deposit
    publish_savings_deposit(user_id, {
        "goal_id": goal.id, "transaction_id": tx.id,
        "amount": float(req.amount), "current_amount": float(goal.current_amount),
        "progress": float(goal.progress),
    })
    return tx


def withdraw(db: Session, user_id: int, goal: SavingsGoal, req: WithdrawRequest) -> SavingsTransaction:
    if goal.current_amount < req.amount:
        raise ValueError(
            f"Insufficient balance: available {goal.current_amount}, requested {req.amount}"
        )
    tx = SavingsTransaction(
        goal_id=goal.id, user_id=user_id,
        amount=req.amount, transaction_type="withdrawal",
        description=req.description, notes=req.notes,
    )
    db.add(tx)
    goal.current_amount -= req.amount
    goal.progress = calc_progress(goal.current_amount, goal.target_amount)
    db.commit()
    db.refresh(tx)
    return tx


def list_transactions(
    db: Session, goal_id: int, user_id: int,
    tx_type: Optional[str] = None,
    limit: int = 50, offset: int = 0,
) -> Dict[str, Any]:
    q = db.query(SavingsTransaction).filter(
        SavingsTransaction.goal_id == goal_id,
        SavingsTransaction.user_id == user_id,
    )
    if tx_type:
        q = q.filter(SavingsTransaction.transaction_type == tx_type)
    total = q.count()
    rows = q.order_by(SavingsTransaction.transaction_date.desc()).limit(limit).offset(offset).all()
    deposits = sum(float(t.amount) for t in rows if t.transaction_type == "deposit")
    withdrawals = sum(float(t.amount) for t in rows if t.transaction_type == "withdrawal")
    return {
        "transactions": rows,
        "total": total,
        "summary": {"total_deposits": deposits, "total_withdrawals": withdrawals,
                    "net_amount": deposits - withdrawals},
    }


def goals_summary(goals: List[SavingsGoal]) -> Dict[str, Any]:
    total_target = sum(float(g.target_amount) for g in goals)
    total_saved = sum(float(g.current_amount or 0) for g in goals)
    active = sum(1 for g in goals if g.status == "active")
    completed = sum(1 for g in goals if g.status == "completed")
    return {
        "total_target": total_target,
        "total_saved": total_saved,
        "overall_progress": round(total_saved / total_target * 100, 2) if total_target else 0.0,
        "active_goals": active,
        "completed_goals": completed,
    }
