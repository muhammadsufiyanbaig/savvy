"""Kafka consumer daemon — reacts to finance/user events."""

import json
import logging
import threading
from typing import Dict

logger = logging.getLogger(__name__)


def _handle_user_created(data: Dict) -> None:
    """Generate onboarding recommendations for new user."""
    user_id = data.get("user_id") or data.get("id")
    if not user_id:
        return
    try:
        from app.services import recommendation_service
        from app.events import producer
        recs = recommendation_service.rule_based_recommendations(
            ["savings", "budget"],
            {"monthly_income": 0},
        )
        for rec in recs[:2]:
            producer.publish_recommendation_generated(user_id, rec)
        logger.info("Onboarding recommendations published for user %s", user_id)
    except Exception as exc:
        logger.error("handle_user_created error: %s", exc)


def _handle_expense_created(data: Dict) -> None:
    """Check if new expense triggers a spending insight."""
    user_id = data.get("user_id")
    category = data.get("category", "Other")
    amount = float(data.get("amount", 0))
    if not user_id or amount <= 0:
        return
    try:
        from app.events import producer
        from app.utils.helpers import gen_id, now_iso
        if amount > 200:
            insight = {
                "id": gen_id("ins"),
                "type": "spending_alert",
                "title": f"Large {category} Transaction",
                "message": f"${amount:.2f} spent on {category}. Consider reviewing budget.",
                "priority": "medium",
                "is_urgent": False,
                "supporting_data": {"amount": amount, "category": category},
            }
            producer.publish_insight_generated(user_id, insight)
    except Exception as exc:
        logger.error("handle_expense_created error: %s", exc)


def _handle_budget_exceeded(data: Dict) -> None:
    """Publish corrective recommendation when budget is exceeded."""
    user_id = data.get("user_id")
    category = data.get("category", "Unknown")
    exceeded_by = float(data.get("exceeded_by", 0))
    if not user_id:
        return
    try:
        from app.events import producer
        from app.utils.helpers import gen_id
        rec = {
            "id": gen_id("rec"),
            "type": "budget",
            "title": f"Budget Exceeded: {category}",
            "description": f"You have exceeded your {category} budget by ${exceeded_by:.2f}.",
            "recommended_action": "Review and reduce spending in this category immediately.",
            "expected_benefit": "Prevent further budget overrun.",
            "risk_level": "low",
            "confidence_score": 0.90,
            "priority": "high",
        }
        producer.publish_recommendation_generated(user_id, rec)
    except Exception as exc:
        logger.error("handle_budget_exceeded error: %s", exc)


_HANDLERS = {
    "user.created": lambda d: _handle_user_created(d),
    "expense.created": lambda d: _handle_expense_created(d),
    "savings_goal.created": lambda d: None,  # future
    "budget.exceeded": lambda d: _handle_budget_exceeded(d),
}


def _handle_message(event: Dict) -> None:
    event_type = event.get("event_type", "")
    # Strip prefix if present
    for key in _HANDLERS:
        if event_type.endswith(key):
            _HANDLERS[key](event.get("data", event))
            return
    logger.debug("Unhandled event type: %s", event_type)


def _consume_loop() -> None:
    from app.core.config import settings
    try:
        from kafka import KafkaConsumer
        topics = [
            f"{settings.KAFKA_TOPIC_PREFIX}user.created",
            f"{settings.KAFKA_TOPIC_PREFIX}expense.created",
            f"{settings.KAFKA_TOPIC_PREFIX}savings_goal.created",
            f"{settings.KAFKA_TOPIC_PREFIX}budget.exceeded",
        ]
        consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        logger.info("Kafka consumer started on %d topics", len(topics))
        for message in consumer:
            try:
                _handle_message(message.value)
            except Exception as exc:
                logger.error("Consumer message error: %s", exc)
    except Exception as exc:
        logger.warning("Kafka consumer failed to start: %s — event-driven mode disabled", exc)


def start_consumer() -> None:
    thread = threading.Thread(target=_consume_loop, name="ai-kafka-consumer", daemon=True)
    thread.start()
    logger.info("AI service Kafka consumer daemon started")
