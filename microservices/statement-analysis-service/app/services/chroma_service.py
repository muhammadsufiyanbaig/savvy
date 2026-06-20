"""ChromaDB client wrapper — lazy-init, non-fatal."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_chroma_client = None


def _get_chroma_client():
    """Return ChromaDB HTTP client or None if unavailable."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    from app.core.config import settings

    try:
        import chromadb

        _chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
        # Ping to verify connection
        _chroma_client.heartbeat()
        logger.info("ChromaDB client connected to %s:%d", settings.CHROMA_HOST, settings.CHROMA_PORT)
        return _chroma_client
    except Exception as exc:
        logger.warning("ChromaDB unavailable: %s — falling back to rule-based categorisation", exc)
        return None


def get_client():
    """Public accessor used by categorisation modules."""
    return _get_chroma_client()
