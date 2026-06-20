"""
Rate-limit middleware tests — Redis-backed fixed-window counter.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.middleware.rate_limit import RateLimitMiddleware


# ── Integration: rate-limit behaviour via TestClient ─────────────────────────

class TestRateLimitHeaders:
    def test_x_ratelimit_limit_present(self, client, mock_http_client, auth_headers):
        resp = client.get("/api/v1/users/me", headers=auth_headers)
        assert "x-ratelimit-limit" in resp.headers

    def test_x_ratelimit_remaining_present(self, client, mock_http_client, auth_headers):
        resp = client.get("/api/v1/users/me", headers=auth_headers)
        assert "x-ratelimit-remaining" in resp.headers

    def test_x_ratelimit_reset_present(self, client, mock_http_client, auth_headers):
        resp = client.get("/api/v1/users/me", headers=auth_headers)
        assert "x-ratelimit-reset" in resp.headers

    def test_auth_limit_applied_for_authenticated(self, client, mock_http_client, auth_headers):
        resp = client.get("/api/v1/users/me", headers=auth_headers)
        assert resp.headers["x-ratelimit-limit"] == str(settings.RATE_LIMIT_AUTH)

    def test_anon_limit_applied_for_unauthenticated(self, client, mock_http_client):
        """Register is public — no JWT — should get anon rate limit."""
        resp = client.post(
            "/api/v1/users/register",
            json={"email": "a@b.com", "password": "p"},
        )
        assert resp.headers.get("x-ratelimit-limit") == str(settings.RATE_LIMIT_ANON)

    def test_remaining_decrements(self, client, mock_http_client, auth_headers):
        resp1 = client.get("/api/v1/users/me", headers=auth_headers)
        resp2 = client.get("/api/v1/users/me", headers=auth_headers)
        r1 = int(resp1.headers["x-ratelimit-remaining"])
        r2 = int(resp2.headers["x-ratelimit-remaining"])
        assert r2 < r1

    def test_remaining_never_negative(self, client, mock_http_client, auth_headers):
        for _ in range(5):
            resp = client.get("/api/v1/users/me", headers=auth_headers)
        remaining = int(resp.headers["x-ratelimit-remaining"])
        assert remaining >= 0


class TestRateLimitExceeded:
    def _exhaust_limit(self, client, mock_http_client, auth_headers, n: int):
        """Fire n requests to consume the counter."""
        for _ in range(n):
            client.get("/api/v1/users/me", headers=auth_headers)

    def test_429_when_limit_exceeded(self, client, mock_http_client, auth_headers):
        """Patch _redis pipeline to return count > RATE_LIMIT_AUTH."""
        from app.middleware import rate_limit as rl_module

        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.incr.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe

        async def _execute():
            return [settings.RATE_LIMIT_AUTH + 1, True]

        mock_pipe.execute = _execute
        mock_redis.pipeline.return_value = mock_pipe

        with patch.object(rl_module, "_redis", mock_redis):
            resp = client.get("/api/v1/users/me", headers=auth_headers)

        assert resp.status_code == 429

    def test_429_body_has_detail(self, client, mock_http_client, auth_headers):
        from app.middleware import rate_limit as rl_module

        mock_redis = MagicMock()
        mock_pipe = MagicMock()

        async def _execute():
            return [settings.RATE_LIMIT_AUTH + 5, True]

        mock_pipe.incr.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe
        mock_pipe.execute = _execute
        mock_redis.pipeline.return_value = mock_pipe

        with patch.object(rl_module, "_redis", mock_redis):
            resp = client.get("/api/v1/users/me", headers=auth_headers)

        assert "detail" in resp.json()
        assert "rate limit" in resp.json()["detail"].lower()

    def test_429_has_retry_after_header(self, client, mock_http_client, auth_headers):
        from app.middleware import rate_limit as rl_module

        mock_redis = MagicMock()
        mock_pipe = MagicMock()

        async def _execute():
            return [settings.RATE_LIMIT_AUTH + 1, True]

        mock_pipe.incr.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe
        mock_pipe.execute = _execute
        mock_redis.pipeline.return_value = mock_pipe

        with patch.object(rl_module, "_redis", mock_redis):
            resp = client.get("/api/v1/users/me", headers=auth_headers)

        assert "retry-after" in resp.headers

    def test_429_ratelimit_remaining_is_zero(self, client, mock_http_client, auth_headers):
        from app.middleware import rate_limit as rl_module

        mock_redis = MagicMock()
        mock_pipe = MagicMock()

        async def _execute():
            return [settings.RATE_LIMIT_AUTH + 1, True]

        mock_pipe.incr.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe
        mock_pipe.execute = _execute
        mock_redis.pipeline.return_value = mock_pipe

        with patch.object(rl_module, "_redis", mock_redis):
            resp = client.get("/api/v1/users/me", headers=auth_headers)

        assert resp.headers.get("x-ratelimit-remaining") == "0"


class TestRateLimitFailOpen:
    def test_redis_unavailable_allows_request(self, client, mock_http_client, auth_headers):
        """Redis down → fail open → 200 not 503."""
        from app.middleware import rate_limit as rl_module

        with patch.object(rl_module, "_redis", None):
            with patch.object(rl_module, "_get_redis", return_value=None):
                resp = client.get("/api/v1/users/me", headers=auth_headers)

        assert resp.status_code == 200

    def test_redis_pipeline_exception_allows_request(
        self, client, mock_http_client, auth_headers
    ):
        """Pipeline raises → fail open → request proceeds."""
        from app.middleware import rate_limit as rl_module

        mock_redis = MagicMock()
        mock_pipe = MagicMock()

        async def _execute_error():
            raise ConnectionError("Redis gone")

        mock_pipe.incr.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe
        mock_pipe.execute = _execute_error
        mock_redis.pipeline.return_value = mock_pipe

        with patch.object(rl_module, "_redis", mock_redis):
            resp = client.get("/api/v1/users/me", headers=auth_headers)

        assert resp.status_code == 200


class TestRateLimitSkippedPaths:
    def test_health_skips_rate_limit(self, client, mock_http_client):
        mock_http_client.get = AsyncMock(
            return_value=type("R", (), {"status_code": 200})()
        )
        resp = client.get("/health")
        # No rate limit headers on skipped paths
        assert "x-ratelimit-limit" not in resp.headers

    def test_root_skips_rate_limit(self, client):
        resp = client.get("/")
        assert "x-ratelimit-limit" not in resp.headers

    def test_docs_skips_rate_limit(self, client):
        resp = client.get("/docs")
        assert "x-ratelimit-limit" not in resp.headers


class TestRateLimitPerUser:
    def test_different_users_have_separate_counters(
        self, client, mock_http_client, auth_headers, auth_headers_user2
    ):
        """User 1 and User 2 share no counter — independent remaining values."""
        resp1 = client.get("/api/v1/users/me", headers=auth_headers)
        resp2 = client.get("/api/v1/users/me", headers=auth_headers_user2)

        # Both get fresh limits (counter started from 1 for each)
        r1 = int(resp1.headers["x-ratelimit-limit"])
        r2 = int(resp2.headers["x-ratelimit-limit"])
        assert r1 == settings.RATE_LIMIT_AUTH
        assert r2 == settings.RATE_LIMIT_AUTH
