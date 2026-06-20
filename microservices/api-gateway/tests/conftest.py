"""
Test fixtures — mock httpx pool and Redis before importing app.
All downstream calls intercepted via respx.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response as HttpxResponse
from jose import jwt

# ── 1. Mock Redis BEFORE app import ──────────────────────────────────────────
_rate_store: dict = {}
_mock_redis = MagicMock()
_mock_pipeline = MagicMock()

def _pipeline_incr(key):
    _rate_store[key] = _rate_store.get(key, 0) + 1
    return _mock_pipeline

def _pipeline_expire(key, ttl):
    return _mock_pipeline

async def _pipeline_execute():
    # Return last incr result
    last_key = list(_rate_store.keys())[-1] if _rate_store else "x"
    return [_rate_store.get(last_key, 1), True]

_mock_pipeline.incr.side_effect = _pipeline_incr
_mock_pipeline.expire.side_effect = _pipeline_expire
_mock_pipeline.execute = _pipeline_execute
_mock_redis.pipeline.return_value = _mock_pipeline

_redis_patcher = patch("app.middleware.rate_limit._redis", _mock_redis)
_redis_patcher.start()

# ── 2. Mock httpx client pool ─────────────────────────────────────────────────
# respx intercepts httpx calls at transport level — no real network
# We start a global respx mock; individual tests add routes via fixture

# ── Import app AFTER patches ──────────────────────────────────────────────────
from app.main import app  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.proxy import client as _client_module  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_token(user_id: int = 1) -> str:
    return jwt.encode(
        {"sub": str(user_id), "user_id": user_id},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def make_response(status: int = 200, body: dict = None) -> HttpxResponse:
    return HttpxResponse(
        status_code=status,
        content=json.dumps(body or {"ok": True}).encode(),
        headers={"content-type": "application/json"},
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_rate_store():
    _rate_store.clear()
    yield
    _rate_store.clear()


@pytest.fixture
def mock_http_client():
    """
    Returns a mock AsyncClient that replaces the shared pool.
    Set mock_http_client.request.return_value to control responses.
    """
    mock = MagicMock()
    mock.request = AsyncMock(return_value=make_response(200, {"ok": True}))
    mock.get = AsyncMock(return_value=make_response(200, {"ok": True}))
    # httpx.AsyncClient.stream() is a SYNC call returning an async context manager.
    # Must be MagicMock (not AsyncMock) so the call returns the ctx directly, not a coroutine.
    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=make_response(200, {"proxied": True}))
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
    mock.stream = MagicMock(return_value=mock_stream_ctx)

    with patch.object(_client_module, "_client", mock):
        yield mock


@pytest.fixture
def client(mock_http_client):
    """TestClient with mocked downstream + a pre-initialised connection pool."""
    # Patch app.main's imported names — from-import bindings bypass module-level patches.
    with patch("app.main.init_client", AsyncMock()):
        with patch("app.main.close_client", AsyncMock()):
            with TestClient(app) as c:
                yield c


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_token(1)}"}


@pytest.fixture
def auth_headers_user2():
    return {"Authorization": f"Bearer {make_token(2)}"}
