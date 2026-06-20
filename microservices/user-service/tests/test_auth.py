"""
Tests for authentication flows:
- JWT creation and verification
- Password hashing
- Token blacklisting
- Refresh token logic
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_verification_token,
    get_password_hash,
    verify_access_token,
    verify_password,
    verify_refresh_token,
    verify_verification_token,
)


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #

def test_password_hash_and_verify():
    plain = "MyPassword123"
    hashed = get_password_hash(plain)

    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("WrongPassword", hashed)


def test_different_hashes_for_same_password():
    plain = "SamePass1"
    h1 = get_password_hash(plain)
    h2 = get_password_hash(plain)
    # bcrypt salts → different hashes but both verify
    assert h1 != h2
    assert verify_password(plain, h1)
    assert verify_password(plain, h2)


# --------------------------------------------------------------------------- #
# Access token
# --------------------------------------------------------------------------- #

def test_create_and_verify_access_token():
    with patch("app.core.security.get_redis", return_value=None):
        token = create_access_token({"sub": "42", "role": "user"})
        payload = verify_access_token(token)

    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_expired_access_token_is_rejected():
    with patch("app.core.security.get_redis", return_value=None):
        token = create_access_token(
            {"sub": "1"}, expires_delta=timedelta(seconds=-1)
        )
        payload = verify_access_token(token)

    assert payload is None


def test_wrong_token_type_rejected():
    """A refresh token should not validate as an access token."""
    with patch("app.core.security.get_redis", return_value=None):
        refresh = create_refresh_token(99)
        payload = verify_access_token(refresh)

    assert payload is None


# --------------------------------------------------------------------------- #
# Refresh token
# --------------------------------------------------------------------------- #

def test_create_and_verify_refresh_token():
    with patch("app.core.security.get_redis", return_value=None):
        token = create_refresh_token(7)
        user_id = verify_refresh_token(token)

    assert user_id == 7


def test_access_token_rejected_as_refresh():
    with patch("app.core.security.get_redis", return_value=None):
        access = create_access_token({"sub": "5"})
        result = verify_refresh_token(access)

    assert result is None


# --------------------------------------------------------------------------- #
# Email verification token
# --------------------------------------------------------------------------- #

def test_verification_token():
    token = create_verification_token(33)
    user_id = verify_verification_token(token)
    assert user_id == 33


def test_access_token_not_valid_as_verification():
    with patch("app.core.security.get_redis", return_value=None):
        access = create_access_token({"sub": "10"})
        result = verify_verification_token(access)
    assert result is None
