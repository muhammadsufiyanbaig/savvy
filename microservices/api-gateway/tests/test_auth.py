"""
Auth middleware tests — JWT pre-validation at gateway layer.
"""

import time
from unittest.mock import AsyncMock, patch

import pytest
from jose import jwt

from app.core.config import settings, PUBLIC_PATHS
from app.core.security import decode_token, user_id_from_payload
from app.middleware.auth import _is_public


# ── Unit: decode_token ────────────────────────────────────────────────────────

class TestDecodeToken:
    def _make(self, payload: dict) -> str:
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def test_valid_token_returns_payload(self):
        token = self._make({"sub": "42", "user_id": 42})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"

    def test_expired_token_returns_none(self):
        token = self._make({"sub": "1", "exp": int(time.time()) - 10})
        assert decode_token(token) is None

    def test_wrong_secret_returns_none(self):
        token = jwt.encode({"sub": "1"}, "wrong-secret", algorithm="HS256")
        assert decode_token(token) is None

    def test_malformed_token_returns_none(self):
        assert decode_token("not.a.token") is None

    def test_empty_string_returns_none(self):
        assert decode_token("") is None

    def test_wrong_algorithm_returns_none(self):
        # RS256 token signed with wrong algo
        assert decode_token("header.payload.sig") is None


# ── Unit: user_id_from_payload ────────────────────────────────────────────────

class TestUserIdFromPayload:
    def test_sub_as_string(self):
        assert user_id_from_payload({"sub": "99"}) == 99

    def test_sub_as_int_string(self):
        assert user_id_from_payload({"sub": "1"}) == 1

    def test_user_id_fallback(self):
        assert user_id_from_payload({"user_id": 7}) == 7

    def test_sub_takes_priority(self):
        assert user_id_from_payload({"sub": "5", "user_id": 9}) == 5

    def test_empty_payload_returns_zero(self):
        assert user_id_from_payload({}) == 0

    def test_non_numeric_sub_returns_none(self):
        assert user_id_from_payload({"sub": "abc"}) is None

    def test_none_sub_falls_back_to_user_id(self):
        assert user_id_from_payload({"sub": None, "user_id": 3}) == 3


# ── Unit: _is_public ──────────────────────────────────────────────────────────

class TestIsPublic:
    def test_register_is_public(self):
        assert _is_public("/api/v1/users/register") is True

    def test_login_is_public(self):
        assert _is_public("/api/v1/users/login") is True

    def test_verify_email_is_public(self):
        assert _is_public("/api/v1/users/verify-email") is True

    def test_refresh_is_public(self):
        assert _is_public("/api/v1/users/refresh") is True

    def test_forgot_password_is_public(self):
        assert _is_public("/api/v1/users/forgot-password") is True

    def test_reset_password_is_public(self):
        assert _is_public("/api/v1/users/reset-password") is True

    def test_health_is_public(self):
        assert _is_public("/health") is True

    def test_root_is_public(self):
        assert _is_public("/") is True

    def test_docs_is_public(self):
        assert _is_public("/docs") is True

    def test_openapi_json_is_public(self):
        assert _is_public("/openapi.json") is True

    def test_redoc_is_public(self):
        assert _is_public("/redoc") is True

    def test_protected_path_not_public(self):
        assert _is_public("/api/v1/users/me") is False

    def test_expenses_not_public(self):
        assert _is_public("/api/v1/expenses") is False

    def test_ai_not_public(self):
        assert _is_public("/api/v1/ai/recommendations") is False

    def test_notifications_not_public(self):
        assert _is_public("/api/v1/notifications") is False


# ── Integration: AuthMiddleware via TestClient ────────────────────────────────

class TestAuthMiddleware:
    def test_no_token_returns_401(self, client, mock_http_client):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401

    def test_bad_bearer_token_returns_401(self, client, mock_http_client):
        resp = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_wrong_scheme_returns_401(self, client, mock_http_client):
        resp = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401

    def test_missing_authorization_header_returns_401(self, client, mock_http_client):
        resp = client.post("/api/v1/expenses", json={"amount": 100})
        assert resp.status_code == 401

    def test_valid_token_passes_through(self, client, mock_http_client, auth_headers):
        resp = client.get("/api/v1/users/me", headers=auth_headers)
        # Upstream mock returns 200 — should not be blocked
        assert resp.status_code == 200

    def test_public_register_no_auth_needed(self, client, mock_http_client):
        resp = client.post(
            "/api/v1/users/register",
            json={"email": "x@x.com", "password": "pass123"},
        )
        # Should reach upstream (mock returns 200), not rejected by auth
        assert resp.status_code == 200

    def test_public_login_no_auth_needed(self, client, mock_http_client):
        resp = client.post(
            "/api/v1/users/login",
            json={"email": "x@x.com", "password": "pass123"},
        )
        assert resp.status_code == 200

    def test_health_no_auth_needed(self, client, mock_http_client):
        mock_http_client.get = AsyncMock(
            return_value=type("R", (), {"status_code": 200})()
        )
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_root_no_auth_needed(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_401_has_www_authenticate_header(self, client, mock_http_client):
        resp = client.get("/api/v1/users/me")
        assert resp.headers.get("www-authenticate") == "Bearer"

    def test_401_body_detail(self, client, mock_http_client):
        resp = client.get("/api/v1/users/me")
        assert "credentials" in resp.json()["detail"].lower()

    def test_expired_token_returns_401(self, client, mock_http_client):
        expired = jwt.encode(
            {"sub": "1", "exp": int(time.time()) - 60},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        resp = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert resp.status_code == 401

    def test_x_user_id_forwarded_to_downstream(self, client, mock_http_client, auth_headers):
        client.get("/api/v1/users/me", headers=auth_headers)
        call_kwargs = mock_http_client.stream.call_args.kwargs
        forwarded_headers = {k.lower(): v for k, v in call_kwargs.get("headers", {}).items()}
        assert "x-user-id" in forwarded_headers

    def test_x_user_id_value_matches_token(self, client, mock_http_client, auth_headers):
        """Token has user_id=1 — downstream must receive x-user-id: 1."""
        client.get("/api/v1/users/me", headers=auth_headers)
        call_kwargs = mock_http_client.stream.call_args.kwargs
        forwarded_headers = {k.lower(): v for k, v in call_kwargs.get("headers", {}).items()}
        assert forwarded_headers.get("x-user-id") == "1"

    def test_different_user_ids_forwarded_correctly(
        self, client, mock_http_client, auth_headers_user2
    ):
        client.get("/api/v1/users/me", headers=auth_headers_user2)
        call_kwargs = mock_http_client.stream.call_args.kwargs
        forwarded_headers = {k.lower(): v for k, v in call_kwargs.get("headers", {}).items()}
        assert forwarded_headers.get("x-user-id") == "2"
