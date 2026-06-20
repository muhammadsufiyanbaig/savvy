"""Investment recommendation endpoints."""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models.investment import (
    Investment,
    InvestmentRequest,
    InvestmentResponse,
    MarketSummary,
    ShariahInvestmentRequest,
    ShariahInvestmentResponse,
)

router = APIRouter()


@router.post("/investments", response_model=InvestmentResponse)
def get_investment_recommendations(
    request: InvestmentRequest,
    user_id: int = Depends(get_current_user),
):
    from app.workflows import investment_workflow
    from app.utils.helpers import gen_id, now_iso
    from app.events import producer

    result = investment_workflow.run(
        {
            "user_id": request.user_id,
            "available_amount": request.available_amount,
            "risk_tolerance": request.risk_tolerance,
            "time_horizon": request.time_horizon,
            "country": request.country,
            "city": request.city,
            "shariah_required": request.shariah_compliant,
            "preferred_sectors": request.preferred_sectors,
            "user_context": {},
            "market_summary": {},
            "candidate_investments": [],
            "filtered_investments": [],
            "final_recommendations": [],
            "error": None,
        }
    )

    raw_recs = result.get("final_recommendations", [])
    # Allocate per-investment amount proportionally
    per_inv = (
        round(request.available_amount / len(raw_recs), 2) if raw_recs else 0.0
    )

    investments = []
    for r in raw_recs:
        r = {**r}
        if not r.get("recommended_amount") or r["recommended_amount"] == 0:
            r["recommended_amount"] = per_inv
        if not r.get("time_horizon"):
            r["time_horizon"] = request.time_horizon
        if not r.get("id"):
            r["id"] = gen_id("inv")
        investments.append(Investment(**{k: r[k] for k in Investment.model_fields if k in r}))

    market_raw = result.get("market_summary", {})
    market = MarketSummary(
        trend=market_raw.get("trend", "neutral"),
        sp500_ytd=market_raw.get("sp500_ytd", 0.0),
        recommendation_basis=market_raw.get("recommendation_basis", ""),
    )

    # Publish events
    for inv in investments[:3]:
        producer.publish_investment_recommended(request.user_id, inv.model_dump())

    return InvestmentResponse(
        investments=investments,
        market_summary=market,
        generated_at=now_iso(),
        total_count=len(investments),
    )


@router.post("/investments/shariah", response_model=ShariahInvestmentResponse)
def get_shariah_investments(
    request: ShariahInvestmentRequest,
    user_id: int = Depends(get_current_user),
):
    from app.workflows import investment_workflow
    from app.services.shariah_checker import ShariahChecker
    from app.utils.helpers import gen_id, now_iso

    # Run workflow with shariah=True
    result = investment_workflow.run(
        {
            "user_id": request.user_id,
            "available_amount": request.available_amount,
            "risk_tolerance": request.risk_tolerance,
            "time_horizon": "medium",
            "country": request.country,
            "city": None,
            "shariah_required": True,
            "preferred_sectors": [],
            "user_context": {},
            "market_summary": {},
            "candidate_investments": [],
            "filtered_investments": [],
            "final_recommendations": [],
            "error": None,
        }
    )

    raw = result.get("final_recommendations", [])
    checker = ShariahChecker()
    investments = []
    for r in raw:
        r = {**r, "is_shariah_compliant": True}
        if not r.get("id"):
            r["id"] = gen_id("inv")
        if not r.get("recommended_amount"):
            r["recommended_amount"] = round(request.available_amount / max(len(raw), 1), 2)
        if not r.get("time_horizon"):
            r["time_horizon"] = "medium"
        investments.append(Investment(**{k: r[k] for k in Investment.model_fields if k in r}))

    return ShariahInvestmentResponse(
        investments=investments,
        shariah_screening_note=checker.get_screening_note(),
        excluded_categories=checker.get_excluded_categories(),
        generated_at=now_iso(),
    )
