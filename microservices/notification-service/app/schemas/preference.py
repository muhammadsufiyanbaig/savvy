"""Pydantic v2 schemas for notification preferences."""

from typing import List, Optional

from pydantic import BaseModel, field_validator


class PreferenceResponse(BaseModel):
    user_id: int
    push_enabled: bool
    email_enabled: bool
    sms_enabled: bool
    in_app_enabled: bool
    expense_notifications: bool
    budget_alerts: bool
    goal_updates: bool
    recommendations: bool
    daily_reminders: bool
    weekly_summary: bool
    marketing: bool
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    device_tokens: List[str]
    email_address: Optional[str] = None
    phone_number: Optional[str] = None

    model_config = {"from_attributes": True}


class PreferenceUpdate(BaseModel):
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    expense_notifications: Optional[bool] = None
    budget_alerts: Optional[bool] = None
    goal_updates: Optional[bool] = None
    recommendations: Optional[bool] = None
    daily_reminders: Optional[bool] = None
    weekly_summary: Optional[bool] = None
    marketing: Optional[bool] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    email_address: Optional[str] = None
    phone_number: Optional[str] = None

    @field_validator("quiet_hours_start", "quiet_hours_end", mode="before")
    @classmethod
    def validate_time_format(cls, v):
        if v is None:
            return v
        # Accept HH:MM or HH:MM:SS
        parts = str(v).split(":")
        if len(parts) == 2:
            return f"{v}:00"
        if len(parts) == 3:
            return v
        raise ValueError("Time must be HH:MM or HH:MM:SS")
