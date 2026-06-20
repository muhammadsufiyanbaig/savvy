"""Expense endpoints."""
from __future__ import annotations

import calendar
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.expense import Expense
from app.schemas.expense import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse,
    ExpenseListResponse, ExpenseSummaryResponse,
)
from app.schemas.common import MessageResponse
from app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    data: ExpenseCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return expense_service.create_expense(db, user_id, data)


@router.get("", response_model=ExpenseListResponse)
def list_expenses(
    category: Optional[str] = Query(None),
    expense_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    is_recurring: Optional[bool] = Query(None),
    min_amount: Optional[Decimal] = Query(None),
    max_amount: Optional[Decimal] = Query(None),
    payment_method: Optional[str] = Query(None),
    sort_by: str = Query("transaction_date"),
    sort_order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    expenses, total = expense_service.list_expenses(
        db, user_id,
        category=category, expense_type=expense_type,
        start_date=start_date, end_date=end_date,
        is_recurring=is_recurring,
        min_amount=min_amount, max_amount=max_amount,
        payment_method=payment_method,
        sort_by=sort_by, sort_order=sort_order,
        limit=limit, offset=offset,
    )
    total_amount = sum(float(e.amount) for e in expenses)
    summary = {"total_amount": total_amount, "count": len(expenses)}
    return ExpenseListResponse(expenses=expenses, total=total, limit=limit, offset=offset, summary=summary)


@router.get("/summary", response_model=ExpenseSummaryResponse)
def get_expense_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    return expense_service.get_expense_summary(db, user_id, start_date, end_date)


@router.get("/trend")
def get_expense_trend(
    months: int = Query(6, ge=1, le=24),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Monthly expense totals for the last N months."""
    result = []
    today = date.today()
    for i in range(months - 1, -1, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        month_start = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        month_end = date(year, month, last_day)
        total = db.query(func.sum(Expense.amount)).filter(
            Expense.user_id == user_id,
            Expense.transaction_date >= datetime.combine(month_start, datetime.min.time()),
            Expense.transaction_date <= datetime.combine(month_end, datetime.max.time()),
            Expense.deleted_at.is_(None),
        ).scalar() or 0
        result.append({
            "month": month_start.strftime("%b"),
            "year": year,
            "expenses": float(total),
            "savings": 0.0,
        })
    return {"trend": result}


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    expense = expense_service.get_expense(db, user_id, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    expense = expense_service.get_expense(db, user_id, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense_service.update_expense(db, expense, data)


@router.delete("/{expense_id}", response_model=MessageResponse)
def delete_expense(
    expense_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    expense = expense_service.get_expense(db, user_id, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    expense_service.delete_expense(db, expense)
    return MessageResponse(message="Expense deleted successfully")
