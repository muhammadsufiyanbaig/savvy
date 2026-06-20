"""Notification endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.notification import (
    DeleteResponse,
    DeviceTokenRequest,
    DeviceTokenResponse,
    MarkAllReadRequest,
    MarkAllReadResponse,
    MarkReadResponse,
    NotificationListResponse,
    NotificationResponse,
    SendNotificationRequest,
    SendNotificationResponse,
    UnreadCountResponse,
)
from app.services import notification_service

router = APIRouter()


# ── GET /notifications ────────────────────────────────────────────────────────

@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    is_read: Optional[bool] = Query(None),
    notification_type: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    items, total, unread = notification_service.get_user_notifications(
        db, user_id, page, limit, is_read, notification_type, channel
    )
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in items],
        total_count=total,
        unread_count=unread,
        page=page,
        limit=limit,
        has_more=(page * limit) < total,
    )


# ── GET /notifications/unread ──────────────────────────────────────────────────

@router.get("/notifications/unread", response_model=UnreadCountResponse)
def unread_count(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    from app.integrations import redis_client as rc

    cache_key = f"unread:{user_id}"
    cached = rc.cache_get(cache_key)
    if cached:
        return UnreadCountResponse(**cached)

    result = notification_service.get_unread_count(db, user_id)
    rc.cache_set(cache_key, result, ttl=60)
    return UnreadCountResponse(**result)


# ── POST /notifications/send ──────────────────────────────────────────────────

@router.post("/notifications/send", response_model=SendNotificationResponse)
def send_notification(
    req: SendNotificationRequest,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user),   # auth required; any user can call for own id
):
    result = notification_service.send_notification(
        db,
        user_id=req.user_id,
        notification_type=req.notification_type,
        channels=req.channels,
        title=req.title,
        message=req.message,
        data=req.data,
        priority=req.priority,
    )
    return SendNotificationResponse(**result)


# ── PUT /notifications/read-all ───────────────────────────────────────────────

@router.put("/notifications/read-all", response_model=MarkAllReadResponse)
def mark_all_read(
    req: MarkAllReadRequest = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    ntype = req.notification_type if req else None
    count = notification_service.mark_all_read(db, user_id, ntype)
    from app.integrations import redis_client as rc
    rc.cache_delete(f"unread:{user_id}")
    return MarkAllReadResponse(success=True, count=count)


# ── PUT /notifications/{id}/read ──────────────────────────────────────────────

@router.put("/notifications/{notification_id}/read", response_model=MarkReadResponse)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    n = notification_service.mark_as_read(db, notification_id, user_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    from app.integrations import redis_client as rc
    rc.cache_delete(f"unread:{user_id}")
    return MarkReadResponse(success=True, notification_id=n.id, read_at=n.read_at)


# ── DELETE /notifications/{id} ────────────────────────────────────────────────

@router.delete("/notifications/{notification_id}", response_model=DeleteResponse)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    ok = notification_service.delete_notification(db, notification_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return DeleteResponse(success=True, notification_id=notification_id)


# ── POST /notifications/device-token ─────────────────────────────────────────

@router.post("/notifications/device-token", response_model=DeviceTokenResponse)
def register_device_token(
    req: DeviceTokenRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    pref = notification_service.get_or_create_preferences(db, user_id)
    tokens: list = list(pref.device_tokens or [])

    # Deduplicate
    existing_ids = {
        (t["player_id"] if isinstance(t, dict) else t) for t in tokens
    }
    if req.player_id not in existing_ids:
        tokens.append({
            "player_id": req.player_id,
            "device_type": req.device_type,
            "device_model": req.device_model,
            "app_version": req.app_version,
        })
        notification_service.update_preferences(db, user_id, {"device_tokens": tokens})

    return DeviceTokenResponse(success=True, message="Device token registered")


# ── DELETE /notifications/device-token/{player_id} ───────────────────────────

@router.delete("/notifications/device-token/{player_id}", response_model=DeviceTokenResponse)
def unregister_device_token(
    player_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    pref = notification_service.get_or_create_preferences(db, user_id)
    tokens: list = list(pref.device_tokens or [])
    new_tokens = [
        t for t in tokens
        if (t["player_id"] if isinstance(t, dict) else t) != player_id
    ]
    notification_service.update_preferences(db, user_id, {"device_tokens": new_tokens})
    return DeviceTokenResponse(success=True, message="Device token removed")
