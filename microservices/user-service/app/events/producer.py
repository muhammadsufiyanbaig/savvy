import sys
import os

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))

from events import UserCreatedEvent, UserUpdatedEvent, UserDeletedEvent, UserVerificationRequestedEvent
from utils import EventProducer
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class UserEventProducer:
    def __init__(self):
        self.producer = EventProducer(
            bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS],
            topic_prefix=settings.KAFKA_TOPIC_PREFIX
        )

    def publish_user_created(self, user_data: dict):
        """Publish user created event"""
        event = UserCreatedEvent(
            user_id=user_data["id"],
            email=user_data["email"],
            username=user_data["username"],
            full_name=user_data.get("full_name"),
            country=user_data.get("country"),
            city=user_data.get("city"),
            currency=user_data.get("currency", "USD")
        )
        self.producer.publish_event(event)
        logger.info(f"Published user created event for user_id: {user_data['id']}")

    def publish_user_updated(self, user_id: int, updated_fields: dict):
        """Publish user updated event"""
        event = UserUpdatedEvent(
            user_id=user_id,
            updated_fields=updated_fields
        )
        self.producer.publish_event(event)
        logger.info(f"Published user updated event for user_id: {user_id}")

    def publish_user_deleted(self, user_id: int):
        """Publish user deleted event"""
        event = UserDeletedEvent(user_id=user_id)
        self.producer.publish_event(event)
        logger.info(f"Published user deleted event for user_id: {user_id}")

    def publish_verification_requested(self, user_id: int, email: str, token: str, full_name: str = None):
        """Publish email verification request — notification-service sends the email."""
        event = UserVerificationRequestedEvent(
            user_id=user_id,
            email=email,
            token=token,
            full_name=full_name,
        )
        self.producer.publish_event(event)
        logger.info(f"Published verification_requested for user_id: {user_id}")
