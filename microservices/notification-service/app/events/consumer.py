"""Kafka consumer — daemon thread, non-fatal, handles events from other services."""

import json
import logging
import threading
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Events this service cares about
_TOPICS = [
    "financial_user.created",
    "financial_user.verification_requested",
    "financial_budget.exceeded",
    "financial_savings_goal.completed",
    "financial_recommendation.generated",
    "financial_bank_statement.processed",
]


def _handle_message(event_type: str, data: Dict[str, Any]) -> None:
    """Route event to the correct notification handler."""
    from app.core.database import SessionLocal
    from app.services import notification_service

    db = SessionLocal()
    try:
        if event_type == "user.created":
            notification_service.handle_user_created(db, data)
        elif event_type == "user.verification_requested":
            notification_service.handle_verification_requested(data)
        elif event_type == "budget.exceeded":
            notification_service.handle_budget_exceeded(db, data)
        elif event_type == "savings_goal.completed":
            notification_service.handle_goal_completed(db, data)
        elif event_type == "recommendation.generated":
            notification_service.handle_recommendation_generated(db, data)
        elif event_type == "bank_statement.processed":
            notification_service.handle_statement_processed(db, data)
    except Exception as exc:
        logger.error("Error handling event %s: %s", event_type, exc)
    finally:
        db.close()


def _consume_loop() -> None:
    try:
        from kafka import KafkaConsumer
        from app.core.config import settings

        consumer = KafkaConsumer(
            *_TOPICS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        logger.info("Kafka consumer started, topics: %s", _TOPICS)
        for msg in consumer:
            try:
                payload = msg.value
                event_type = payload.get("event_type", "")
                data = payload.get("data", payload)
                _handle_message(event_type, data)
            except Exception as exc:
                logger.warning("Bad message: %s", exc)
    except Exception as exc:
        logger.warning("Kafka consumer failed to start: %s", exc)


def start_consumer() -> None:
    """Start Kafka consumer in a daemon thread (non-fatal if Kafka unavailable)."""
    t = threading.Thread(target=_consume_loop, daemon=True, name="notification-kafka-consumer")
    t.start()
