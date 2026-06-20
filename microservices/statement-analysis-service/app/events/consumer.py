"""Kafka consumer daemon thread — listens for bank_statement.uploaded events."""

import json
import logging
import threading
import uuid
from typing import Dict

logger = logging.getLogger(__name__)


def _handle_message(event_data: Dict) -> None:
    """Process a single bank_statement.uploaded event."""
    from app.services import statement_processor

    data = event_data.get("data", event_data)  # support both wrapped and flat
    statement_id = data.get("statement_id", "unknown")
    processing_id = str(uuid.uuid4())
    logger.info("Consumer received statement upload event: %s", statement_id)

    try:
        statement_processor.process_statement(data, processing_id)
    except Exception as exc:
        logger.error("Consumer handler error for %s: %s", statement_id, exc)


def _consume_loop() -> None:
    from app.core.config import settings

    try:
        from kafka import KafkaConsumer

        topic = f"{settings.KAFKA_TOPIC_PREFIX}bank_statement.uploaded"
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        logger.info("Kafka consumer started on topic: %s", topic)
        for message in consumer:
            try:
                _handle_message(message.value)
            except Exception as exc:
                logger.error("Consumer message error: %s", exc)
    except Exception as exc:
        logger.warning(
            "Kafka consumer failed to start: %s — event-driven processing disabled", exc
        )


def start_consumer() -> None:
    """Launch consumer in a daemon thread. Non-blocking, non-fatal."""
    thread = threading.Thread(target=_consume_loop, name="kafka-consumer", daemon=True)
    thread.start()
    logger.info("Kafka consumer daemon thread started")
