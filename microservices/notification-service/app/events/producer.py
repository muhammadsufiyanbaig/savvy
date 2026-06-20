"""Kafka producer — fire-and-forget, lazy init, non-fatal."""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
_producer = None


def _get_kafka_producer():
    global _producer
    if _producer is None:
        try:
            from kafka import KafkaProducer
            from app.core.config import settings
            _producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        except Exception as exc:
            logger.warning("Kafka producer unavailable: %s", exc)
            _producer = None
    return _producer


def _publish(topic: str, payload: Dict) -> None:
    p = _get_kafka_producer()
    if not p:
        return
    try:
        p.send(topic, value=payload)
        p.flush(timeout=1)
    except Exception as exc:
        logger.warning("Kafka publish failed on %s: %s", topic, exc)


def _base(event_type: str) -> Dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
    }


def publish_notification_sent(
    notification_id: int,
    user_id: int,
    notification_type: str,
    channel: str,
    external_id: Optional[str] = None,
) -> None:
    payload = {
        **_base("notification.sent"),
        "data": {
            "notification_id": notification_id,
            "user_id": user_id,
            "notification_type": notification_type,
            "channel": channel,
            "external_id": external_id,
            "sent_at": datetime.utcnow().isoformat(),
        },
    }
    _publish("financial_notification.sent", payload)


def publish_notification_failed(
    user_id: int,
    notification_type: str,
    channel: str,
    error_message: str,
    retry_count: int = 0,
) -> None:
    payload = {
        **_base("notification.failed"),
        "data": {
            "user_id": user_id,
            "notification_type": notification_type,
            "channel": channel,
            "error_message": error_message,
            "retry_count": retry_count,
        },
    }
    _publish("financial_notification.failed", payload)
