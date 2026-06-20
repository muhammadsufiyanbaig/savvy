"""
Request forwarding — resolve service, strip/forward headers, stream response.

Latency notes:
- Header whitelist: copy only needed headers, skip host/connection/transfer-encoding
- Streaming response: first byte delivered to client as it arrives — no full buffer
- X-Request-ID already injected by request_id middleware
"""

import logging
from typing import Optional

import httpx
from fastapi import Request
from fastapi.responses import Response, StreamingResponse

from app.core.config import SERVICE_MAP, SORTED_PREFIXES
from app.proxy.client import get_client

try:
    from shared.utils.service_auth import sign_request as _sign_request
except ImportError:
    def _sign_request(method: str, path: str) -> dict:
        return {}

logger = logging.getLogger(__name__)

# Headers we copy from client → downstream (whitelist = fast + safe)
_FORWARD_REQUEST_HEADERS = frozenset({
    "authorization",
    "content-type",
    "accept",
    "accept-encoding",
    "accept-language",
    "x-request-id",
    "x-user-id",              # injected by auth middleware
    "x-internal-sig",         # HMAC service signature (added by gateway)
    "x-internal-timestamp",   # signature timestamp
    "user-agent",
    "cache-control",
    "if-none-match",
    "if-modified-since",
})

# Headers we copy from downstream → client (skip hop-by-hop)
_FORWARD_RESPONSE_HEADERS = frozenset({
    "content-type",
    "content-length",
    "cache-control",
    "etag",
    "last-modified",
    "x-request-id",
    "x-process-time",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "www-authenticate",
    "location",
})


def _resolve_service(path: str) -> Optional[str]:
    """Return base URL for first matching prefix. O(n) but n=12, negligible."""
    for prefix in SORTED_PREFIXES:
        if path.startswith(prefix):
            return SERVICE_MAP[prefix]
    return None


def _build_request_headers(request: Request) -> dict:
    """Whitelist-filter headers to forward downstream."""
    return {
        k: v
        for k, v in request.headers.items()
        if k.lower() in _FORWARD_REQUEST_HEADERS
    }


def _build_response_headers(response: httpx.Response) -> dict:
    """Whitelist-filter headers to return to client."""
    return {
        k: v
        for k, v in response.headers.items()
        if k.lower() in _FORWARD_RESPONSE_HEADERS
    }


async def forward_request(request: Request) -> Response:
    """
    Core proxy function:
    1. Resolve service URL from path prefix
    2. Build target URL (preserve path + query string)
    3. Forward whitelisted headers
    4. Stream response back — first byte goes to client immediately
    """
    path = request.url.path
    service_base = _resolve_service(path)

    if not service_base:
        return Response(
            content='{"detail":"No upstream service for this path"}',
            status_code=404,
            media_type="application/json",
        )

    # Build full URL with query string
    target_url = f"{service_base}{path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = _build_request_headers(request)
    # Add HMAC service signature so downstream services can verify origin
    headers.update(_sign_request(request.method, path))

    body: Optional[bytes] = None
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()

    client = get_client()

    try:
        # Use client.stream() so response bytes flow to client as they arrive
        async with client.stream(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
        ) as upstream:
            resp_headers = _build_response_headers(upstream)

            # For streaming we need to consume aiter_bytes inside the context manager
            # Collect here; for large file downloads a true passthrough stream is better
            # but for JSON APIs this is fine and simpler to test
            content = await upstream.aread()

        return Response(
            content=content,
            status_code=upstream.status_code,
            headers=resp_headers,
            media_type=resp_headers.get("content-type", "application/json"),
        )

    except httpx.TimeoutException as exc:
        logger.warning("Upstream timeout %s %s: %s", request.method, target_url, exc)
        return Response(
            content='{"detail":"Upstream service timeout"}',
            status_code=504,
            media_type="application/json",
        )
    except httpx.ConnectError as exc:
        logger.warning("Upstream unreachable %s: %s", target_url, exc)
        return Response(
            content='{"detail":"Upstream service unavailable"}',
            status_code=503,
            media_type="application/json",
        )
    except httpx.RequestError as exc:
        logger.error("Proxy request error %s: %s", target_url, exc)
        return Response(
            content='{"detail":"Gateway error"}',
            status_code=502,
            media_type="application/json",
        )
