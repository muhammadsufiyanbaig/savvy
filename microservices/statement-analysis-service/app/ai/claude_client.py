"""Lazy-init Anthropic Claude client with prompt caching support."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    from app.core.config import settings
    if not settings.ANTHROPIC_API_KEY:
        return None

    try:
        from anthropic import Anthropic
        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        logger.info("Anthropic client initialised")
        return _client
    except Exception as exc:
        logger.warning("Anthropic client init failed: %s", exc)
        return None


def call_claude(prompt: str, max_tokens: int = 4096) -> Optional[str]:
    """Basic call — no caching. Use call_claude_cached for large static prompts."""
    client = _get_client()
    if client is None:
        return None

    from app.core.config import settings
    try:
        response = client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=max_tokens,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as exc:
        logger.error("Claude call failed: %s", exc)
        return None


def call_claude_cached(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 4096,
) -> Optional[str]:
    """
    Call Claude with prompt caching on the system prompt.

    The system_prompt is marked with cache_control="ephemeral" — Anthropic caches
    it for 5 minutes after first use. Cache hits cost ~10× less (input tokens).
    Requires system_prompt >= 1024 tokens to activate caching (sonnet models).

    Returns the text response, or None on failure.
    """
    client = _get_client()
    if client is None:
        return None

    from app.core.config import settings
    try:
        response = client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=max_tokens,
            temperature=0,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {"role": "user", "content": user_message},
            ],
        )
        usage = getattr(response, "usage", None)
        if usage:
            cache_read   = getattr(usage, "cache_read_input_tokens", 0) or 0
            cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
            if cache_read:
                logger.debug("Cache HIT  — %d tokens read from cache", cache_read)
            elif cache_create:
                logger.debug("Cache MISS — %d tokens written to cache", cache_create)
        return response.content[0].text
    except Exception as exc:
        logger.error("Claude cached call failed: %s", exc)
        return None
