"""Financial insights endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.models.recommendation import Insight, InsightsResponse

router = APIRouter()


@router.get("/insights", response_model=InsightsResponse)
def get_insights(
    user_id_param: Optional[int] = Query(None, alias="user_id"),
    period: str = Query("monthly"),
    user_id: int = Depends(get_current_user),
):
    from app.utils.helpers import gen_id, now_iso
    from app.integrations import redis_client

    target_user = user_id_param or user_id

    # Check cache
    cache_key = f"insights:{target_user}:{period}"
    cached = redis_client.cache_get(cache_key)
    if cached:
        return InsightsResponse(**cached)

    # Rule-based default insights (always available)
    insights = [
        Insight(
            id=gen_id("ins"),
            type="savings_opportunity",
            title="Review Your Recurring Subscriptions",
            message=(
                "Audit your bank statements for unused subscriptions. "
                "Average user saves $35–$80/month by cancelling 2–3 services."
            ),
            priority="medium",
            is_urgent=False,
            supporting_data={"potential_savings_min": 35, "potential_savings_max": 80},
        ),
        Insight(
            id=gen_id("ins"),
            type="budget_alert",
            title="Set Up Automatic Savings Transfers",
            message=(
                "Automating savings on payday prevents spending money earmarked for goals. "
                "Even $50/month grows to $600+/year."
            ),
            priority="medium",
            is_urgent=False,
            supporting_data={"annual_savings_estimate": 600},
        ),
    ]

    result = InsightsResponse(
        insights=insights,
        generated_at=now_iso(),
        total_count=len(insights),
    )

    # Cache for 1 hour
    redis_client.cache_set(cache_key, result.model_dump(), ttl=3600)

    return result
