"""
Integration tests for User Service API endpoints.
All tests run against an in-memory SQLite DB (see conftest.py).
"""
from __future__ import annotations

import pytest
from tests.conftest import VALID_USER


# --------------------------------------------------------------------------- #
# Infrastructure
# --------------------------------------------------------------------------- #

def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


def test_health(client):
    resp = client.get("/health")
    data = resp.json()
    assert resp.status_code == 200
    assert data["service"] == "User Service"


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #

def test_register_success(client):
    resp = client.post("/api/v1/users/register", json=VALID_USER)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == VALID_USER["email"]
    assert data["username"] == VALID_USER["username"]
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert "hashed_password" not in data


def test_register_duplicate_email(client, registered_user):
    dupe = {**VALID_USER, "username": "another_user"}
    resp = client.post("/api/v1/users/register", json=dupe)
    assert resp.status_code == 409
    assert "Email" in resp.json()["detail"]


def test_register_duplicate_username(client, registered_user):
    dupe = {**VALID_USER, "email": "another@savvy.io"}
    resp = client.post("/api/v1/users/register", json=dupe)
    assert resp.status_code == 409
    assert "Username" in resp.json()["detail"]


@pytest.mark.parametrize(
    "bad_data,expected_msg",
    [
        ({"password": "short"}, "at least 8"),
        ({"password": "alllowercase1"}, "uppercase"),
        ({"password": "NoDigitPass"}, "digit"),
        ({"username": "ab"}, "at least 3"),
        ({"username": "bad user!"}, "alphanumeric"),
        ({"email": "not-an-email"}, None),
    ],
)
def test_register_validation(client, bad_data, expected_msg):
    payload = {**VALID_USER, "email": "unique@test.io", "username": "uniqueuser", **bad_data}
    resp = client.post("/api/v1/users/register", json=payload)
    assert resp.status_code == 422
    if expected_msg:
        assert expected_msg.lower() in resp.text.lower()


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #

def test_login_success(client, registered_user):
    resp = client.post(
        "/api/v1/users/login",
        data={"username": VALID_USER["username"], "password": VALID_USER["password"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == VALID_USER["username"]


def test_login_by_email(client, registered_user):
    resp = client.post(
        "/api/v1/users/login",
        data={"username": VALID_USER["email"], "password": VALID_USER["password"]},
    )
    assert resp.status_code == 200


def test_login_wrong_password(client, registered_user):
    resp = client.post(
        "/api/v1/users/login",
        data={"username": VALID_USER["username"], "password": "WrongPass99"},
    )
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post(
        "/api/v1/users/login",
        data={"username": "ghost", "password": "Pass1234"},
    )
    assert resp.status_code == 401


# --------------------------------------------------------------------------- #
# Token refresh
# --------------------------------------------------------------------------- #

def test_token_refresh(client, registered_user):
    login_resp = client.post(
        "/api/v1/users/login",
        data={"username": VALID_USER["username"], "password": VALID_USER["password"]},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = client.post("/api/v1/users/token/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_token_refresh_invalid(client):
    resp = client.post("/api/v1/users/token/refresh", json={"refresh_token": "bad.token.here"})
    assert resp.status_code == 401


# --------------------------------------------------------------------------- #
# Protected endpoints
# --------------------------------------------------------------------------- #

def test_get_me(client, auth_headers):
    resp = client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == VALID_USER["email"]
    assert "hashed_password" not in data


def test_get_me_no_auth(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_update_me(client, auth_headers):
    payload = {"full_name": "Updated Name", "city": "Lahore", "currency": "PKR"}
    resp = client.put("/api/v1/users/me", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Updated Name"
    assert data["city"] == "Lahore"


def test_update_me_partial(client, auth_headers):
    """Only supplied fields are updated."""
    resp = client.put(
        "/api/v1/users/me",
        json={"city": "Islamabad"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["city"] == "Islamabad"


def test_update_me_invalid_time(client, auth_headers):
    resp = client.put(
        "/api/v1/users/me",
        json={"daily_reminder_time": "9am"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Password change
# --------------------------------------------------------------------------- #

def test_change_password(client, auth_headers):
    payload = {
        "current_password": VALID_USER["password"],
        "new_password": "NewSecure1",
    }
    resp = client.post("/api/v1/users/me/password", json=payload, headers=auth_headers)
    assert resp.status_code == 200

    # Login with new password
    login_resp = client.post(
        "/api/v1/users/login",
        data={"username": VALID_USER["username"], "password": "NewSecure1"},
    )
    assert login_resp.status_code == 200


def test_change_password_wrong_current(client, auth_headers):
    payload = {"current_password": "WrongOld1", "new_password": "NewSecure1"}
    resp = client.post("/api/v1/users/me/password", json=payload, headers=auth_headers)
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# Email verification
# --------------------------------------------------------------------------- #

def test_send_and_use_verification(client, auth_headers):
    # Request token
    resp = client.post("/api/v1/users/me/send-verification", headers=auth_headers)
    assert resp.status_code == 200
    token = resp.json()["detail"]["token"]

    # Use token
    verify_resp = client.post("/api/v1/users/verify-email", json={"token": token})
    assert verify_resp.status_code == 200

    # Profile should now show verified
    me_resp = client.get("/api/v1/users/me", headers=auth_headers)
    assert me_resp.json()["is_verified"] is True


def test_verify_email_bad_token(client):
    resp = client.post("/api/v1/users/verify-email", json={"token": "invalid"})
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# Account deletion
# --------------------------------------------------------------------------- #

def test_delete_me(client):
    """Register a separate user and delete them."""
    unique_user = {
        "email": "delete_me@savvy.io",
        "username": "deleteme",
        "password": "Delete1Me",
        "currency": "USD",
    }
    client.post("/api/v1/users/register", json=unique_user)
    login = client.post(
        "/api/v1/users/login",
        data={"username": unique_user["username"], "password": unique_user["password"]},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = client.delete("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200

    # Can no longer login
    login2 = client.post(
        "/api/v1/users/login",
        data={"username": unique_user["username"], "password": unique_user["password"]},
    )
    assert login2.status_code == 401


# --------------------------------------------------------------------------- #
# Admin endpoints
# --------------------------------------------------------------------------- #

def test_admin_list_users_forbidden_for_regular_user(client, auth_headers):
    resp = client.get("/api/v1/users/", headers=auth_headers)
    assert resp.status_code == 403
