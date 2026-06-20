"""Bank account service."""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.account import BankAccount
from app.models.statement import BankStatement
from app.schemas.account import BankAccountCreate, BankAccountUpdate

logger = logging.getLogger(__name__)


def create_account(db: Session, user_id: int, data: BankAccountCreate) -> BankAccount:
    # Enforce single primary — demote existing primary if new one flagged
    if data.is_primary:
        _demote_primary(db, user_id)

    account = BankAccount(
        user_id=user_id,
        account_name=data.account_name,
        bank_name=data.bank_name,
        account_number=data.account_number,
        account_type=data.account_type,
        balance=data.balance,
        currency=data.currency,
        credit_limit=data.credit_limit,
        interest_rate=data.interest_rate,
        purpose=data.purpose,
        notes=data.notes,
        is_primary=data.is_primary,
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    try:
        from app.events.producer import publish_account_added
        publish_account_added(user_id, {
            "account_id": account.id,
            "bank_name": account.bank_name,
            "account_name": account.account_name,
            "account_type": account.account_type,
            "balance": float(account.balance),
            "currency": account.currency,
        })
    except Exception as exc:
        logger.warning("Kafka publish failed (non-fatal): %s", exc)

    logger.info("Account created: id=%s user=%s type=%s", account.id, user_id, account.account_type)
    return account


def get_account(db: Session, user_id: int, account_id: int) -> Optional[BankAccount]:
    return db.query(BankAccount).filter(
        BankAccount.id == account_id,
        BankAccount.user_id == user_id,
    ).first()


def list_accounts(
    db: Session, user_id: int,
    account_type: Optional[str] = None,
    is_active: Optional[bool] = True,
) -> List[BankAccount]:
    q = db.query(BankAccount).filter(BankAccount.user_id == user_id)
    if account_type:
        q = q.filter(BankAccount.account_type == account_type)
    if is_active is not None:
        q = q.filter(BankAccount.is_active == is_active)
    return q.order_by(BankAccount.is_primary.desc(), BankAccount.created_at).all()


def update_account(db: Session, account: BankAccount, data: BankAccountUpdate) -> BankAccount:
    changed = data.model_dump(exclude_unset=True)

    # Enforce single primary
    if changed.get("is_primary") is True:
        _demote_primary(db, account.user_id, exclude_id=account.id)

    for field, val in changed.items():
        setattr(account, field, val)

    account.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(account)

    try:
        from app.events.producer import publish_account_updated
        publish_account_updated(account.user_id, {
            "account_id": account.id,
            "updated_fields": changed,
        })
    except Exception as exc:
        logger.warning("Kafka publish failed (non-fatal): %s", exc)

    return account


def delete_account(db: Session, account: BankAccount) -> int:
    """Delete account + all associated statements (cascade). Returns count of statements deleted."""
    stmt_count = db.query(BankStatement).filter(
        BankStatement.account_id == account.id
    ).count()

    # S3 cleanup (non-fatal)
    _cleanup_s3_for_account(db, account.id)

    db.delete(account)
    db.commit()
    return stmt_count


def accounts_summary(accounts: List[BankAccount]) -> Dict[str, Any]:
    """Net worth summary across all accounts."""
    total = sum(float(a.balance) for a in accounts)
    by_type: Dict[str, float] = {}
    for a in accounts:
        by_type[a.account_type] = by_type.get(a.account_type, 0.0) + float(a.balance)
    return {
        "total_balance": round(total, 2),
        "total_accounts": len(accounts),
        **{f"{t}_balance": round(v, 2) for t, v in by_type.items()},
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _demote_primary(db: Session, user_id: int, exclude_id: Optional[int] = None) -> None:
    """Unset is_primary for all user accounts (optionally excluding one)."""
    q = db.query(BankAccount).filter(
        BankAccount.user_id == user_id,
        BankAccount.is_primary == True,  # noqa: E712
    )
    if exclude_id:
        q = q.filter(BankAccount.id != exclude_id)
    q.update({"is_primary": False}, synchronize_session=False)


def _cleanup_s3_for_account(db: Session, account_id: int) -> None:
    """Delete S3 files for all statements of an account (non-fatal)."""
    try:
        from app.services import s3_service
        statements = db.query(BankStatement).filter(
            BankStatement.account_id == account_id,
            BankStatement.s3_key.isnot(None),
        ).all()
        for stmt in statements:
            s3_service.delete_file(stmt.s3_key)
    except Exception as exc:
        logger.warning("S3 cleanup failed (non-fatal): %s", exc)
