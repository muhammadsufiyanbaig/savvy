"""Kafka event producer — fire-and-forget."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)

_producer = None


def _get_producer():
    global _producer
    if _producer is not None:
        return _producer
    try:
        from kafka import KafkaProducer as _KP
        _producer = _KP(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        return _producer
    except Exception as exc:
        logger.warning("Kafka producer init failed (non-fatal): %s", exc)
        return None


def _publish(topic_suffix: str, user_id: int, data: Dict[str, Any]) -> None:
    topic = f"{settings.KAFKA_TOPIC_PREFIX}{topic_suffix}"
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": topic_suffix,
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "data": data,
    }
    producer = _get_producer()
    if producer is None:
        logger.warning("Kafka unavailable — skipping event: %s", topic)
        return
    try:
        producer.send(topic, payload)
    except Exception as exc:
        logger.error("Kafka publish failed for %s: %s", topic, exc)


def publish_account_added(user_id: int, data: Dict[str, Any]) -> None:
    _publish("bank_account.added", user_id, data)


def publish_account_updated(user_id: int, data: Dict[str, Any]) -> None:
    _publish("bank_account.updated", user_id, data)


def publish_account_deleted(user_id: int, data: Dict[str, Any]) -> None:
    _publish("bank_account.deleted", user_id, data)


def publish_statement_uploaded(user_id: int, data: Dict[str, Any]) -> None:
    _publish("bank_statement.uploaded", user_id, data)
