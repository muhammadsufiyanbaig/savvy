"""Bank account endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.account import (
    BankAccountCreate, BankAccountUpdate, BankAccountResponse,
    BankAccountListResponse, AccountDeleteResponse,
)
from app.schemas.common import MessageResponse
from app.services import account_service

router = APIRouter(prefix="/accounts", tags=["Bank Accounts"])


@router.post("", response_model=BankAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    data: BankAccountCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return account_service.create_account(db, user_id, data)


@router.get("", response_model=BankAccountListResponse)
def list_accounts(
    account_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    accounts = account_service.list_accounts(db, user_id, account_type=account_type, is_active=is_active)
    summary = account_service.accounts_summary(accounts)
    return BankAccountListResponse(accounts=accounts, total=len(accounts), summary=summary)


@router.get("/{account_id}", response_model=BankAccountResponse)
def get_account(
    account_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    account = account_service.get_account(db, user_id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    # Enrich with statement count + latest statement date
    from app.models.statement import BankStatement
    stmt_count = db.query(BankStatement).filter(BankStatement.account_id == account_id).count()
    latest = (
        db.query(BankStatement)
        .filter(BankStatement.account_id == account_id)
        .order_by(BankStatement.statement_period_end.desc())
        .first()
    )

    resp = BankAccountResponse.model_validate(account)
    resp.statement_count = stmt_count
    resp.latest_statement_date = (
        latest.statement_period_end.isoformat() if latest and latest.statement_period_end else None
    )
    return resp


@router.put("/{account_id}", response_model=BankAccountResponse)
def update_account(
    account_id: int,
    data: BankAccountUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    account = account_service.get_account(db, user_id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    return account_service.update_account(db, account, data)


@router.delete("/{account_id}", response_model=AccountDeleteResponse)
def delete_account(
    account_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    account = account_service.get_account(db, user_id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    statements_deleted = account_service.delete_account(db, account)
    return AccountDeleteResponse(
        message="Bank account deleted successfully",
        deleted_account_id=account_id,
        statements_deleted=statements_deleted,
    )
