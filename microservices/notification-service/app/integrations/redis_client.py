"""Redis client — lazy init, non-fatal."""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)
_client = None


def _get_redis_client():
    global _client
    if _client is None:
        try:
            import redis as redis_lib
            from app.core.config import settings
            _client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
            _client.ping()
        except Exception as exc:
            logger.warning("Redis unavailable: %s", exc)
            _client = None
    return _client


def cache_get(key: str) -> Optional[Any]:
    r = _get_redis_client()
    if not r:
        return None
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("Redis GET failed for %s: %s", key, exc)
        return None


def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    r = _get_redis_client()
    if not r:
        return False
    try:
        r.setex(key, ttl, json.dumps(value))
        return True
    except Exception as exc:
        logger.warning("Redis SET failed for %s: %s", key, exc)
        return False


def cache_delete(key: str) -> bool:
    r = _get_redis_client()
    if not r:
        return False
    try:
        r.delete(key)
        return True
    except Exception as exc:
        logger.warning("Redis DELETE failed for %s: %s", key, exc)
        return False


def cache_incr(key: str, ttl: int = 3600) -> Optional[int]:
    """Increment a counter; create with TTL if new. Returns new value or None."""
    r = _get_redis_client()
    if not r:
        return None
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        results = pipe.execute()
        return results[0]
    except Exception as exc:
        logger.warning("Redis INCR failed for %s: %s", key, exc)
        return None
