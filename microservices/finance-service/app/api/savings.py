"""Savings goals endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.savings import (
    SavingsGoalCreate, SavingsGoalUpdate, SavingsGoalResponse, SavingsGoalListResponse,
    DepositRequest, WithdrawRequest, TransactionResponse, TransactionListResponse,
)
from app.schemas.common import MessageResponse
from app.services import savings_service

router = APIRouter(prefix="/savings", tags=["Savings Goals"])


# ── Goals ────────────────────────────────────────────────────────────────────

@router.post("", response_model=SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    data: SavingsGoalCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return savings_service.create_goal(db, user_id, data)


@router.get("", response_model=SavingsGoalListResponse)
def list_goals(
    status: Optional[str] = Query(None),
    goal_type: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goals = savings_service.list_goals(
        db, user_id, status=status, goal_type=goal_type,
        sort_by=sort_by, sort_order=sort_order,
    )
    summary = savings_service.goals_summary(goals)
    return SavingsGoalListResponse(goals=goals, total=len(goals), summary=summary)


@router.get("/{goal_id}", response_model=SavingsGoalResponse)
def get_goal(
    goal_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = savings_service.get_goal(db, user_id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    return goal


@router.put("/{goal_id}", response_model=SavingsGoalResponse)
def update_goal(
    goal_id: int,
    data: SavingsGoalUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = savings_service.get_goal(db, user_id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    return savings_service.update_goal(db, goal, data)


@router.delete("/{goal_id}", response_model=MessageResponse)
def delete_goal(
    goal_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = savings_service.get_goal(db, user_id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    savings_service.delete_goal(db, goal)
    return MessageResponse(message="Savings goal deleted successfully")


# ── Transactions ─────────────────────────────────────────────────────────────

@router.post("/{goal_id}/deposit", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def deposit(
    goal_id: int,
    req: DepositRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = savings_service.get_goal(db, user_id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    if goal.status == "completed":
        raise HTTPException(status_code=400, detail="Goal already completed")
    return savings_service.deposit(db, user_id, goal, req)


@router.post("/{goal_id}/withdraw", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def withdraw(
    goal_id: int,
    req: WithdrawRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = savings_service.get_goal(db, user_id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    try:
        return savings_service.withdraw(db, user_id, goal, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{goal_id}/transactions", response_model=TransactionListResponse)
def list_transactions(
    goal_id: int,
    tx_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = savings_service.get_goal(db, user_id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    result = savings_service.list_transactions(db, goal_id, user_id, tx_type=tx_type, limit=limit, offset=offset)
    return TransactionListResponse(**result)
