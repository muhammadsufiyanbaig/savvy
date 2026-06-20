"""
Finance Service — Kafka event consumer.
Handles: bank_statement.processed, user.deleted
Runs in a background thread started by the lifespan hook.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


def _handle_bank_statement_processed(event: dict) -> None:
    """Create expenses from AI-analysed bank statement transactions."""
    from app.core.database import SessionLocal
    from app.services import expense_service as svc
    from app.schemas.expense import ExpenseCreate

    user_id = event.get("user_id")
    transactions = event.get("data", {}).get("transactions", [])
    if not user_id or not transactions:
        return

    db = SessionLocal()
    try:
        for tx in transactions:
            try:
                data = ExpenseCreate(
                    amount=tx["amount"],
                    currency=tx.get("currency", "USD"),
                    category=tx.get("category", "Other"),
                    expense_type=tx.get("expense_type", "variable"),
                    description=f"Bank transaction: {tx.get('description', '')}",
                    merchant_name=tx.get("merchant"),
                    payment_method="bank_transfer",
                    transaction_date=tx["date"],
                    created_from="bank_statement",
                )
                svc.create_expense(db, user_id, data)
            except Exception as exc:
                logger.error("Failed to import tx from statement: %s", exc)
        db.commit()
        logger.info("Imported %d transactions for user %s", len(transactions), user_id)
    except Exception as exc:
        logger.error("bank_statement.processed handler error: %s", exc)
        db.rollback()
    finally:
        db.close()


def _handle_user_deleted(event: dict) -> None:
    """Remove all financial data when user account is deleted."""
    from app.core.database import SessionLocal
    from app.models.expense import Expense
    from app.models.savings import SavingsGoal
    from app.models.cash_savings import CashSavings
    from app.models.budget import Budget
    from app.models.spending_limit import SpendingLimit
    from app.models.zakat import ZakatRecord
    from app.models.qurbani import QurbaniSavings

    user_id = event.get("user_id")
    if not user_id:
        return

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        db.query(Expense).filter(Expense.user_id == user_id).update({"deleted_at": now})
        for Model in (SavingsGoal, CashSavings, Budget, SpendingLimit, ZakatRecord, QurbaniSavings):
            db.query(Model).filter(Model.user_id == user_id).delete()
        db.commit()
        logger.info("Purged financial data for user %s", user_id)
    except Exception as exc:
        logger.error("user.deleted handler error: %s", exc)
        db.rollback()
    finally:
        db.close()


def start_consumer() -> threading.Thread:
    """Start the Kafka consumer in a daemon thread. Non-fatal if Kafka is down."""

    def _run():
        try:
            from kafka import KafkaConsumer
            import json
            from app.core.config import settings

            consumer = KafkaConsumer(
                f"{settings.KAFKA_TOPIC_PREFIX}bank_statement.processed",
                f"{settings.KAFKA_TOPIC_PREFIX}user.deleted",
                bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS],
                group_id=settings.KAFKA_GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )
            logger.info("Finance consumer started")
            for msg in consumer:
                event = msg.value
                etype = event.get("event_type", "")
                try:
                    if etype == "bank_statement.processed":
                        _handle_bank_statement_processed(event)
                    elif etype == "user.deleted":
                        _handle_user_deleted(event)
                except Exception as exc:
                    logger.error("Consumer handler error [%s]: %s", etype, exc)
        except Exception as exc:
            logger.warning("Finance consumer failed to start (non-fatal): %s", exc)

    t = threading.Thread(target=_run, daemon=True, name="finance-consumer")
    t.start()
    return t
