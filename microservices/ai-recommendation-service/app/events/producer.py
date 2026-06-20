"""Kafka producer — fire-and-forget, lazy-init, non-fatal."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict

logger = logging.getLogger(__name__)

_producer = None


def _get_kafka_producer():
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
        logger.info("Kafka producer connected")
        return _producer
    except Exception as exc:
        logger.warning("Kafka producer unavailable: %s", exc)
        return None


def _publish(topic: str, payload: Dict) -> bool:
    p = _get_kafka_producer()
    if p is None:
        return False
    try:
        p.send(topic, value=payload)
        p.flush(timeout=5)
        return True
    except Exception as exc:
        logger.error("Kafka publish failed %s: %s", topic, exc)
        return False


def _event(event_type: str, user_id: int, data: Dict) -> Dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "user_id": user_id,
        "data": data,
    }


def publish_recommendation_generated(user_id: int, recommendation: Dict) -> bool:
    from app.core.config import settings
    topic = f"{settings.KAFKA_TOPIC_PREFIX}recommendation.generated"
    return _publish(topic, _event("recommendation.generated", user_id, recommendation))


def publish_investment_recommended(user_id: int, investment: Dict) -> bool:
    from app.core.config import settings
    topic = f"{settings.KAFKA_TOPIC_PREFIX}investment.recommended"
    return _publish(topic, _event("investment.recommended", user_id, investment))


def publish_insight_generated(user_id: int, insight: Dict) -> bool:
    from app.core.config import settings
    topic = f"{settings.KAFKA_TOPIC_PREFIX}insight.generated"
    return _publish(topic, _event("insight.generated", user_id, insight))
