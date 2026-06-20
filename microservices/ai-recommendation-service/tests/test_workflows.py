"""LangGraph workflow tests — all external calls mocked."""

import json
from unittest.mock import MagicMock, patch

import pytest


# ── Investment workflow ────────────────────────────────────────────────────────

class TestInvestmentWorkflow:
    def _make_state(self, **overrides):
        base = {
            "user_id": 1,
            "available_amount": 5000.0,
            "risk_tolerance": "medium",
            "time_horizon": "long",
            "country": "USA",
            "city": None,
            "shariah_required": False,
            "preferred_sectors": [],
            "user_context": {},
            "market_summary": {},
            "candidate_investments": [],
            "filtered_investments": [],
            "final_recommendations": [],
            "error": None,
        }
        return {**base, **overrides}

    def test_workflow_returns_investments(self):
        from app.workflows import investment_workflow
        state = self._make_state()
        result = investment_workflow.run(state)
        assert "final_recommendations" in result
        assert isinstance(result["final_recommendations"], list)
        assert len(result["final_recommendations"]) > 0

    def test_workflow_shariah_filter_applied(self):
        from app.workflows import investment_workflow
        state = self._make_state(shariah_required=True)
        result = investment_workflow.run(state)
        recs = result["final_recommendations"]
        # All returned should be Shariah compliant
        for rec in recs:
            assert rec.get("is_shariah_compliant") is True

    def test_workflow_handles_ai_failure_gracefully(self):
        from app.workflows import investment_workflow
        # Claude returns None (already mocked in conftest), workflow should not raise
        state = self._make_state()
        result = investment_workflow.run(state)
        assert "final_recommendations" in result
        assert result.get("error") is None or isinstance(result.get("error"), str)

    def test_workflow_node_market_data(self):
        from app.workflows.investment_workflow import _node_market_data
        result = _node_market_data(
            {
                "country": "USA",
                "user_id": 1,
                "available_amount": 1000,
                "risk_tolerance": "medium",
                "time_horizon": "long",
                "shariah_required": False,
                "preferred_sectors": [],
                "city": None,
            }
        )
        assert "market_summary" in result
        assert isinstance(result["market_summary"], dict)

    def test_workflow_node_finalize_sorts_by_confidence(self):
        from app.workflows.investment_workflow import _node_finalize
        candidates = [
            {"investment_type": "stocks", "confidence_score": 0.6},
            {"investment_type": "etf", "confidence_score": 0.9},
            {"investment_type": "bonds", "confidence_score": 0.75},
        ]
        result = _node_finalize(
            {
                "candidate_investments": candidates,
                "filtered_investments": candidates,
                "shariah_required": False,
            }
        )
        final = result["final_recommendations"]
        # Top result should have highest confidence
        assert final[0]["confidence_score"] == 0.9

    def test_workflow_max_5_recommendations(self):
        from app.workflows.investment_workflow import _node_finalize
        pool = [{"investment_type": "x", "confidence_score": 0.5} for _ in range(10)]
        result = _node_finalize({"filtered_investments": pool, "candidate_investments": pool})
        assert len(result["final_recommendations"]) <= 5

    def test_workflow_ai_candidates_used_when_available(self):
        from app.workflows import investment_workflow
        canned_candidates = json.dumps([
            {
                "investment_type": "stocks",
                "asset_name": "Test Corp",
                "asset_symbol": "TC",
                "expected_return": 15.0,
                "risk_level": "medium",
                "sector": "technology",
                "is_shariah_compliant": False,
                "debt_ratio": 0.1,
                "interest_income_ratio": 0.01,
                "analysis": "Test analysis.",
                "pros": ["pro"],
                "cons": ["con"],
                "confidence_score": 0.88,
            }
        ])
        with patch("app.integrations.claude_client.call_claude", return_value=canned_candidates):
            state = self._make_state()
            result = investment_workflow.run(state)
        # Should have at least the AI candidate
        assert len(result["final_recommendations"]) >= 1


# ── Recommendation workflow ────────────────────────────────────────────────────

class TestRecommendationWorkflow:
    def test_workflow_returns_recommendations(self):
        from app.workflows import recommendation_workflow
        result = recommendation_workflow.run(
            {
                "user_id": 1,
                "recommendation_types": ["savings", "spending"],
                "context": {"monthly_income": 5000, "monthly_expenses": 4000},
                "user_profile": {},
                "ai_recommendations": [],
                "fallback_recommendations": [],
                "final": [],
                "error": None,
            }
        )
        assert "final" in result
        assert len(result["final"]) >= 1

    def test_workflow_uses_ai_when_available(self):
        canned = json.dumps([
            {
                "type": "savings",
                "title": "AI Savings Tip",
                "description": "Desc",
                "recommended_action": "Action",
                "expected_benefit": "Benefit",
                "risk_level": "low",
                "confidence_score": 0.92,
                "priority": "high",
            }
        ])
        from app.workflows import recommendation_workflow
        with patch("app.integrations.claude_client.call_claude", return_value=canned):
            result = recommendation_workflow.run(
                {
                    "user_id": 1,
                    "recommendation_types": ["savings"],
                    "context": {},
                    "user_profile": {},
                    "ai_recommendations": [],
                    "fallback_recommendations": [],
                    "final": [],
                    "error": None,
                }
            )
        # AI recommendations should appear in final
        ai_recs = [r for r in result["final"] if r.get("title") == "AI Savings Tip"]
        assert len(ai_recs) >= 1

    def test_workflow_fallback_when_ai_fails(self):
        from app.workflows import recommendation_workflow
        # Claude mocked to return None (conftest)
        result = recommendation_workflow.run(
            {
                "user_id": 1,
                "recommendation_types": ["budget"],
                "context": {},
                "user_profile": {},
                "ai_recommendations": [],
                "fallback_recommendations": [],
                "final": [],
                "error": None,
            }
        )
        assert len(result["final"]) >= 1
        assert all("title" in r for r in result["final"])


# ── Spending workflow ──────────────────────────────────────────────────────────

class TestSpendingWorkflow:
    def test_workflow_aggregates_expenses(self, sample_expenses):
        from app.workflows import spending_workflow
        result = spending_workflow.run(
            {
                "user_id": 1,
                "period": "monthly",
                "expenses": sample_expenses,
                "aggregated": {},
                "anomalies": [],
                "ai_insights": [],
                "final_insights": [],
                "error": None,
            }
        )
        assert "aggregated" in result
        assert result["aggregated"]["total"] > 0
        assert "Food & Dining" in result["aggregated"]["by_category"]

    def test_workflow_detects_anomalies(self, sample_expenses):
        from app.workflows import spending_workflow
        result = spending_workflow.run(
            {
                "user_id": 1,
                "period": "monthly",
                "expenses": sample_expenses,
                "aggregated": {},
                "anomalies": [],
                "ai_insights": [],
                "final_insights": [],
                "error": None,
            }
        )
        # Food & Dining is 54% of total → above typical 15% → should be flagged
        assert len(result.get("anomalies", [])) >= 1

    def test_workflow_empty_expenses(self):
        from app.workflows import spending_workflow
        result = spending_workflow.run(
            {
                "user_id": 1,
                "period": "monthly",
                "expenses": [],
                "aggregated": {},
                "anomalies": [],
                "ai_insights": [],
                "final_insights": [],
                "error": None,
            }
        )
        assert result["aggregated"]["total"] == 0.0
        assert result["final_insights"] == []
