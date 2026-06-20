"""Lazy Redis client for caching recommendations."""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_redis_client = None


def _get_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    from app.core.config import settings
    try:
        import redis
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        _redis_client.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable: %s", exc)
        return None


def cache_get(key: str) -> Optional[Dict]:
    client = _get_redis_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("Redis get failed: %s", exc)
        return None


def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    client = _get_redis_client()
    if client is None:
        return False
    try:
        client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as exc:
        logger.warning("Redis set failed: %s", exc)
        return False
