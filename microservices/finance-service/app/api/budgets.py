"""Budget endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetListResponse, BudgetStatusResponse,
)
from app.schemas.common import MessageResponse
from app.services import budget_service

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    data: BudgetCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return budget_service.create_budget(db, user_id, data)


@router.get("", response_model=BudgetListResponse)
def list_budgets(
    period: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_period_only: bool = Query(True),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    budgets = budget_service.list_budgets(
        db, user_id,
        period=period, category=category,
        status=status, current_period_only=current_period_only,
    )
    total_alloc = sum(float(b.allocated_amount) for b in budgets)
    total_spent = sum(float(b.spent_amount or 0) for b in budgets)
    summary = {
        "total_allocated": total_alloc,
        "total_spent": total_spent,
        "total_remaining": total_alloc - total_spent,
    }
    return BudgetListResponse(budgets=budgets, total=len(budgets), summary=summary)


@router.get("/status", response_model=BudgetStatusResponse)
def get_budget_status(
    period: str = Query("monthly"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return budget_service.get_budget_status(db, user_id, period=period)


@router.get("/{budget_id}", response_model=BudgetResponse)
def get_budget(
    budget_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    budget = budget_service.get_budget(db, user_id, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    data: BudgetUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    budget = budget_service.get_budget(db, user_id, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget_service.update_budget(db, budget, data)


@router.delete("/{budget_id}", response_model=MessageResponse)
def delete_budget(
    budget_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    budget = budget_service.get_budget(db, user_id, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    budget_service.delete_budget(db, budget)
    return MessageResponse(message="Budget deleted successfully")
