"""Kafka producer — fire-and-forget, lazy-init, non-fatal."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_producer = None


def _get_kafka_producer():
    """Return KafkaProducer singleton or None if Kafka is unavailable."""
    global _producer
    if _producer is not None:
        return _producer

    from app.core.config import settings

    try:
        from kafka import KafkaProducer

        _producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        logger.info("Kafka producer connected to %s", settings.KAFKA_BOOTSTRAP_SERVERS)
        return _producer
    except Exception as exc:
        logger.warning("Kafka producer unavailable: %s", exc)
        return None


def _publish(topic: str, payload: Dict) -> bool:
    """Send message to Kafka. Returns True on success, False otherwise."""
    producer = _get_kafka_producer()
    if producer is None:
        return False

    try:
        producer.send(topic, value=payload)
        producer.flush(timeout=5)
        return True
    except Exception as exc:
        logger.error("Kafka publish failed on %s: %s", topic, exc)
        return False


def _base_event(event_type: str, user_id: int, data: Dict) -> Dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "user_id": user_id,
        "data": data,
    }


# ── Public publish functions ──────────────────────────────────────────────────

def publish_statement_processed(
    user_id: int,
    statement_id: str,
    processing_id: str,
    transactions: List[Dict],
    summary: Dict,
) -> bool:
    from app.core.config import settings

    topic = f"{settings.KAFKA_TOPIC_PREFIX}bank_statement.processed"
    payload = _base_event(
        "bank_statement.processed",
        user_id,
        {
            "statement_id": statement_id,
            "processing_id": processing_id,
            "transactions": transactions,
            **summary,
        },
    )
    return _publish(topic, payload)


def publish_statement_failed(
    user_id: int,
    statement_id: str,
    processing_id: str,
    error_message: str,
    processing_time_seconds: int = 0,
) -> bool:
    from app.core.config import settings

    topic = f"{settings.KAFKA_TOPIC_PREFIX}bank_statement.failed"
    payload = _base_event(
        "bank_statement.failed",
        user_id,
        {
            "statement_id": statement_id,
            "processing_id": processing_id,
            "error_message": error_message,
            "processing_time_seconds": processing_time_seconds,
        },
    )
    return _publish(topic, payload)


def publish_expense_categorized(
    user_id: int,
    statement_id: str,
    transaction: Dict,
) -> bool:
    from app.core.config import settings

    topic = f"{settings.KAFKA_TOPIC_PREFIX}expense.categorized"
    payload = _base_event(
        "expense.categorized",
        user_id,
        {"statement_id": statement_id, **transaction},
    )
    return _publish(topic, payload)
