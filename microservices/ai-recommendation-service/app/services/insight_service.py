"""Spending insight generation — aggregation, anomaly detection, AI insights."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# ── Aggregation ───────────────────────────────────────────────────────────────

def aggregate_expenses(expenses: List[Dict]) -> Dict[str, Any]:
    """Aggregate a list of expense dicts into summary statistics."""
    if not expenses:
        return {
            "total": 0.0,
            "by_category": {},
            "count": 0,
            "avg_transaction": 0.0,
        }

    total = sum(float(e.get("amount", 0)) for e in expenses)
    by_cat: Dict[str, float] = {}
    for e in expenses:
        cat = e.get("category", "Other")
        by_cat[cat] = by_cat.get(cat, 0.0) + float(e.get("amount", 0))

    return {
        "total": round(total, 2),
        "by_category": {k: round(v, 2) for k, v in by_cat.items()},
        "count": len(expenses),
        "avg_transaction": round(total / len(expenses), 2) if expenses else 0.0,
    }


# ── Anomaly detection ─────────────────────────────────────────────────────────

_TYPICAL_CATEGORY_PCT = {
    "Food & Dining": 0.15,
    "Transportation": 0.10,
    "Entertainment": 0.08,
    "Shopping": 0.10,
    "Bills & Utilities": 0.20,
    "Healthcare": 0.05,
    "Personal Care": 0.05,
    "Other": 0.05,
}


def detect_anomalies(aggregated: Dict[str, Any]) -> List[Dict]:
    """Flag categories where spending deviates significantly from typical patterns."""
    total = aggregated.get("total", 0)
    by_cat = aggregated.get("by_category", {})
    if not total or not by_cat:
        return []

    anomalies = []
    for cat, amount in by_cat.items():
        pct = amount / total
        typical = _TYPICAL_CATEGORY_PCT.get(cat, 0.08)
        if pct > typical * 1.5:            # 50% above typical
            anomalies.append(
                {
                    "category": cat,
                    "amount": amount,
                    "percentage": round(pct * 100, 1),
                    "typical_percentage": round(typical * 100, 1),
                    "deviation": round((pct / typical - 1) * 100, 1),
                }
            )
    return sorted(anomalies, key=lambda x: x["deviation"], reverse=True)


def anomalies_to_insights(anomalies: List[Dict]) -> List[Dict]:
    """Convert anomaly dicts to Insight dicts."""
    from app.utils.helpers import gen_id

    insights = []
    for a in anomalies:
        insights.append(
            {
                "id": gen_id("ins"),
                "type": "spending_anomaly",
                "title": f"High {a['category']} Spending",
                "message": (
                    f"Your {a['category']} spending is {a['deviation']:.0f}% above typical "
                    f"({a['percentage']:.0f}% of budget vs typical {a['typical_percentage']:.0f}%)."
                ),
                "priority": "high" if a["deviation"] > 100 else "medium",
                "is_urgent": a["deviation"] > 200,
                "supporting_data": a,
            }
        )
    return insights


# ── AI insights ───────────────────────────────────────────────────────────────

def ai_generate_insights(
    user_id: int,
    aggregated: Dict[str, Any],
    anomalies: List[Dict],
) -> List[Dict]:
    """Ask Claude for deeper insights. Returns [] on failure."""
    from app.integrations import claude_client
    from app.utils.helpers import gen_id, parse_json_safely

    prompt = f"""You are a financial wellness coach. Analyse this user's spending data and provide 3-5 actionable insights.

Spending summary:
- Total: ${aggregated.get('total', 0):,.2f}
- By category: {aggregated.get('by_category', {})}
- Anomalies detected: {anomalies}

Return ONLY a valid JSON array:
[
  {{
    "type": "spending_anomaly|savings_opportunity|budget_alert|positive_trend",
    "title": "Short title",
    "message": "Clear, actionable message",
    "priority": "high|medium|low",
    "is_urgent": false,
    "supporting_data": {{}}
  }}
]"""

    text = claude_client.call_claude(prompt)
    if not text:
        return []

    raw_list = parse_json_safely(text, default=[])
    if not isinstance(raw_list, list):
        return []

    result = []
    for item in raw_list:
        if isinstance(item, dict) and item.get("title"):
            result.append({"id": gen_id("ins"), **item})
    return result


def build_spending_analysis(aggregated: Dict, period: str = "last_3_months") -> Dict:
    """Build SpendingAnalysis-compatible dict from aggregated data."""
    total = aggregated.get("total", 0.0)
    by_cat = aggregated.get("by_category", {})

    # Top categories sorted by amount
    sorted_cats = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
    top_categories = [
        {
            "category": cat,
            "amount": amount,
            "percentage": round((amount / total * 100) if total else 0, 1),
        }
        for cat, amount in sorted_cats[:5]
    ]

    # Simple trend determination
    trend = "stable"
    score = 70

    # Find biggest opportunity
    biggest = sorted_cats[0] if sorted_cats else ("N/A", 0)
    opportunity = (
        f"Reducing {biggest[0]} spending by 20% could save ${biggest[1] * 0.20:,.0f}/period"
        if biggest[1] > 0
        else "Track your expenses for personalized insights."
    )

    return {
        "top_categories": top_categories,
        "spending_trend": trend,
        "month_over_month_change": 0.0,
        "vs_similar_users": "Analysis based on your personal data.",
        "biggest_opportunity": opportunity,
        "score": score,
        "score_label": "Good — room for improvement" if score < 80 else "Excellent",
    }
