"""Redis client for processing-status caching — lazy-init, non-fatal."""

import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_redis_client = None


def _get_redis_client():
    """Return redis.Redis instance or None if unavailable."""
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


def get_status(statement_id: str) -> Optional[Dict]:
    """Retrieve processing status from Redis. Returns None if not found."""
    client = _get_redis_client()
    if client is None:
        return None

    try:
        raw = client.get(f"stmt_status:{statement_id}")
        if raw:
            return json.loads(raw)
        return None
    except Exception as exc:
        logger.warning("Redis get_status error: %s", exc)
        return None


def set_status(statement_id: str, status: Dict, ttl: Optional[int] = None) -> bool:
    """Store processing status in Redis. Returns True on success."""
    client = _get_redis_client()
    if client is None:
        return False

    from app.core.config import settings

    ttl = ttl or settings.REDIS_CACHE_TTL

    try:
        client.setex(
            f"stmt_status:{statement_id}",
            ttl,
            json.dumps(status),
        )
        return True
    except Exception as exc:
        logger.warning("Redis set_status error: %s", exc)
        return False
