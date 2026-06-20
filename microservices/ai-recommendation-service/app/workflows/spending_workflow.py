"""Spending analysis workflow: aggregate → detect anomalies → AI insights."""

import logging
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


class SpendingState(TypedDict):
    user_id: int
    period: str
    expenses: List[Dict[str, Any]]
    # computed
    aggregated: Dict[str, Any]
    anomalies: List[Dict]
    ai_insights: List[Dict]
    final_insights: List[Dict]
    error: Optional[str]


def _node_aggregate(state: SpendingState) -> Dict:
    from app.services import insight_service
    agg = insight_service.aggregate_expenses(state.get("expenses", []))
    return {"aggregated": agg}


def _node_detect_anomalies(state: SpendingState) -> Dict:
    from app.services import insight_service
    anomalies = insight_service.detect_anomalies(state.get("aggregated", {}))
    return {"anomalies": anomalies}


def _node_ai_insights(state: SpendingState) -> Dict:
    from app.services import insight_service
    insights = insight_service.ai_generate_insights(
        state["user_id"],
        state.get("aggregated", {}),
        state.get("anomalies", []),
    )
    return {"ai_insights": insights}


def _node_finalize(state: SpendingState) -> Dict:
    ai = state.get("ai_insights", [])
    anomalies = state.get("anomalies", [])
    # Convert anomalies to insight dicts and merge with AI insights
    from app.services import insight_service
    converted = insight_service.anomalies_to_insights(anomalies)
    combined = ai if ai else converted
    return {"final_insights": combined[:10]}


def _build_workflow():
    builder = StateGraph(SpendingState)
    builder.add_node("aggregate", _node_aggregate)
    builder.add_node("detect_anomalies", _node_detect_anomalies)
    builder.add_node("ai_insights", _node_ai_insights)
    builder.add_node("finalize", _node_finalize)
    builder.set_entry_point("aggregate")
    builder.add_edge("aggregate", "detect_anomalies")
    builder.add_edge("detect_anomalies", "ai_insights")
    builder.add_edge("ai_insights", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()


_workflow = None


def _get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = _build_workflow()
    return _workflow


def run(initial_state: Dict) -> Dict:
    try:
        return _get_workflow().invoke(initial_state)
    except Exception as exc:
        logger.error("Spending workflow failed: %s", exc)
        return {**initial_state, "final_insights": [], "error": str(exc)}
