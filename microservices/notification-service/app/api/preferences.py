"""Notification preferences endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.preference import PreferenceResponse, PreferenceUpdate
from app.services import notification_service

router = APIRouter()


@router.get("/notifications/preferences", response_model=PreferenceResponse)
def get_preferences(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    pref = notification_service.get_or_create_preferences(db, user_id)
    # Normalise device_tokens to list of strings
    tokens = pref.device_tokens or []
    player_ids = [(t["player_id"] if isinstance(t, dict) else t) for t in tokens]
    return PreferenceResponse(
        user_id=pref.user_id,
        push_enabled=pref.push_enabled,
        email_enabled=pref.email_enabled,
        sms_enabled=pref.sms_enabled,
        in_app_enabled=pref.in_app_enabled,
        expense_notifications=pref.expense_notifications,
        budget_alerts=pref.budget_alerts,
        goal_updates=pref.goal_updates,
        recommendations=pref.recommendations,
        daily_reminders=pref.daily_reminders,
        weekly_summary=pref.weekly_summary,
        marketing=pref.marketing,
        quiet_hours_enabled=pref.quiet_hours_enabled,
        quiet_hours_start=pref.quiet_hours_start,
        quiet_hours_end=pref.quiet_hours_end,
        device_tokens=player_ids,
        email_address=pref.email_address,
        phone_number=pref.phone_number,
    )


@router.put("/notifications/preferences", response_model=PreferenceResponse)
def update_preferences(
    req: PreferenceUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    pref = notification_service.update_preferences(db, user_id, updates)
    tokens = pref.device_tokens or []
    player_ids = [(t["player_id"] if isinstance(t, dict) else t) for t in tokens]
    return PreferenceResponse(
        user_id=pref.user_id,
        push_enabled=pref.push_enabled,
        email_enabled=pref.email_enabled,
        sms_enabled=pref.sms_enabled,
        in_app_enabled=pref.in_app_enabled,
        expense_notifications=pref.expense_notifications,
        budget_alerts=pref.budget_alerts,
        goal_updates=pref.goal_updates,
        recommendations=pref.recommendations,
        daily_reminders=pref.daily_reminders,
        weekly_summary=pref.weekly_summary,
        marketing=pref.marketing,
        quiet_hours_enabled=pref.quiet_hours_enabled,
        quiet_hours_start=pref.quiet_hours_start,
        quiet_hours_end=pref.quiet_hours_end,
        device_tokens=player_ids,
        email_address=pref.email_address,
        phone_number=pref.phone_number,
    )
