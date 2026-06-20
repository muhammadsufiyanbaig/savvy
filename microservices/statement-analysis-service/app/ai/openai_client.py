"""Lazy-init OpenAI client used as fallback when Claude is unavailable."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    from app.core.config import settings

    if not settings.OPENAI_API_KEY:
        return None

    try:
        import openai

        _client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("OpenAI client initialised")
        return _client
    except Exception as exc:
        logger.warning("OpenAI client init failed: %s", exc)
        return None


def call_openai(prompt: str, max_tokens: int = 4096) -> Optional[str]:
    """Send prompt to GPT-4o-mini; return text or None on failure."""
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=max_tokens,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as exc:
        logger.error("OpenAI call failed: %s", exc)
        return None
