"""API endpoint tests."""

import pytest


# ── /health ────────────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "notification-service"
    assert "dependencies" in data


# ── /notifications — auth ──────────────────────────────────────────────────────

def test_list_notifications_no_auth(client):
    resp = client.get("/api/v1/notifications")
    assert resp.status_code == 401


def test_send_no_auth(client):
    resp = client.post("/api/v1/notifications/send", json={
        "user_id": 1, "notification_type": "system",
        "channels": ["in_app"], "title": "T", "message": "M"
    })
    assert resp.status_code == 401


def test_unread_no_auth(client):
    resp = client.get("/api/v1/notifications/unread")
    assert resp.status_code == 401


def test_preferences_no_auth(client):
    resp = client.get("/api/v1/notifications/preferences")
    assert resp.status_code == 401


# ── GET /notifications ─────────────────────────────────────────────────────────

def test_list_notifications_empty(client, auth_headers):
    resp = client.get("/api/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "notifications" in data
    assert data["total_count"] == 0
    assert data["unread_count"] == 0


def test_list_notifications_returns_items(client, auth_headers, sample_notification):
    resp = client.get("/api/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] >= 1
    n = data["notifications"][0]
    assert n["notification_type"] == "budget"
    assert n["title"] == "Budget Alert"
    assert n["is_read"] is False


def test_list_notifications_structure(client, auth_headers, sample_notification):
    resp = client.get("/api/v1/notifications", headers=auth_headers)
    n = resp.json()["notifications"][0]
    for field in ("id", "user_id", "notification_type", "channel", "title",
                  "message", "is_read", "is_sent", "priority", "created_at"):
        assert field in n


def test_list_notifications_filter_unread(client, auth_headers, sample_notification):
    resp = client.get("/api/v1/notifications?is_read=false", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total_count"] >= 1


def test_list_notifications_filter_read(client, auth_headers, sample_notification):
    resp = client.get("/api/v1/notifications?is_read=true", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 0


def test_list_notifications_filter_by_type(client, auth_headers, sample_notification):
    resp = client.get("/api/v1/notifications?notification_type=budget", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total_count"] >= 1


def test_list_notifications_user_isolation(client, auth_headers_user2, sample_notification):
    # sample_notification belongs to user_id=1; user2 should see 0
    resp = client.get("/api/v1/notifications", headers=auth_headers_user2)
    assert resp.json()["total_count"] == 0


def test_list_notifications_pagination(client, auth_headers, db):
    from app.models.notification import Notification
    from datetime import datetime, timedelta
    for i in range(5):
        n = Notification(
            user_id=1, notification_type="system", channel="in_app",
            title=f"N{i}", message="msg", is_sent=True, is_read=False, priority=1,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(n)
    db.commit()

    r1 = client.get("/api/v1/notifications?page=1&limit=3", headers=auth_headers)
    assert len(r1.json()["notifications"]) == 3
    assert r1.json()["has_more"] is True

    r2 = client.get("/api/v1/notifications?page=2&limit=3", headers=auth_headers)
    assert len(r2.json()["notifications"]) == 2
    assert r2.json()["has_more"] is False


# ── GET /notifications/unread ──────────────────────────────────────────────────

def test_unread_count_zero(client, auth_headers):
    resp = client.get("/api/v1/notifications/unread", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 0


def test_unread_count_with_notification(client, auth_headers, sample_notification):
    resp = client.get("/api/v1/notifications/unread", headers=auth_headers)
    assert resp.json()["unread_count"] == 1
    assert "budget" in resp.json()["by_type"]


# ── POST /notifications/send ───────────────────────────────────────────────────

def test_send_in_app_notification(client, auth_headers):
    resp = client.post(
        "/api/v1/notifications/send",
        headers=auth_headers,
        json={
            "user_id": 1,
            "notification_type": "system",
            "channels": ["in_app"],
            "title": "Test Notification",
            "message": "This is a test",
            "priority": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "in_app" in data["notification_ids"]
    assert data["delivery_status"]["in_app"] == "sent"


def test_send_creates_db_record(client, auth_headers, db):
    from app.models.notification import Notification
    client.post(
        "/api/v1/notifications/send",
        headers=auth_headers,
        json={"user_id": 1, "notification_type": "budget", "channels": ["in_app"],
              "title": "T", "message": "M"},
    )
    count = db.query(Notification).filter_by(user_id=1).count()
    assert count >= 1


def test_send_multiple_channels(client, auth_headers):
    resp = client.post(
        "/api/v1/notifications/send",
        headers=auth_headers,
        json={
            "user_id": 1,
            "notification_type": "budget",
            "channels": ["in_app", "push"],
            "title": "Multi channel",
            "message": "test",
        },
    )
    assert resp.status_code == 200
    status = resp.json()["delivery_status"]
    assert "in_app" in status
    assert "push" in status


def test_send_respects_channel_disabled(client, auth_headers, db):
    from app.services.notification_service import update_preferences
    update_preferences(db, 1, {"push_enabled": False})

    resp = client.post(
        "/api/v1/notifications/send",
        headers=auth_headers,
        json={"user_id": 1, "notification_type": "budget",
              "channels": ["push", "in_app"], "title": "T", "message": "M"},
    )
    status = resp.json()["delivery_status"]
    assert "disabled" in status.get("push", "")
    assert status.get("in_app") == "sent"


# ── PUT /notifications/read-all ────────────────────────────────────────────────

def test_mark_all_read(client, auth_headers, db):
    from app.models.notification import Notification
    from datetime import datetime, timedelta
    for _ in range(3):
        db.add(Notification(
            user_id=1, notification_type="system", channel="in_app",
            title="N", message="M", is_sent=True, is_read=False, priority=1,
            expires_at=datetime.utcnow() + timedelta(days=30),
        ))
    db.commit()

    resp = client.put("/api/v1/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["count"] == 3


def test_mark_all_read_by_type(client, auth_headers, db):
    from app.models.notification import Notification
    from datetime import datetime, timedelta
    for t in ["budget", "budget", "goal"]:
        db.add(Notification(
            user_id=1, notification_type=t, channel="in_app",
            title="N", message="M", is_sent=True, is_read=False, priority=1,
            expires_at=datetime.utcnow() + timedelta(days=30),
        ))
    db.commit()

    resp = client.put(
        "/api/v1/notifications/read-all",
        headers=auth_headers,
        json={"notification_type": "budget"},
    )
    assert resp.json()["count"] == 2


# ── PUT /notifications/{id}/read ──────────────────────────────────────────────

def test_mark_one_read(client, auth_headers, sample_notification):
    resp = client.put(
        f"/api/v1/notifications/{sample_notification.id}/read",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["read_at"] is not None


def test_mark_read_wrong_user(client, auth_headers_user2, sample_notification):
    resp = client.put(
        f"/api/v1/notifications/{sample_notification.id}/read",
        headers=auth_headers_user2,
    )
    assert resp.status_code == 404


def test_mark_read_nonexistent(client, auth_headers):
    resp = client.put("/api/v1/notifications/99999/read", headers=auth_headers)
    assert resp.status_code == 404


# ── DELETE /notifications/{id} ────────────────────────────────────────────────

def test_delete_notification(client, auth_headers, sample_notification):
    resp = client.delete(
        f"/api/v1/notifications/{sample_notification.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_delete_wrong_user(client, auth_headers_user2, sample_notification):
    resp = client.delete(
        f"/api/v1/notifications/{sample_notification.id}",
        headers=auth_headers_user2,
    )
    assert resp.status_code == 404


def test_delete_nonexistent(client, auth_headers):
    resp = client.delete("/api/v1/notifications/99999", headers=auth_headers)
    assert resp.status_code == 404


# ── /notifications/preferences ────────────────────────────────────────────────

def test_get_preferences_creates_defaults(client, auth_headers):
    resp = client.get("/api/v1/notifications/preferences", headers=auth_headers)
    assert resp.status_code == 200
    p = resp.json()
    assert p["push_enabled"] is True
    assert p["email_enabled"] is True
    assert p["in_app_enabled"] is True
    assert p["sms_enabled"] is False
    assert p["marketing"] is False
    assert p["budget_alerts"] is True


def test_update_preferences(client, auth_headers):
    resp = client.put(
        "/api/v1/notifications/preferences",
        headers=auth_headers,
        json={"push_enabled": False, "marketing": True, "email_enabled": False},
    )
    assert resp.status_code == 200
    p = resp.json()
    assert p["push_enabled"] is False
    assert p["marketing"] is True
    assert p["email_enabled"] is False


def test_update_quiet_hours(client, auth_headers):
    resp = client.put(
        "/api/v1/notifications/preferences",
        headers=auth_headers,
        json={"quiet_hours_enabled": True, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00"},
    )
    assert resp.status_code == 200
    p = resp.json()
    assert p["quiet_hours_enabled"] is True
    assert "23:00" in p["quiet_hours_start"]


# ── Device tokens ──────────────────────────────────────────────────────────────

def test_register_device_token(client, auth_headers):
    resp = client.post(
        "/api/v1/notifications/device-token",
        headers=auth_headers,
        json={"player_id": "token_abc123", "device_type": "ios", "app_version": "1.0"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_register_device_token_dedup(client, auth_headers):
    payload = {"player_id": "same_token", "device_type": "android"}
    client.post("/api/v1/notifications/device-token", headers=auth_headers, json=payload)
    client.post("/api/v1/notifications/device-token", headers=auth_headers, json=payload)

    prefs = client.get("/api/v1/notifications/preferences", headers=auth_headers).json()
    assert prefs["device_tokens"].count("same_token") == 1


def test_unregister_device_token(client, auth_headers):
    client.post("/api/v1/notifications/device-token", headers=auth_headers,
                json={"player_id": "del_token"})
    resp = client.delete("/api/v1/notifications/device-token/del_token", headers=auth_headers)
    assert resp.status_code == 200
    prefs = client.get("/api/v1/notifications/preferences", headers=auth_headers).json()
    assert "del_token" not in prefs["device_tokens"]
