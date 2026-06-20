"""Pydantic v2 schemas for notification endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator


# ── Request schemas ───────────────────────────────────────────────────────────

class SendNotificationRequest(BaseModel):
    user_id: int
    notification_type: str
    channels: List[str] = ["in_app"]
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    priority: int = 2

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        return max(1, min(4, v))

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: List[str]) -> List[str]:
        valid = {"push", "email", "sms", "in_app"}
        return [c for c in v if c in valid] or ["in_app"]

    @field_validator("notification_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid = {"expense", "budget", "goal", "recommendation", "reminder", "system", "statement"}
        return v if v in valid else "system"


class MarkAllReadRequest(BaseModel):
    notification_type: Optional[str] = None


class DeviceTokenRequest(BaseModel):
    player_id: str
    device_type: str = "unknown"   # ios|android|web|unknown
    device_model: Optional[str] = None
    app_version: Optional[str] = None


# ── Response schemas ──────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    notification_type: str
    channel: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    is_read: bool
    is_sent: bool
    priority: int
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total_count: int
    unread_count: int
    page: int
    limit: int
    has_more: bool


class UnreadCountResponse(BaseModel):
    unread_count: int
    by_type: Dict[str, int]


class MarkReadResponse(BaseModel):
    success: bool
    notification_id: int
    read_at: Optional[datetime] = None


class MarkAllReadResponse(BaseModel):
    success: bool
    count: int


class DeleteResponse(BaseModel):
    success: bool
    notification_id: int


class SendNotificationResponse(BaseModel):
    success: bool = True
    notification_ids: Dict[str, int]        # channel → db id
    delivery_status: Dict[str, str]         # channel → "sent"|"queued"|"skipped"|"failed"
    message: str = "Notification queued for delivery"


class DeviceTokenResponse(BaseModel):
    success: bool
    message: str
