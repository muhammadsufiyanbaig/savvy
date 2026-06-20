"""Service-layer and model tests."""

import pytest
from datetime import datetime, timedelta


# ── Fixtures helpers ──────────────────────────────────────────────────────────

def _make_notification(db, user_id=1, ntype="system", is_read=False, priority=2):
    from app.models.notification import Notification
    n = Notification(
        user_id=user_id, notification_type=ntype, channel="in_app",
        title="Test", message="Msg", is_sent=True, is_read=is_read,
        priority=priority, expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


# ── Preferences ───────────────────────────────────────────────────────────────

class TestPreferences:
    def test_creates_default_prefs(self, db):
        from app.services.notification_service import get_or_create_preferences
        pref = get_or_create_preferences(db, user_id=42)
        assert pref.user_id == 42
        assert pref.push_enabled is True
        assert pref.in_app_enabled is True
        assert pref.marketing is False

    def test_idempotent_create(self, db):
        from app.services.notification_service import get_or_create_preferences
        p1 = get_or_create_preferences(db, user_id=10)
        p2 = get_or_create_preferences(db, user_id=10)
        assert p1.id == p2.id

    def test_update_preferences(self, db):
        from app.services.notification_service import get_or_create_preferences, update_preferences
        get_or_create_preferences(db, user_id=5)
        pref = update_preferences(db, 5, {"push_enabled": False, "marketing": True})
        assert pref.push_enabled is False
        assert pref.marketing is True

    def test_update_ignores_unknown_fields(self, db):
        from app.services.notification_service import get_or_create_preferences, update_preferences
        get_or_create_preferences(db, user_id=6)
        pref = update_preferences(db, 6, {"nonexistent_field": True})
        assert pref is not None  # no crash


# ── should_deliver ────────────────────────────────────────────────────────────

class TestShouldDeliver:
    def _pref(self, db, **kwargs):
        from app.services.notification_service import get_or_create_preferences, update_preferences
        get_or_create_preferences(db, user_id=99)
        return update_preferences(db, 99, kwargs)

    def test_in_app_always_ok_by_default(self, db):
        from app.services.notification_service import should_deliver
        pref = self._pref(db)
        ok, reason = should_deliver(pref, "system", "in_app")
        assert ok is True

    def test_push_disabled_blocks(self, db):
        from app.services.notification_service import should_deliver
        pref = self._pref(db, push_enabled=False)
        ok, reason = should_deliver(pref, "system", "push")
        assert ok is False
        assert "disabled" in reason

    def test_category_disabled_blocks(self, db):
        from app.services.notification_service import should_deliver
        pref = self._pref(db, budget_alerts=False)
        ok, reason = should_deliver(pref, "budget", "in_app")
        assert ok is False

    def test_system_always_delivers(self, db):
        from app.services.notification_service import should_deliver
        # system has no category pref — always ok
        pref = self._pref(db)
        ok, _ = should_deliver(pref, "system", "in_app")
        assert ok is True

    def test_sms_disabled_by_default(self, db):
        from app.services.notification_service import should_deliver
        pref = self._pref(db)
        ok, reason = should_deliver(pref, "system", "sms")
        assert ok is False


# ── Notification CRUD ─────────────────────────────────────────────────────────

class TestCreateNotification:
    def test_creates_record(self, db):
        from app.services.notification_service import create_notification
        n = create_notification(db, 1, "budget", "in_app", "Title", "Message")
        assert n.id is not None
        assert n.user_id == 1
        assert n.is_read is False
        assert n.is_sent is True
        assert n.expires_at is not None

    def test_data_stored_as_json(self, db):
        from app.services.notification_service import create_notification
        n = create_notification(db, 1, "budget", "in_app", "T", "M", data={"k": "v"})
        assert n.data == {"k": "v"}

    def test_priority_stored(self, db):
        from app.services.notification_service import create_notification
        n = create_notification(db, 1, "system", "in_app", "T", "M", priority=4)
        assert n.priority == 4


class TestGetUserNotifications:
    def test_returns_user_only(self, db):
        from app.services.notification_service import get_user_notifications
        _make_notification(db, user_id=1)
        _make_notification(db, user_id=2)
        items, total, unread = get_user_notifications(db, 1)
        assert total == 1
        assert all(n.user_id == 1 for n in items)

    def test_filter_by_read_status(self, db):
        from app.services.notification_service import get_user_notifications
        _make_notification(db, user_id=1, is_read=False)
        _make_notification(db, user_id=1, is_read=True)
        _, total_unread, _ = get_user_notifications(db, 1, is_read=False)
        _, total_read, _ = get_user_notifications(db, 1, is_read=True)
        assert total_unread == 1
        assert total_read == 1

    def test_unread_count_in_result(self, db):
        from app.services.notification_service import get_user_notifications
        _make_notification(db, user_id=1, is_read=False)
        _make_notification(db, user_id=1, is_read=True)
        _, _, unread = get_user_notifications(db, 1)
        assert unread == 1

    def test_pagination(self, db):
        from app.services.notification_service import get_user_notifications
        for _ in range(5):
            _make_notification(db, user_id=1)
        items, total, _ = get_user_notifications(db, 1, page=1, limit=3)
        assert total == 5
        assert len(items) == 3


class TestMarkAsRead:
    def test_marks_read(self, db):
        from app.services.notification_service import mark_as_read
        n = _make_notification(db, user_id=1, is_read=False)
        updated = mark_as_read(db, n.id, user_id=1)
        assert updated.is_read is True
        assert updated.read_at is not None

    def test_wrong_user_returns_none(self, db):
        from app.services.notification_service import mark_as_read
        n = _make_notification(db, user_id=1)
        result = mark_as_read(db, n.id, user_id=2)
        assert result is None

    def test_idempotent(self, db):
        from app.services.notification_service import mark_as_read
        n = _make_notification(db, user_id=1)
        mark_as_read(db, n.id, 1)
        updated = mark_as_read(db, n.id, 1)
        assert updated.is_read is True


class TestMarkAllRead:
    def test_marks_all(self, db):
        from app.services.notification_service import mark_all_read
        _make_notification(db, user_id=1, is_read=False)
        _make_notification(db, user_id=1, is_read=False)
        count = mark_all_read(db, 1)
        assert count == 2

    def test_filter_by_type(self, db):
        from app.services.notification_service import mark_all_read
        _make_notification(db, user_id=1, ntype="budget")
        _make_notification(db, user_id=1, ntype="goal")
        count = mark_all_read(db, 1, notification_type="budget")
        assert count == 1

    def test_no_cross_user(self, db):
        from app.services.notification_service import mark_all_read
        _make_notification(db, user_id=2)
        count = mark_all_read(db, 1)
        assert count == 0


class TestDeleteNotification:
    def test_deletes_own(self, db):
        from app.services.notification_service import delete_notification
        n = _make_notification(db, user_id=1)
        ok = delete_notification(db, n.id, user_id=1)
        assert ok is True

    def test_cannot_delete_others(self, db):
        from app.services.notification_service import delete_notification
        n = _make_notification(db, user_id=1)
        ok = delete_notification(db, n.id, user_id=2)
        assert ok is False

    def test_nonexistent_returns_false(self, db):
        from app.services.notification_service import delete_notification
        ok = delete_notification(db, 99999, user_id=1)
        assert ok is False


class TestGetUnreadCount:
    def test_empty(self, db):
        from app.services.notification_service import get_unread_count
        result = get_unread_count(db, 1)
        assert result["unread_count"] == 0
        assert result["by_type"] == {}

    def test_counts_by_type(self, db):
        from app.services.notification_service import get_unread_count
        _make_notification(db, user_id=1, ntype="budget")
        _make_notification(db, user_id=1, ntype="budget")
        _make_notification(db, user_id=1, ntype="goal")
        result = get_unread_count(db, 1)
        assert result["unread_count"] == 3
        assert result["by_type"]["budget"] == 2
        assert result["by_type"]["goal"] == 1

    def test_excludes_read(self, db):
        from app.services.notification_service import get_unread_count
        _make_notification(db, user_id=1, is_read=True)
        result = get_unread_count(db, 1)
        assert result["unread_count"] == 0


# ── Event handlers ────────────────────────────────────────────────────────────

class TestEventHandlers:
    def test_handle_user_created_creates_welcome(self, db):
        from app.services.notification_service import handle_user_created
        from app.models.notification import Notification
        handle_user_created(db, {"user_id": 7, "name": "Ali"})
        n = db.query(Notification).filter_by(user_id=7).first()
        assert n is not None
        assert n.notification_type == "system"
        assert "Welcome" in n.title

    def test_handle_user_created_creates_prefs(self, db):
        from app.services.notification_service import handle_user_created
        from app.models.notification import NotificationPreference
        handle_user_created(db, {"user_id": 8, "name": "Fatima"})
        pref = db.query(NotificationPreference).filter_by(user_id=8).first()
        assert pref is not None

    def test_handle_budget_exceeded(self, db):
        from app.services.notification_service import handle_budget_exceeded
        from app.models.notification import Notification
        handle_budget_exceeded(db, {"user_id": 1, "category": "Food", "percentage_used": 85})
        n = db.query(Notification).filter_by(user_id=1, notification_type="budget").first()
        assert n is not None
        assert "85" in n.message or "Food" in n.message

    def test_handle_goal_completed(self, db):
        from app.services.notification_service import handle_goal_completed
        from app.models.notification import Notification
        handle_goal_completed(db, {"user_id": 1, "goal_name": "Emergency Fund"})
        n = db.query(Notification).filter_by(user_id=1, notification_type="goal").first()
        assert n is not None
        assert "Emergency Fund" in n.message

    def test_handle_recommendation_generated(self, db):
        from app.services.notification_service import handle_recommendation_generated
        from app.models.notification import Notification
        handle_recommendation_generated(db, {"user_id": 1, "title": "Save more"})
        n = db.query(Notification).filter_by(user_id=1, notification_type="recommendation").first()
        assert n is not None

    def test_handle_statement_processed(self, db):
        from app.services.notification_service import handle_statement_processed
        from app.models.notification import Notification
        handle_statement_processed(db, {"user_id": 1})
        n = db.query(Notification).filter_by(user_id=1, notification_type="statement").first()
        assert n is not None

    def test_handler_missing_user_id_no_crash(self, db):
        from app.services.notification_service import handle_budget_exceeded
        handle_budget_exceeded(db, {"category": "Food"})  # no user_id


# ── Pydantic schema validation ────────────────────────────────────────────────

class TestSchemas:
    def test_send_request_priority_clamped(self):
        from app.schemas.notification import SendNotificationRequest
        r = SendNotificationRequest(
            user_id=1, notification_type="system", title="T", message="M", priority=99
        )
        assert r.priority == 4

    def test_send_request_invalid_channel_filtered(self):
        from app.schemas.notification import SendNotificationRequest
        r = SendNotificationRequest(
            user_id=1, notification_type="system", title="T", message="M",
            channels=["invalid_channel"]
        )
        assert r.channels == ["in_app"]

    def test_send_request_unknown_type_normalised(self):
        from app.schemas.notification import SendNotificationRequest
        r = SendNotificationRequest(
            user_id=1, notification_type="unknown_xyz", title="T", message="M"
        )
        assert r.notification_type == "system"

    def test_preference_update_time_format_hhmm(self):
        from app.schemas.preference import PreferenceUpdate
        u = PreferenceUpdate(quiet_hours_start="22:00", quiet_hours_end="08:00")
        assert u.quiet_hours_start == "22:00:00"
        assert u.quiet_hours_end == "08:00:00"

    def test_preference_update_time_format_hhmmss(self):
        from app.schemas.preference import PreferenceUpdate
        u = PreferenceUpdate(quiet_hours_start="22:30:00")
        assert u.quiet_hours_start == "22:30:00"

    def test_notification_response_from_orm(self, db):
        from app.schemas.notification import NotificationResponse
        n = _make_notification(db, user_id=1)
        resp = NotificationResponse.model_validate(n)
        assert resp.id == n.id
        assert resp.is_read is False
