"""
Lazy ChromaDB client with financial-data helpers.

Security:
- Per-user collections (`u{user_id}_history`) — cross-user contamination impossible
  even if the `where` filter were bypassed; each user's embeddings live in a separate namespace.
- Server-side auth token (`CHROMA_AUTH_TOKEN` env var) — rejects unauthenticated writes.
- `where` filter always includes `{"user_id": str(user_id)}` as secondary guard.
"""

import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_client = None


def _get_chroma_client():
    global _client
    if _client is not None:
        return _client

    from app.core.config import settings
    try:
        import chromadb

        auth_token = os.environ.get("CHROMA_AUTH_TOKEN", "")
        if auth_token:
            _client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                headers={"Authorization": f"Bearer {auth_token}"},
            )
        else:
            _client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)

        _client.heartbeat()
        logger.info("ChromaDB connected (auth=%s)", "yes" if auth_token else "no")
        return _client
    except Exception as exc:
        logger.warning("ChromaDB unavailable: %s", exc)
        return None


def _user_collection(user_id: int):
    """Return a per-user ChromaDB collection. Cross-user contamination is impossible
    because each user's embeddings are stored in a separate namespace."""
    client = _get_chroma_client()
    if client is None:
        return None
    collection_name = f"u{user_id}_history"
    return client.get_or_create_collection(collection_name)


def get_user_investment_context(user_id: int) -> Dict:
    """Retrieve stored spending / investment patterns for user."""
    col = _user_collection(user_id)
    if col is None:
        return {}

    try:
        results = col.query(
            query_texts=[f"user {user_id} investment history"],
            n_results=5,
            # Redundant where-filter: secondary guard even within the per-user collection
            where={"user_id": str(user_id)},
        )
        docs = results.get("documents", [[]])[0]
        return {"history_docs": docs}
    except Exception as exc:
        logger.warning("ChromaDB user context query failed: %s", exc)
        return {}


def store_expense_pattern(user_id: int, expense: Dict) -> bool:
    """Persist expense embedding for future RAG queries."""
    col = _user_collection(user_id)
    if col is None:
        return False

    try:
        text = (
            f"Category: {expense.get('category', '?')}. "
            f"Amount: {expense.get('amount', 0)}. "
            f"Description: {expense.get('description', '?')}."
        )
        doc_id = f"expense_{user_id}_{expense.get('id', hash(text))}"
        col.upsert(
            documents=[text],
            ids=[doc_id],
            metadatas=[{"user_id": str(user_id), "type": "expense"}],
        )
        return True
    except Exception as exc:
        logger.warning("ChromaDB store_expense_pattern failed: %s", exc)
        return False


def delete_user_data(user_id: int) -> bool:
    """Delete entire per-user collection (GDPR / account deletion)."""
    client = _get_chroma_client()
    if client is None:
        return False
    try:
        client.delete_collection(f"u{user_id}_history")
        return True
    except Exception as exc:
        logger.warning("ChromaDB delete_user_data failed: %s", exc)
        return False
