"""
Finance Service — Kafka event producer.
All publish calls are fire-and-forget; failures are logged, never raised.
"""
from __future__ import annotations

import logging
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared"))

logger = logging.getLogger(__name__)

_producer = None


def _get_producer():
    global _producer
    if _producer is None:
        try:
            from utils import EventProducer
            from app.core.config import settings
            _producer = EventProducer(
                bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS],
                topic_prefix=settings.KAFKA_TOPIC_PREFIX,
            )
        except Exception as exc:
            logger.warning("Kafka producer init failed (non-fatal): %s", exc)
    return _producer


def _publish(event_type: str, user_id: int, data: dict) -> None:
    p = _get_producer()
    if p is None:
        return
    try:
        from kafka import KafkaProducer
        import json
        from app.core.config import settings
        topic = f"{settings.KAFKA_TOPIC_PREFIX}{event_type}"
        payload = {
            "event_type": event_type,
            "user_id": user_id,
            "data": data,
        }
        p.producer.send(topic, key=str(user_id), value=payload)
    except Exception as exc:
        logger.error("Kafka publish [%s] failed: %s", event_type, exc)


# ── Public publish functions ────────────────────────────────────────────────

def publish_expense_created(user_id: int, data: dict) -> None:
    _publish("expense.created", user_id, data)


def publish_expense_updated(user_id: int, data: dict) -> None:
    _publish("expense.updated", user_id, data)


def publish_expense_deleted(user_id: int, expense_id: int) -> None:
    _publish("expense.deleted", user_id, {"expense_id": expense_id})


def publish_savings_goal_created(user_id: int, data: dict) -> None:
    _publish("savings_goal.created", user_id, data)


def publish_savings_goal_completed(user_id: int, data: dict) -> None:
    _publish("savings_goal.completed", user_id, data)


def publish_savings_deposit(user_id: int, data: dict) -> None:
    _publish("savings.deposit", user_id, data)


def publish_budget_created(user_id: int, data: dict) -> None:
    _publish("budget.created", user_id, data)


def publish_budget_exceeded(user_id: int, data: dict) -> None:
    _publish("budget.exceeded", user_id, data)


def publish_zakat_calculated(user_id: int, data: dict) -> None:
    _publish("zakat.calculated", user_id, data)


def publish_qurbani_goal_created(user_id: int, data: dict) -> None:
    _publish("qurbani.goal_created", user_id, data)
