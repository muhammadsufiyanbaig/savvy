"""Core notification service — DB operations and delivery orchestration."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification, NotificationPreference

_DELIVERY_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="notif-delivery")

logger = logging.getLogger(__name__)

# ── Category → ORM field mapping for preference checks ────────────────────────
_TYPE_TO_PREF = {
    "expense": "expense_notifications",
    "budget": "budget_alerts",
    "goal": "goal_updates",
    "recommendation": "recommendations",
    "reminder": "daily_reminders",
    "system": None,      # system always delivered
    "statement": None,
}


# ── Preference helpers ────────────────────────────────────────────────────────

def get_or_create_preferences(db: Session, user_id: int) -> NotificationPreference:
    pref = db.query(NotificationPreference).filter_by(user_id=user_id).first()
    if not pref:
        pref = NotificationPreference(user_id=user_id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


def update_preferences(
    db: Session, user_id: int, updates: Dict[str, Any]
) -> NotificationPreference:
    pref = get_or_create_preferences(db, user_id)
    for key, value in updates.items():
        if value is not None and hasattr(pref, key):
            setattr(pref, key, value)
    pref.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pref)
    return pref


def should_deliver(
    pref: NotificationPreference,
    notification_type: str,
    channel: str,
) -> Tuple[bool, str]:
    """Check preference gates. Returns (ok, reason)."""
    # Channel gate
    channel_map = {
        "push": pref.push_enabled,
        "email": pref.email_enabled,
        "sms": pref.sms_enabled,
        "in_app": pref.in_app_enabled,
    }
    if not channel_map.get(channel, True):
        return False, f"{channel}_disabled"

    # Category gate
    pref_field = _TYPE_TO_PREF.get(notification_type)
    if pref_field and not getattr(pref, pref_field, True):
        return False, f"{notification_type}_disabled"

    return True, "ok"


# ── Notification CRUD ─────────────────────────────────────────────────────────

def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    channel: str,
    title: str,
    message: str,
    data: Optional[Dict] = None,
    priority: int = 2,
    is_sent: bool = True,
    external_id: Optional[str] = None,
) -> Notification:
    expires = datetime.utcnow() + timedelta(days=settings.NOTIFICATION_TTL_DAYS)
    n = Notification(
        user_id=user_id,
        notification_type=notification_type,
        channel=channel,
        title=title,
        message=message,
        data=data,
        priority=priority,
        is_sent=is_sent,
        sent_at=datetime.utcnow() if is_sent else None,
        external_id=external_id,
        expires_at=expires,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def get_user_notifications(
    db: Session,
    user_id: int,
    page: int = 1,
    limit: int = 20,
    is_read: Optional[bool] = None,
    notification_type: Optional[str] = None,
    channel: Optional[str] = None,
) -> Tuple[List[Notification], int, int]:
    """Returns (items, total_count, unread_count)."""
    limit = min(limit, settings.MAX_NOTIFICATIONS_PER_PAGE)
    q = db.query(Notification).filter(Notification.user_id == user_id)

    if is_read is not None:
        q = q.filter(Notification.is_read == is_read)
    if notification_type:
        q = q.filter(Notification.notification_type == notification_type)
    if channel:
        q = q.filter(Notification.channel == channel)

    total = q.count()
    items = q.order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    unread = db.query(Notification).filter(
        Notification.user_id == user_id, Notification.is_read == False
    ).count()
    return items, total, unread


def mark_as_read(db: Session, notification_id: int, user_id: int) -> Optional[Notification]:
    n = db.query(Notification).filter_by(id=notification_id, user_id=user_id).first()
    if not n:
        return None
    if not n.is_read:
        n.is_read = True
        n.read_at = datetime.utcnow()
        db.commit()
        db.refresh(n)
    return n


def mark_all_read(db: Session, user_id: int, notification_type: Optional[str] = None) -> int:
    q = db.query(Notification).filter(
        Notification.user_id == user_id, Notification.is_read == False
    )
    if notification_type:
        q = q.filter(Notification.notification_type == notification_type)
    now = datetime.utcnow()
    count = q.update({"is_read": True, "read_at": now}, synchronize_session=False)
    db.commit()
    return count


def delete_notification(db: Session, notification_id: int, user_id: int) -> bool:
    n = db.query(Notification).filter_by(id=notification_id, user_id=user_id).first()
    if not n:
        return False
    db.delete(n)
    db.commit()
    return True


def get_unread_count(db: Session, user_id: int) -> Dict[str, Any]:
    rows = (
        db.query(Notification.notification_type, Notification.id)
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .all()
    )
    by_type: Dict[str, int] = {}
    for row in rows:
        by_type[row.notification_type] = by_type.get(row.notification_type, 0) + 1
    return {"unread_count": len(rows), "by_type": by_type}


# ── Delivery orchestration ────────────────────────────────────────────────────

def send_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    channels: List[str],
    title: str,
    message: str,
    data: Optional[Dict] = None,
    priority: int = 2,
) -> Dict[str, Any]:
    """Create DB records and deliver to all channels.

    Email and push are dispatched concurrently via a shared thread pool —
    reduces total delivery time from sum of latencies to max(latencies).
    DB writes happen first (sequential) then I/O deliveries run in parallel.
    """
    from app.services import email_service, push_service

    pref = get_or_create_preferences(db, user_id)
    notification_ids: Dict[str, int] = {}
    delivery_status: Dict[str, str] = {}

    # ── Phase 1: DB writes (must be sequential — shared SQLAlchemy session) ─────
    pending_io: Dict[str, Any] = {}  # channel → delivery kwargs

    for channel in channels:
        ok, reason = should_deliver(pref, notification_type, channel)
        if not ok:
            delivery_status[channel] = f"skipped_{reason}"
            continue

        n = create_notification(
            db, user_id, notification_type, channel, title, message, data, priority
        )
        notification_ids[channel] = n.id

        if channel == "in_app":
            delivery_status[channel] = "sent"
        elif channel == "email":
            if pref.email_address:
                pending_io["email"] = {
                    "fn": email_service.send_notification_email,
                    "args": (pref.email_address, notification_type, title, message),
                }
            else:
                delivery_status[channel] = "skipped_no_email"
        elif channel == "push":
            tokens = pref.device_tokens or []
            player_ids = [t["player_id"] if isinstance(t, dict) else t for t in tokens]
            if player_ids:
                pending_io["push"] = {
                    "fn": push_service.send_push,
                    "args": (player_ids, title, message, data),
                }
            else:
                delivery_status[channel] = "skipped_no_tokens"
        elif channel == "sms":
            delivery_status[channel] = "skipped_sms_not_implemented"

    # ── Phase 2: I/O delivery — email + push run concurrently ────────────────────
    if pending_io:
        futures = {
            _DELIVERY_POOL.submit(spec["fn"], *spec["args"]): ch
            for ch, spec in pending_io.items()
        }
        for future in as_completed(futures, timeout=15):
            ch = futures[future]
            try:
                result = future.result()
                delivery_status[ch] = "sent" if result else "failed"
            except Exception as exc:
                logger.error("Delivery failed [%s] user=%s: %s", ch, user_id, exc)
                delivery_status[ch] = "failed"

    # ── Invalidate unread count cache ─────────────────────────────────────────────
    from app.integrations import redis_client
    redis_client.cache_delete(f"unread:{user_id}")

    return {
        "notification_ids": notification_ids,
        "delivery_status": delivery_status,
    }


# ── Event-driven handlers ─────────────────────────────────────────────────────

def handle_verification_requested(event_data: Dict) -> None:
    """Send email verification link directly — no DB notification record needed."""
    from app.services import email_service

    email = event_data.get("email")
    token = event_data.get("token")
    name = event_data.get("full_name") or "there"

    if not email or not token:
        logger.warning("verification_requested missing email or token")
        return

    subject = "Verify your Savvy account"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;">
      <h2 style="color:#7c3aed;">Verify your email</h2>
      <p>Hi {name},</p>
      <p>Use the token below in the Savvy app to verify your email address.</p>
      <div style="background:#f4f4f5;border-radius:8px;padding:16px;text-align:center;
                  font-size:24px;font-weight:bold;letter-spacing:4px;color:#18181b;">
        {token[:8]}...
      </div>
      <p style="color:#71717a;font-size:13px;">
        Or call <code>POST /api/v1/users/verify-email</code> with the full token.
        This token expires in 24 hours.
      </p>
    </div>
    """
    text = f"Hi {name},\n\nVerify your Savvy email using this token:\n{token}\n\nExpires in 24 hours."
    email_service.send_email(email, subject, html, text_content=text)
    logger.info("Verification email sent to %s", email)


def handle_user_created(db: Session, event_data: Dict) -> None:
    """Welcome notification + create default preferences."""
    user_id = event_data.get("user_id")
    if not user_id:
        return
    name = event_data.get("name") or event_data.get("full_name") or "there"
    get_or_create_preferences(db, user_id)
    send_notification(
        db, user_id, "system", ["in_app"],
        title="Welcome to Savvy! 👋",
        message=f"Hi {name}! Start tracking your finances today.",
        priority=2,
    )


def handle_budget_exceeded(db: Session, event_data: Dict) -> None:
    user_id = event_data.get("user_id")
    if not user_id:
        return
    category = event_data.get("category", "your budget")
    pct = event_data.get("percentage_used", event_data.get("threshold", 80))
    send_notification(
        db, user_id, "budget", ["in_app", "push"],
        title="Budget Alert ⚠️",
        message=f"You've used {pct}% of your {category} budget.",
        data=event_data,
        priority=3,
    )


def handle_goal_completed(db: Session, event_data: Dict) -> None:
    user_id = event_data.get("user_id")
    if not user_id:
        return
    goal_name = event_data.get("goal_name", "savings goal")
    send_notification(
        db, user_id, "goal", ["in_app", "push"],
        title="Goal Achieved! 🎉",
        message=f"Congratulations! You've reached your '{goal_name}' goal!",
        data=event_data,
        priority=3,
    )


def handle_recommendation_generated(db: Session, event_data: Dict) -> None:
    user_id = event_data.get("user_id")
    if not user_id:
        return
    send_notification(
        db, user_id, "recommendation", ["in_app"],
        title="New Recommendation 💡",
        message=event_data.get("title", "A new financial recommendation is ready for you."),
        data=event_data,
        priority=2,
    )


def handle_statement_processed(db: Session, event_data: Dict) -> None:
    user_id = event_data.get("user_id")
    if not user_id:
        return
    send_notification(
        db, user_id, "statement", ["in_app"],
        title="Statement Analysis Complete 📊",
        message="Your bank statement has been analysed. Tap to view insights.",
        data=event_data,
        priority=2,
    )
