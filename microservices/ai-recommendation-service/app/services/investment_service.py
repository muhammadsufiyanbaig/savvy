"""Investment candidate generation — Claude AI + rule-based fallback."""

import json
import logging
import uuid
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── Fallback investment pools per risk level ───────────────────────────────────

_FALLBACK_INVESTMENTS: Dict[str, List[Dict]] = {
    "low": [
        {
            "investment_type": "sukuk",
            "asset_name": "US Treasury Bills (halal-equivalent short-term)",
            "asset_symbol": "BIL",
            "expected_return": 4.5,
            "risk_level": "low",
            "sector": "government",
            "is_shariah_compliant": False,
            "debt_ratio": 0.0,
            "interest_income_ratio": 0.01,
            "analysis": "Short-term government securities offering capital preservation.",
            "pros": ["Low risk", "Liquid", "Stable returns"],
            "cons": ["Returns may not beat inflation"],
            "confidence_score": 0.80,
        },
        {
            "investment_type": "mutual_funds",
            "asset_name": "Vanguard Total Bond Market ETF",
            "asset_symbol": "BND",
            "expected_return": 5.2,
            "risk_level": "low",
            "sector": "fixed_income",
            "is_shariah_compliant": False,
            "debt_ratio": 0.10,
            "interest_income_ratio": 0.40,  # bond fund — not Shariah compliant
            "analysis": "Diversified bond fund providing stable income.",
            "pros": ["Diversified", "Low expense ratio"],
            "cons": ["Interest-bearing — not Shariah compliant"],
            "confidence_score": 0.78,
        },
    ],
    "medium": [
        {
            "investment_type": "stocks",
            "asset_name": "Apple Inc.",
            "asset_symbol": "AAPL",
            "expected_return": 12.0,
            "risk_level": "medium",
            "sector": "technology",
            "is_shariah_compliant": False,
            "debt_ratio": 0.18,
            "interest_income_ratio": 0.02,
            "analysis": "Global technology leader with strong fundamentals and consistent growth.",
            "pros": ["Strong brand", "Diversified revenue", "Services growth"],
            "cons": ["High valuation", "Hardware dependency"],
            "confidence_score": 0.85,
        },
        {
            "investment_type": "etf",
            "asset_name": "iShares MSCI World ETF",
            "asset_symbol": "URTH",
            "expected_return": 9.5,
            "risk_level": "medium",
            "sector": "diversified",
            "is_shariah_compliant": False,
            "debt_ratio": 0.12,
            "interest_income_ratio": 0.03,
            "analysis": "Broad global equity exposure across developed markets.",
            "pros": ["Global diversification", "Low cost", "Passive strategy"],
            "cons": ["Currency risk", "Contains some non-compliant stocks"],
            "confidence_score": 0.82,
        },
        {
            "investment_type": "mutual_funds",
            "asset_name": "Amana Growth Fund",
            "asset_symbol": "AMAGX",
            "expected_return": 9.8,
            "risk_level": "medium",
            "sector": "diversified",
            "is_shariah_compliant": True,
            "debt_ratio": 0.15,
            "interest_income_ratio": 0.00,
            "analysis": "Shariah-compliant growth fund with long track record.",
            "pros": ["Shariah screened", "Diversified", "Low minimum"],
            "cons": ["Higher expense ratio", "Limited to halal companies"],
            "confidence_score": 0.88,
        },
    ],
    "high": [
        {
            "investment_type": "stocks",
            "asset_name": "NVIDIA Corporation",
            "asset_symbol": "NVDA",
            "expected_return": 25.0,
            "risk_level": "high",
            "sector": "technology",
            "is_shariah_compliant": False,
            "debt_ratio": 0.08,
            "interest_income_ratio": 0.01,
            "analysis": "AI chip leader benefiting from exponential AI infrastructure demand.",
            "pros": ["AI tailwind", "Market dominance", "Strong margins"],
            "cons": ["Very high valuation", "Cyclical risk"],
            "confidence_score": 0.75,
        },
    ],
}


def generate_investment_candidates(state: Dict) -> List[Dict]:
    """Generate investment candidates via Claude or fallback."""
    from app.integrations import claude_client
    from app.utils.helpers import gen_id, parse_json_safely

    risk = state.get("risk_tolerance", "medium")
    country = state.get("country", "USA")
    amount = state.get("available_amount", 1000)
    shariah = state.get("shariah_required", False)
    sectors = state.get("preferred_sectors", [])
    market = state.get("market_summary", {})

    prompt = f"""You are a financial investment advisor. Generate investment recommendations.

User profile:
- Available amount: ${amount:,.0f}
- Risk tolerance: {risk}
- Country: {country}
- Shariah compliant required: {shariah}
- Preferred sectors: {', '.join(sectors) if sectors else 'any'}
- Market trend: {market.get('trend','neutral')} ({market.get('sp500_ytd',0):+.1f}% YTD)

Generate 5 investment candidates. Return ONLY a valid JSON array:
[
  {{
    "investment_type": "stocks|etf|mutual_funds|sukuk|bonds",
    "asset_name": "Full name",
    "asset_symbol": "TICKER",
    "expected_return": 10.5,
    "risk_level": "{risk}",
    "sector": "technology",
    "is_shariah_compliant": false,
    "debt_ratio": 0.15,
    "interest_income_ratio": 0.02,
    "analysis": "Brief analysis (2 sentences)",
    "pros": ["pro1", "pro2"],
    "cons": ["con1"],
    "confidence_score": 0.85
  }}
]"""

    ai_text = claude_client.call_claude(prompt)
    candidates = parse_json_safely(ai_text, default=[]) if ai_text else []

    if candidates and isinstance(candidates, list):
        normalised = [_normalise_candidate(c) for c in candidates if isinstance(c, dict)]
        return normalised

    # Fallback to static pool
    pool = _FALLBACK_INVESTMENTS.get(risk, _FALLBACK_INVESTMENTS["medium"]).copy()
    # Allocate amounts proportionally
    per_inv = amount / max(len(pool), 1)
    for inv in pool:
        inv = inv.copy()
        inv["recommended_amount"] = round(per_inv, 2)
    return pool


def _normalise_candidate(raw: Dict) -> Dict:
    from app.utils.helpers import gen_id
    return {
        "id": gen_id("inv"),
        "investment_type": raw.get("investment_type", "stocks"),
        "asset_name": raw.get("asset_name", "Unknown"),
        "asset_symbol": raw.get("asset_symbol"),
        "recommended_amount": float(raw.get("recommended_amount", 0)),
        "current_price": raw.get("current_price"),
        "target_price": raw.get("target_price"),
        "expected_return": float(raw.get("expected_return", 0)),
        "risk_level": raw.get("risk_level", "medium"),
        "time_horizon": raw.get("time_horizon", "long"),
        "is_shariah_compliant": bool(raw.get("is_shariah_compliant", False)),
        "sector": raw.get("sector"),
        "debt_ratio": float(raw.get("debt_ratio", 0)),
        "interest_income_ratio": float(raw.get("interest_income_ratio", 0)),
        "analysis": raw.get("analysis", ""),
        "pros": raw.get("pros", []),
        "cons": raw.get("cons", []),
        "confidence_score": float(raw.get("confidence_score", 0.7)),
    }
