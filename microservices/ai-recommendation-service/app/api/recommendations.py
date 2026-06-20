"""Recommendation & spending-analysis endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.recommendation import (
    FeedbackRequest,
    FeedbackResponse,
    RecommendationRequest,
    RecommendationResponse,
    SpendingAnalysisRequest,
    SpendingAnalysisResponse,
    Recommendation,
    SpendingAnalysis,
    SpendingCategory,
)

router = APIRouter()


@router.post("/recommendations", response_model=RecommendationResponse)
def generate_recommendations(
    request: RecommendationRequest,
    user_id: int = Depends(get_current_user),
):
    from app.workflows import recommendation_workflow
    from app.utils.helpers import now_iso
    from app.events import producer

    # IDOR guard: never use user_id from request body — always use JWT-validated identity
    if request.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Cannot request recommendations for another user")

    result = recommendation_workflow.run(
        {
            "user_id": user_id,
            "recommendation_types": request.recommendation_types,
            "context": request.context,
            "user_profile": {},
            "ai_recommendations": [],
            "fallback_recommendations": [],
            "final": [],
            "error": None,
        }
    )

    recs_raw = result.get("final", [])
    recs = [Recommendation(**r) for r in recs_raw if isinstance(r, dict)]

    model_used = "claude+langgraph" if any(
        r.get("confidence_score", 0) > 0.9 for r in recs_raw
    ) else "rule-based+langgraph"

    # Publish events (fire-and-forget)
    for rec in recs_raw[:3]:
        producer.publish_recommendation_generated(request.user_id, rec)

    return RecommendationResponse(
        recommendations=recs,
        generated_at=now_iso(),
        model_used=model_used,
        total_count=len(recs),
    )


@router.post("/analyze-spending", response_model=SpendingAnalysisResponse)
def analyze_spending(
    request: SpendingAnalysisRequest,
    user_id: int = Depends(get_current_user),
):
    from app.workflows import spending_workflow
    from app.services import insight_service

    if request.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Cannot analyze spending for another user")

    expenses = request.expenses or []
    result = spending_workflow.run(
        {
            "user_id": user_id,
            "period": request.period,
            "expenses": expenses,
            "aggregated": {},
            "anomalies": [],
            "ai_insights": [],
            "final_insights": [],
            "error": None,
        }
    )

    aggregated = result.get("aggregated", {})
    analysis_dict = insight_service.build_spending_analysis(aggregated, request.period)

    top_cats = [SpendingCategory(**c) for c in analysis_dict.pop("top_categories", [])]
    return SpendingAnalysisResponse(
        analysis=SpendingAnalysis(top_categories=top_cats, **analysis_dict)
    )


@router.post("/recommendations/{recommendation_id}/feedback", response_model=FeedbackResponse)
def submit_feedback(
    recommendation_id: str,
    request: FeedbackRequest,
    user_id: int = Depends(get_current_user),
):
    from app.integrations import redis_client
    from app.utils.helpers import now_iso
    import logging
    import json

    _logger = logging.getLogger(__name__)

    redis_client.cache_set(
        f"rec_feedback:{recommendation_id}:{user_id}",
        {
            "rating": request.rating,
            "was_helpful": request.was_helpful,
            "feedback_text": request.feedback_text,
            "is_implemented": request.is_implemented,
            "submitted_at": now_iso(),
        },
        ttl=86400 * 30,
    )

    # Bot/poisoning detection: flag users who rate everything identically
    # (systematic false feedback to poison future recommendation tuning)
    _detect_feedback_bot(user_id, request.rating, _logger)

    return FeedbackResponse(
        recommendation_id=recommendation_id,
        feedback_recorded=True,
        message="Thank you for your feedback!",
    )


def _detect_feedback_bot(user_id: int, rating: int, logger) -> None:
    """
    Append rating to a rolling window; flag user if last 10 ratings are identical.
    Feedback is stored in Redis only — never auto-fed into ChromaDB or used for retraining.
    """
    from app.integrations import redis_client
    import json

    r_client = redis_client._get_redis_client()
    if r_client is None:
        return

    try:
        key = f"fb_history:{user_id}"
        r_client.rpush(key, str(rating))
        r_client.ltrim(key, -10, -1)    # keep last 10
        r_client.expire(key, 86400 * 7)

        history_raw = r_client.lrange(key, 0, -1)
        if len(history_raw) >= 10:
            ratings = [int(x) for x in history_raw]
            if len(set(ratings)) == 1:
                r_client.setex(f"fb_bot_flag:{user_id}", 86400 * 30, "1")
                logger.warning(
                    "Potential feedback bot detected: user_id=%s rated 10 consecutive recs identically (rating=%d)",
                    user_id, ratings[0],
                )
    except Exception as exc:
        logger.warning("Feedback bot detection error: %s", exc)
