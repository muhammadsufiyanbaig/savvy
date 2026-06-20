"""
Shared httpx.AsyncClient — created once at startup, reused for every request.

Why this matters for latency:
- TCP handshake:   ~50–200ms  (happens ONCE per connection, not per request)
- TLS handshake:   ~100–300ms (happens ONCE per connection, not per request)
- HTTP/2:          multiplexes multiple requests over one connection
- Keep-alive pool: 20 warm connections always ready
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    """Return the shared pooled client. Must call init_client() at startup first."""
    if _client is None:
        raise RuntimeError("HTTP client not initialised. Call init_client() in lifespan.")
    return _client


async def init_client() -> None:
    """Create the shared AsyncClient with connection pool. Call on app startup."""
    global _client
    limits = httpx.Limits(
        max_keepalive_connections=settings.HTTP_POOL_MAX_KEEPALIVE,
        max_connections=settings.HTTP_POOL_MAX_CONNECTIONS,
        keepalive_expiry=30,          # seconds before idle connection is closed
    )
    _client = httpx.AsyncClient(
        limits=limits,
        timeout=httpx.Timeout(settings.HTTP_TIMEOUT, connect=5.0),
        http2=True,                   # HTTP/2 multiplexing when server supports it
        follow_redirects=False,
    )
    logger.info(
        "HTTP client pool ready (max=%d, keepalive=%d, http2=True)",
        settings.HTTP_POOL_MAX_CONNECTIONS,
        settings.HTTP_POOL_MAX_KEEPALIVE,
    )


async def close_client() -> None:
    """Close all pooled connections. Call on app shutdown."""
    global _client
    if _client:
        await _client.aclose()
        _client = None
        logger.info("HTTP client pool closed")
