"""
Internal service-to-service request signing (HMAC-SHA256).

Attack prevented: compromised container calling other services as if trusted.

Usage — signing (api-gateway proxy):
    from shared.utils.service_auth import sign_request
    headers.update(sign_request("GET", "/api/v1/users/123"))

Usage — verification (downstream service middleware):
    from shared.utils.service_auth import InternalAuthMiddleware
    app.add_middleware(InternalAuthMiddleware)

Env var: INTERNAL_SERVICE_SECRET (shared across all services via docker-compose).
If not set, verification is skipped (dev mode — fail open).
"""

import hashlib
import hmac
import logging
import os
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

_TIMESTAMP_TOLERANCE_SECONDS = 30

# Paths that must come from the api-gateway (not directly from clients)
# Override INTERNAL_ONLY_PREFIXES env var to customise per service.
_INTERNAL_PATHS = frozenset({
    "/internal/",
})


def _get_secret() -> Optional[str]:
    return os.environ.get("INTERNAL_SERVICE_SECRET", "")


def sign_request(method: str, path: str) -> dict:
    """
    Return headers dict to add to an outbound inter-service request.
    Returns empty dict if no secret is configured.
    """
    secret = _get_secret()
    if not secret:
        return {}
    ts = str(int(time.time()))
    message = f"{method.upper()}:{path}:{ts}"
    sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return {
        "X-Internal-Sig": sig,
        "X-Internal-Timestamp": ts,
    }


def verify_signature(method: str, path: str, sig: str, timestamp: str) -> bool:
    """Validate X-Internal-Sig. Returns True if valid or if no secret is configured."""
    secret = _get_secret()
    if not secret:
        return True  # dev mode — no secret configured
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > _TIMESTAMP_TOLERANCE_SECONDS:
            logger.warning("Internal request replay detected: timestamp delta = %ds", abs(time.time() - ts))
            return False
        message = f"{method.upper()}:{path}:{timestamp}"
        expected = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)
    except Exception as exc:
        logger.warning("Service signature verification error: %s", exc)
        return False


class InternalAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for downstream services: validates X-Internal-Sig on every request.

    In development (no INTERNAL_SERVICE_SECRET): logs warning but passes through.
    In production (secret set): rejects requests missing or with invalid signatures with 403.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip health checks and public paths
        if path in ("/health", "/", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        secret = _get_secret()
        sig = request.headers.get("x-internal-sig", "")
        ts = request.headers.get("x-internal-timestamp", "")

        if not secret:
            # Dev mode: no secret configured — log once and pass through
            return await call_next(request)

        if not sig or not ts:
            logger.warning("Missing internal auth headers on %s %s", request.method, path)
            return JSONResponse({"detail": "Missing internal authentication headers"}, status_code=403)

        if not verify_signature(request.method, path, sig, ts):
            logger.warning("Invalid internal signature on %s %s", request.method, path)
            return JSONResponse({"detail": "Invalid internal request signature"}, status_code=403)

        return await call_next(request)
