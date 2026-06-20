from dataclasses import dataclass
from typing import Dict, Any, Optional
from .base import BaseEvent, EventType


@dataclass
class NotificationSendEvent(BaseEvent):
    user_id: int = None
    notification_type: str = None
    channel: str = None
    title: str = None
    message: str = None
    action_url: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None
    priority: str = "normal"

    def __post_init__(self):
        self.event_type = EventType.NOTIFICATION_SEND

    def _get_data(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "channel": self.channel,
            "title": self.title,
            "message": self.message,
            "action_url": self.action_url,
            "action_data": self.action_data,
            "priority": self.priority
        }


@dataclass
class NotificationSentEvent(BaseEvent):
    notification_id: int = None
    user_id: int = None
    notification_type: str = None
    channel: str = None
    external_id: Optional[str] = None
    delivery_status: str = "sent"

    def __post_init__(self):
        self.event_type = EventType.NOTIFICATION_SENT

    def _get_data(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "channel": self.channel,
            "external_id": self.external_id,
            "delivery_status": self.delivery_status
        }


@dataclass
class NotificationFailedEvent(BaseEvent):
    user_id: int = None
    notification_type: str = None
    channel: str = None
    error_message: str = None
    retry_count: int = 0

    def __post_init__(self):
        self.event_type = EventType.NOTIFICATION_FAILED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "channel": self.channel,
            "error_message": self.error_message,
            "retry_count": self.retry_count
        }
