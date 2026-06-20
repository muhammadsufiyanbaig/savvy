"""LangGraph workflow: profile analysis → AI generation → fallback merge."""

import logging
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


class RecommendationState(TypedDict):
    user_id: int
    recommendation_types: List[str]
    context: Dict[str, Any]
    # computed
    user_profile: Dict[str, Any]
    ai_recommendations: List[Dict]
    fallback_recommendations: List[Dict]
    final: List[Dict]
    error: Optional[str]


def _node_user_profile(state: RecommendationState) -> Dict:
    from app.integrations import chroma_client
    profile = chroma_client.get_user_investment_context(state["user_id"])
    return {"user_profile": profile or {}}


def _node_ai_generate(state: RecommendationState) -> Dict:
    from app.services import recommendation_service
    recs = recommendation_service.ai_generate_recommendations(
        state["user_id"],
        state["recommendation_types"],
        state["context"],
        state.get("user_profile", {}),
    )
    return {"ai_recommendations": recs}


def _node_fallback(state: RecommendationState) -> Dict:
    from app.services import recommendation_service
    fallback = recommendation_service.rule_based_recommendations(
        state["recommendation_types"],
        state["context"],
    )
    return {"fallback_recommendations": fallback}


def _node_merge(state: RecommendationState) -> Dict:
    ai = state.get("ai_recommendations", [])
    fb = state.get("fallback_recommendations", [])
    # Prefer AI recommendations; pad with fallback if AI returned too few
    combined = ai if ai else fb
    if ai and len(ai) < 2:
        combined = ai + fb[:max(0, 3 - len(ai))]
    return {"final": combined[:5]}


def _build_workflow():
    builder = StateGraph(RecommendationState)
    builder.add_node("user_profile", _node_user_profile)
    builder.add_node("ai_generate", _node_ai_generate)
    builder.add_node("fallback", _node_fallback)
    builder.add_node("merge", _node_merge)
    builder.set_entry_point("user_profile")
    builder.add_edge("user_profile", "ai_generate")
    builder.add_edge("ai_generate", "fallback")
    builder.add_edge("fallback", "merge")
    builder.add_edge("merge", END)
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
        logger.error("Recommendation workflow failed: %s", exc)
        return {**initial_state, "final": [], "error": str(exc)}
