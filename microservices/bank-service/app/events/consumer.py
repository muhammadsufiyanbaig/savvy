"""Kafka consumer — handles user.deleted and bank_statement.processed."""
from __future__ import annotations

import json
import logging
import threading
from decimal import Decimal
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


def _handle_user_deleted(data: Dict[str, Any]) -> None:
    """Delete all accounts (+ cascade statements) for deleted user."""
    user_id = data.get("user_id")
    if not user_id:
        return
    try:
        from app.core.database import SessionLocal
        from app.models.account import BankAccount
        from app.models.statement import BankStatement
        from app.services import s3_service

        db = SessionLocal()
        try:
            # S3 cleanup first
            statements = db.query(BankStatement).filter(
                BankStatement.user_id == user_id,
                BankStatement.s3_key.isnot(None),
            ).all()
            for stmt in statements:
                s3_service.delete_file(stmt.s3_key)

            # Hard-delete all accounts (cascade deletes statements)
            db.query(BankAccount).filter(BankAccount.user_id == user_id).delete()
            db.commit()
            logger.info("Deleted all bank data for user=%s", user_id)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Error handling user.deleted for user=%s: %s", user_id, exc)


def _handle_statement_processed(data: Dict[str, Any]) -> None:
    """Update statement processing result after Statement Analysis finishes."""
    statement_id = data.get("statement_id")
    if not statement_id:
        return
    try:
        from app.core.database import SessionLocal
        from app.services.statement_service import update_processing_result

        db = SessionLocal()
        try:
            update_processing_result(
                db=db,
                statement_id=int(statement_id),
                status=data.get("status", "processed"),
                error=data.get("error"),
                total_transactions=data.get("total_transactions"),
                total_income=Decimal(str(data["total_income"])) if data.get("total_income") else None,
                total_expenses=Decimal(str(data["total_expenses"])) if data.get("total_expenses") else None,
            )
            logger.info("Statement %s processing result updated", statement_id)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Error handling bank_statement.processed: %s", exc)


_HANDLERS = {
    f"{settings.KAFKA_TOPIC_PREFIX}user.deleted": _handle_user_deleted,
    f"{settings.KAFKA_TOPIC_PREFIX}bank_statement.processed": _handle_statement_processed,
}


def _run_consumer() -> None:
    try:
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(
            *_HANDLERS.keys(),
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        logger.info("Kafka consumer started, topics: %s", list(_HANDLERS.keys()))
        for message in consumer:
            try:
                handler = _HANDLERS.get(message.topic)
                if handler:
                    payload = message.value
                    handler(payload.get("data", payload))
            except Exception as exc:
                logger.error("Consumer message error: %s", exc)
    except Exception as exc:
        logger.warning("Kafka consumer failed to start (non-fatal): %s", exc)


def start_consumer() -> threading.Thread:
    t = threading.Thread(target=_run_consumer, daemon=True, name="bank-kafka-consumer")
    t.start()
    return t
