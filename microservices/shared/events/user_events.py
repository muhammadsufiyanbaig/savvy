from dataclasses import dataclass
from typing import Dict, Any, Optional
from .base import BaseEvent, EventType


@dataclass
class UserCreatedEvent(BaseEvent):
    user_id: int = None
    email: str = None
    username: str = None
    full_name: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    currency: str = "USD"

    def __post_init__(self):
        self.event_type = EventType.USER_CREATED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "country": self.country,
            "city": self.city,
            "currency": self.currency
        }


@dataclass
class UserUpdatedEvent(BaseEvent):
    user_id: int = None
    updated_fields: Dict[str, Any] = None

    def __post_init__(self):
        self.event_type = EventType.USER_UPDATED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "updated_fields": self.updated_fields
        }


@dataclass
class UserDeletedEvent(BaseEvent):
    user_id: int = None

    def __post_init__(self):
        self.event_type = EventType.USER_DELETED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id
        }


@dataclass
class UserVerificationRequestedEvent(BaseEvent):
    user_id: int = None
    email: str = None
    token: str = None
    full_name: Optional[str] = None

    def __post_init__(self):
        self.event_type = EventType.USER_VERIFICATION_REQUESTED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "token": self.token,
            "full_name": self.full_name or "there",
        }
