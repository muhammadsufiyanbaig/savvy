"""ChromaDB vector-similarity categoriser. Falls back to None on any failure."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def categorise(description: str, chroma_client=None) -> Optional[Dict]:
    """Query ChromaDB for similar transactions.

    Returns categorisation dict or None (caller should fall back to rule-based).
    """
    if chroma_client is None:
        return None

    try:
        from app.core.config import settings

        collection = chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

        results = collection.query(query_texts=[description], n_results=5)
        ids = results.get("ids", [[]])[0]
        if not ids:
            return None

        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # Aggregate votes
        votes: Dict[str, int] = {}
        for meta in metadatas:
            cat = meta.get("category", "")
            if cat:
                votes[cat] = votes.get(cat, 0) + 1

        if not votes:
            return None

        top_cat = max(votes, key=lambda k: votes[k])
        confidence = votes[top_cat] / len(ids)
        # Convert cosine distance to similarity (lower distance = better)
        avg_distance = sum(distances) / len(distances) if distances else 1.0
        similarity = max(0.0, 1.0 - avg_distance)

        top_sub = None
        for meta in metadatas:
            if meta.get("category") == top_cat and meta.get("subcategory"):
                top_sub = meta["subcategory"]
                break

        return {
            "category": top_cat,
            "subcategory": top_sub,
            "confidence_score": round(confidence * 0.7 + similarity * 0.3, 4),
            "tags": [],
            "categorization_method": "vector",
            "similar_transactions": [
                {"description": d, "similarity_score": round(1 - dist, 4)}
                for d, dist in zip(results.get("documents", [[]])[0][:3], distances[:3])
            ],
        }
    except Exception as exc:
        logger.warning("Vector categorisation failed for '%s': %s", description, exc)
        return None


def add_pattern(
    description: str,
    category: str,
    subcategory: Optional[str],
    chroma_client=None,
) -> bool:
    """Store a transaction pattern in ChromaDB for future similarity matching."""
    if chroma_client is None:
        return False

    try:
        from app.core.config import settings

        collection = chroma_client.get_or_create_collection(name=settings.CHROMA_COLLECTION)
        doc_id = f"txn_{abs(hash(description))}"
        collection.upsert(
            documents=[description],
            ids=[doc_id],
            metadatas=[{"category": category, "subcategory": subcategory or ""}],
        )
        return True
    except Exception as exc:
        logger.warning("Failed to add vector pattern: %s", exc)
        return False
