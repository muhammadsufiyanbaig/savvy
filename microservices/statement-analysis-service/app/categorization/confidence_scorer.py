"""Confidence scoring helpers."""

from typing import Dict


_HIGH = 0.85
_MEDIUM = 0.65


def score_level(confidence: float) -> str:
    """Map float → 'high' | 'medium' | 'low'."""
    if confidence >= _HIGH:
        return "high"
    if confidence >= _MEDIUM:
        return "medium"
    return "low"


def combine(
    cat_confidence: float,
    extraction_confidence: float,
    method: str,
) -> float:
    """Produce a final confidence blending categorisation + extraction quality."""
    method_bonus = {
        "vector": 0.15,
        "rule": 0.05,
        "ai_hint": 0.0,
        "ai": 0.10,
    }.get(method, 0.0)

    final = (cat_confidence * 0.60) + (extraction_confidence * 0.30) + method_bonus
    return round(min(1.0, max(0.0, final)), 4)


def count_by_level(confidence_scores: list) -> Dict[str, int]:
    """Count transactions per confidence level."""
    counts = {"high": 0, "medium": 0, "low": 0}
    for score in confidence_scores:
        counts[score_level(score)] += 1
    return counts
