"""LangGraph workflow: fetch context → market data → generate → filter → finalize."""

import logging
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


# ── State schema ──────────────────────────────────────────────────────────────

class InvestmentState(TypedDict):
    user_id: int
    available_amount: float
    risk_tolerance: str
    time_horizon: str
    country: str
    city: Optional[str]
    shariah_required: bool
    preferred_sectors: List[str]
    # computed by nodes
    user_context: Dict[str, Any]
    market_summary: Dict[str, Any]
    candidate_investments: List[Dict]
    filtered_investments: List[Dict]
    final_recommendations: List[Dict]
    error: Optional[str]


# ── Node functions (sync) ─────────────────────────────────────────────────────

def _node_user_context(state: InvestmentState) -> Dict:
    from app.integrations import chroma_client
    context = chroma_client.get_user_investment_context(state["user_id"])
    return {"user_context": context or {}}


def _node_market_data(state: InvestmentState) -> Dict:
    from app.integrations import market_data
    summary = market_data.get_market_summary(state.get("country", "USA"))
    return {"market_summary": summary or {}}


def _node_generate_candidates(state: InvestmentState) -> Dict:
    from app.services import investment_service
    candidates = investment_service.generate_investment_candidates(state)
    return {"candidate_investments": candidates}


def _node_apply_shariah(state: InvestmentState) -> Dict:
    candidates = state.get("candidate_investments", [])
    if not state.get("shariah_required"):
        return {"filtered_investments": candidates}

    from app.services.shariah_checker import ShariahChecker
    filtered = ShariahChecker().filter_compliant(candidates)
    # If filter removed everything, return all (best effort)
    return {"filtered_investments": filtered if filtered else candidates}


def _node_finalize(state: InvestmentState) -> Dict:
    pool = state.get("filtered_investments") or state.get("candidate_investments", [])
    pool_sorted = sorted(pool, key=lambda x: x.get("confidence_score", 0), reverse=True)
    final = pool_sorted[:5]
    return {"final_recommendations": final}


# ── Build workflow ─────────────────────────────────────────────────────────────

def _build_workflow() -> Any:
    builder: StateGraph = StateGraph(InvestmentState)

    builder.add_node("user_context", _node_user_context)
    builder.add_node("market_data", _node_market_data)
    builder.add_node("generate_candidates", _node_generate_candidates)
    builder.add_node("apply_shariah", _node_apply_shariah)
    builder.add_node("finalize", _node_finalize)

    builder.set_entry_point("user_context")
    builder.add_edge("user_context", "market_data")
    builder.add_edge("market_data", "generate_candidates")
    builder.add_edge("generate_candidates", "apply_shariah")
    builder.add_edge("apply_shariah", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()


_workflow = None


def _get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = _build_workflow()
    return _workflow


def run(initial_state: Dict) -> Dict:
    """Execute the investment workflow. Returns state dict; never raises."""
    try:
        return _get_workflow().invoke(initial_state)
    except Exception as exc:
        logger.error("Investment workflow failed: %s", exc)
        return {
            **initial_state,
            "user_context": {},
            "market_summary": {},
            "candidate_investments": [],
            "filtered_investments": [],
            "final_recommendations": [],
            "error": str(exc),
        }
