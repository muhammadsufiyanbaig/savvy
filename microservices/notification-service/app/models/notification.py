"""SQLAlchemy ORM models for notifications and preferences."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    notification_type = Column(String(50), nullable=False)   # expense|budget|goal|recommendation|reminder|system
    channel = Column(String(20), nullable=False, default="in_app")  # push|email|sms|in_app
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)

    # Delivery tracking
    is_sent = Column(Boolean, default=True)
    is_read = Column(Boolean, default=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    # Priority: 1=low, 2=medium, 3=high, 4=urgent
    priority = Column(Integer, default=2)

    # External delivery ID (OneSignal, SMTP message-id, etc.)
    external_id = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)

    # Channel toggles
    push_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    in_app_enabled = Column(Boolean, default=True)

    # Category toggles
    expense_notifications = Column(Boolean, default=True)
    budget_alerts = Column(Boolean, default=True)
    goal_updates = Column(Boolean, default=True)
    recommendations = Column(Boolean, default=True)
    daily_reminders = Column(Boolean, default=True)
    weekly_summary = Column(Boolean, default=True)
    marketing = Column(Boolean, default=False)

    # Quiet hours
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String(8), default="22:00:00")  # "HH:MM:SS"
    quiet_hours_end = Column(String(8), default="08:00:00")

    # Push device tokens (OneSignal player IDs)
    device_tokens = Column(JSON, default=list)

    # Contact info for email/sms delivery
    email_address = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
