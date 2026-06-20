"""
Redis-backed rate limiter — one pipeline round trip per request.

Algorithm: fixed window counter
- Key:   rate:{identifier}:{window_start}
- INCR + EXPIRE in a single pipeline = 1 RTT instead of 2

Limits:
- AI/Statement endpoints:              10 req/hour  per user (cost protection)
- Authenticated (X-User-ID present):  RATE_LIMIT_AUTH  req/window  (default 300/min)
- Unauthenticated (IP-based):          RATE_LIMIT_ANON  req/window  (default 60/min)

Fail-open: if Redis is unavailable, requests pass through (availability > strict limiting)

Response headers:
- X-RateLimit-Limit:     max allowed
- X-RateLimit-Remaining: left in this window
- X-RateLimit-Reset:     seconds until window resets
"""

import logging
import time
from typing import Optional

import redis.asyncio as aioredis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

logger = logging.getLogger(__name__)

# AI endpoints: separate hourly limit to prevent cost-exhaustion attacks
_AI_PATH_PREFIXES = ("/api/v1/ai/", "/api/v1/statements/analyze")
_AI_RATE_LIMIT = 10       # 10 calls per hour per user
_AI_RATE_WINDOW = 3600    # 1 hour window

# Suspicious activity: bulk DELETE detection
_BULK_DELETE_LIMIT = 5        # max DELETE requests in _BULK_DELETE_WINDOW seconds
_BULK_DELETE_WINDOW = 60      # 1-minute window

# Suspicious activity: multi-IP detection (same user from many IPs)
_MULTI_IP_LIMIT = 3           # flag if same user_id seen from >N distinct IPs in window
_MULTI_IP_WINDOW = 600        # 10-minute window

_redis: Optional[aioredis.Redis] = None


def _get_redis() -> Optional[aioredis.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
        except Exception as exc:
            logger.warning("Rate-limit Redis unavailable: %s", exc)
    return _redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip rate limit for docs / health
        if path in ("/health", "/", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        r = _get_redis()
        if r is None:
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        client_ip = request.client.host if request.client else "unknown"

        # ── Suspicious activity: bulk DELETE detection ─────────────────────────
        if request.method == "DELETE" and user_id:
            del_window = int(time.time()) // _BULK_DELETE_WINDOW
            del_key = f"del:{user_id}:{del_window}"
            try:
                pipe = r.pipeline()
                pipe.incr(del_key)
                pipe.expire(del_key, _BULK_DELETE_WINDOW)
                del_results = await pipe.execute()
                del_count = int(del_results[0])
                if del_count > _BULK_DELETE_LIMIT:
                    logger.warning(
                        "Bulk DELETE detected: user_id=%s ip=%s count=%d in %ds window",
                        user_id, client_ip, del_count, _BULK_DELETE_WINDOW,
                    )
                    if del_count > _BULK_DELETE_LIMIT * 3:
                        return JSONResponse(
                            {"detail": "Too many delete operations. Try again later."},
                            status_code=429,
                        )
            except Exception as exc:
                logger.warning("Bulk-delete check Redis error: %s", exc)

        # ── Suspicious activity: multi-IP detection ─────────────────────────
        if user_id:
            ip_window = int(time.time()) // _MULTI_IP_WINDOW
            ip_set_key = f"ips:{user_id}:{ip_window}"
            try:
                await r.sadd(ip_set_key, client_ip)
                await r.expire(ip_set_key, _MULTI_IP_WINDOW)
                ip_count = await r.scard(ip_set_key)
                if ip_count > _MULTI_IP_LIMIT:
                    logger.warning(
                        "Multi-IP suspicious activity: user_id=%s seen from %d IPs in %ds",
                        user_id, ip_count, _MULTI_IP_WINDOW,
                    )
            except Exception as exc:
                logger.warning("Multi-IP check Redis error: %s", exc)

        # ── AI-specific rate limit (cost-exhaustion protection) ────────────────
        is_ai_path = any(path.startswith(p) for p in _AI_PATH_PREFIXES)
        if is_ai_path and user_id:
            ai_window_start = int(time.time()) // _AI_RATE_WINDOW
            ai_key = f"rl:ai:{user_id}:{ai_window_start}"
            ai_reset_in = _AI_RATE_WINDOW - (int(time.time()) % _AI_RATE_WINDOW)
            try:
                pipe = r.pipeline()
                pipe.incr(ai_key)
                pipe.expire(ai_key, _AI_RATE_WINDOW)
                results = await pipe.execute()
                ai_count = int(results[0])
            except Exception as exc:
                logger.warning("AI rate-limit Redis error: %s — fail open", exc)
                ai_count = 0

            if ai_count > _AI_RATE_LIMIT:
                return JSONResponse(
                    {"detail": f"AI request limit exceeded. Try again in {ai_reset_in // 60} minutes."},
                    status_code=429,
                    headers={
                        "X-RateLimit-Limit": str(_AI_RATE_LIMIT),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(ai_reset_in),
                        "Retry-After": str(ai_reset_in),
                    },
                )

        # ── Standard rate limit ────────────────────────────────────────────────
        if user_id:
            identifier = f"user:{user_id}"
            limit = settings.RATE_LIMIT_AUTH
        else:
            identifier = f"ip:{client_ip}"
            limit = settings.RATE_LIMIT_ANON

        window = settings.RATE_LIMIT_WINDOW
        window_start = int(time.time()) // window
        key = f"rl:{identifier}:{window_start}"
        reset_in = window - (int(time.time()) % window)

        try:
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            results = await pipe.execute()
            count = int(results[0])
        except Exception as exc:
            logger.warning("Rate-limit Redis error: %s — fail open", exc)
            return await call_next(request)

        remaining = max(0, limit - count)

        if count > limit:
            return JSONResponse(
                {"detail": f"Rate limit exceeded. Try again in {reset_in}s."},
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_in),
                    "Retry-After": str(reset_in),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_in)
        return response
