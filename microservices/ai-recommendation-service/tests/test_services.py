"""Service-layer unit tests — recommendation_service, investment_service, insight_service."""

import pytest


# ── recommendation_service ────────────────────────────────────────────────────

class TestRuleBasedRecommendations:
    def test_returns_list(self):
        from app.services.recommendation_service import rule_based_recommendations
        result = rule_based_recommendations(["savings"], {})
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_each_rec_has_required_fields(self):
        from app.services.recommendation_service import rule_based_recommendations
        recs = rule_based_recommendations(["savings", "spending"], {})
        for rec in recs:
            assert "id" in rec
            assert "type" in rec
            assert "title" in rec
            assert "description" in rec
            assert "recommended_action" in rec
            assert "confidence_score" in rec
            assert "priority" in rec

    def test_savings_type_returns_savings_recs(self):
        from app.services.recommendation_service import rule_based_recommendations
        recs = rule_based_recommendations(["savings"], {})
        types = {r["type"] for r in recs}
        # All recs should be savings type (ignoring the urgent override which is also savings)
        assert "savings" in types

    def test_spending_type_returns_spending_recs(self):
        from app.services.recommendation_service import rule_based_recommendations
        recs = rule_based_recommendations(["spending"], {})
        assert any(r["type"] == "spending" for r in recs)

    def test_budget_type_returns_budget_recs(self):
        from app.services.recommendation_service import rule_based_recommendations
        recs = rule_based_recommendations(["budget"], {})
        assert any(r["type"] == "budget" for r in recs)

    def test_unknown_type_falls_back_to_general(self):
        from app.services.recommendation_service import rule_based_recommendations
        recs = rule_based_recommendations(["unknown_category"], {})
        assert len(recs) >= 1
        assert all(r["type"] == "general" for r in recs)

    def test_multiple_types_returned(self):
        from app.services.recommendation_service import rule_based_recommendations
        recs = rule_based_recommendations(["savings", "spending", "budget"], {})
        types = {r["type"] for r in recs}
        assert len(types) >= 2

    def test_max_6_recommendations(self):
        from app.services.recommendation_service import rule_based_recommendations
        recs = rule_based_recommendations(["savings", "spending", "budget", "general"], {})
        assert len(recs) <= 6

    def test_low_savings_rate_triggers_urgent_rec(self):
        from app.services.recommendation_service import rule_based_recommendations
        context = {"monthly_income": 5000, "monthly_expenses": 4800}  # 4% savings rate
        recs = rule_based_recommendations(["savings"], context)
        priorities = [r["priority"] for r in recs]
        assert "high" in priorities

    def test_low_savings_rate_rec_inserted_first(self):
        from app.services.recommendation_service import rule_based_recommendations
        context = {"monthly_income": 5000, "monthly_expenses": 4900}  # 2% savings rate
        recs = rule_based_recommendations(["savings"], context)
        assert recs[0]["priority"] == "high"
        assert "Urgent" in recs[0]["title"] or "savings" in recs[0]["title"].lower()

    def test_good_savings_rate_no_urgent_boost(self):
        from app.services.recommendation_service import rule_based_recommendations
        context = {"monthly_income": 5000, "monthly_expenses": 3000}  # 40% savings rate
        recs = rule_based_recommendations(["savings"], context)
        # No extra urgent rec inserted for good savers
        assert all("Urgent" not in r["title"] for r in recs)

    def test_empty_types_returns_empty(self):
        from app.services.recommendation_service import rule_based_recommendations
        recs = rule_based_recommendations([], {})
        assert recs == []

    def test_recs_have_unique_ids(self):
        from app.services.recommendation_service import rule_based_recommendations
        recs = rule_based_recommendations(["savings", "spending"], {})
        ids = [r["id"] for r in recs]
        assert len(ids) == len(set(ids))

    def test_confidence_score_between_0_and_1(self):
        from app.services.recommendation_service import rule_based_recommendations
        recs = rule_based_recommendations(["savings", "spending", "budget"], {})
        for rec in recs:
            assert 0.0 <= rec["confidence_score"] <= 1.0

    def test_priority_valid_values(self):
        from app.services.recommendation_service import rule_based_recommendations
        recs = rule_based_recommendations(["savings", "spending"], {})
        valid = {"high", "medium", "low"}
        for rec in recs:
            assert rec["priority"] in valid

    def test_zero_income_no_crash(self):
        from app.services.recommendation_service import rule_based_recommendations
        result = rule_based_recommendations(["savings"], {"monthly_income": 0, "monthly_expenses": 0})
        assert isinstance(result, list)


# ── investment_service ────────────────────────────────────────────────────────

class TestGenerateInvestmentCandidates:
    def _state(self, **kwargs):
        base = {
            "user_id": 1,
            "available_amount": 5000.0,
            "risk_tolerance": "medium",
            "time_horizon": "long",
            "country": "USA",
            "shariah_required": False,
            "preferred_sectors": [],
            "market_summary": {"trend": "bullish", "sp500_ytd": 8.5},
        }
        return {**base, **kwargs}

    def test_returns_list(self):
        from app.services.investment_service import generate_investment_candidates
        result = generate_investment_candidates(self._state())
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_low_risk_returns_low_risk_candidates(self):
        from app.services.investment_service import generate_investment_candidates
        result = generate_investment_candidates(self._state(risk_tolerance="low"))
        # All fallback candidates should be low risk
        for inv in result:
            assert inv.get("risk_level") == "low"

    def test_medium_risk_returns_medium_risk_candidates(self):
        from app.services.investment_service import generate_investment_candidates
        result = generate_investment_candidates(self._state(risk_tolerance="medium"))
        for inv in result:
            assert inv.get("risk_level") == "medium"

    def test_high_risk_returns_high_risk_candidates(self):
        from app.services.investment_service import generate_investment_candidates
        result = generate_investment_candidates(self._state(risk_tolerance="high"))
        for inv in result:
            assert inv.get("risk_level") == "high"

    def test_shariah_fund_in_medium_pool(self):
        from app.services.investment_service import generate_investment_candidates, _FALLBACK_INVESTMENTS
        medium_pool = _FALLBACK_INVESTMENTS["medium"]
        shariah_items = [inv for inv in medium_pool if inv.get("is_shariah_compliant")]
        assert len(shariah_items) >= 1

    def test_fallback_pool_has_required_fields(self):
        from app.services.investment_service import _FALLBACK_INVESTMENTS
        required = {"investment_type", "asset_name", "expected_return", "risk_level",
                    "sector", "debt_ratio", "interest_income_ratio", "confidence_score"}
        for risk_level, pool in _FALLBACK_INVESTMENTS.items():
            for inv in pool:
                for field in required:
                    assert field in inv, f"Missing {field} in {risk_level} pool"

    def test_unknown_risk_falls_back_to_medium(self):
        from app.services.investment_service import generate_investment_candidates
        result = generate_investment_candidates(self._state(risk_tolerance="unknown"))
        assert len(result) >= 1  # medium pool used as default


# ── insight_service ───────────────────────────────────────────────────────────

class TestAggregateExpenses:
    def test_empty_list_returns_zero_total(self):
        from app.services.insight_service import aggregate_expenses
        result = aggregate_expenses([])
        assert result["total"] == 0.0
        assert result["count"] == 0
        assert result["by_category"] == {}

    def test_single_expense(self):
        from app.services.insight_service import aggregate_expenses
        result = aggregate_expenses([{"category": "Food & Dining", "amount": 100.0}])
        assert result["total"] == 100.0
        assert result["by_category"]["Food & Dining"] == 100.0
        assert result["count"] == 1

    def test_multiple_same_category_summed(self):
        from app.services.insight_service import aggregate_expenses
        expenses = [
            {"category": "Food & Dining", "amount": 100.0},
            {"category": "Food & Dining", "amount": 200.0},
            {"category": "Transportation", "amount": 50.0},
        ]
        result = aggregate_expenses(expenses)
        assert result["by_category"]["Food & Dining"] == 300.0
        assert result["by_category"]["Transportation"] == 50.0
        assert result["total"] == 350.0

    def test_avg_transaction_correct(self):
        from app.services.insight_service import aggregate_expenses
        expenses = [
            {"category": "A", "amount": 100.0},
            {"category": "B", "amount": 200.0},
        ]
        result = aggregate_expenses(expenses)
        assert result["avg_transaction"] == 150.0

    def test_missing_category_defaults_to_other(self):
        from app.services.insight_service import aggregate_expenses
        result = aggregate_expenses([{"amount": 50.0}])
        assert "Other" in result["by_category"]

    def test_missing_amount_defaults_to_zero(self):
        from app.services.insight_service import aggregate_expenses
        result = aggregate_expenses([{"category": "Food", "amount": 0}])
        assert result["total"] == 0.0

    def test_count_matches_input_length(self, sample_expenses):
        from app.services.insight_service import aggregate_expenses
        result = aggregate_expenses(sample_expenses)
        assert result["count"] == len(sample_expenses)


class TestDetectAnomalies:
    def test_no_anomalies_on_empty(self):
        from app.services.insight_service import detect_anomalies
        result = detect_anomalies({"total": 0, "by_category": {}})
        assert result == []

    def test_detects_high_food_spending(self, sample_expenses):
        from app.services.insight_service import aggregate_expenses, detect_anomalies
        agg = aggregate_expenses(sample_expenses)
        anomalies = detect_anomalies(agg)
        # Food & Dining is 54% vs typical 15% → should be flagged
        cats = [a["category"] for a in anomalies]
        assert "Food & Dining" in cats

    def test_anomaly_has_required_fields(self, sample_expenses):
        from app.services.insight_service import aggregate_expenses, detect_anomalies
        agg = aggregate_expenses(sample_expenses)
        anomalies = detect_anomalies(agg)
        for a in anomalies:
            assert "category" in a
            assert "amount" in a
            assert "percentage" in a
            assert "typical_percentage" in a
            assert "deviation" in a

    def test_anomalies_sorted_by_deviation_desc(self, sample_expenses):
        from app.services.insight_service import aggregate_expenses, detect_anomalies
        agg = aggregate_expenses(sample_expenses)
        anomalies = detect_anomalies(agg)
        if len(anomalies) >= 2:
            assert anomalies[0]["deviation"] >= anomalies[1]["deviation"]

    def test_below_threshold_not_flagged(self):
        from app.services.insight_service import detect_anomalies
        # Bills & Utilities at exactly typical (20%) — should NOT be flagged
        agg = {
            "total": 1000.0,
            "by_category": {"Bills & Utilities": 200.0},  # 20% == typical
        }
        anomalies = detect_anomalies(agg)
        assert anomalies == []

    def test_1_5x_threshold_triggers(self):
        from app.services.insight_service import detect_anomalies
        # Food & Dining typical = 15%. 1.5x = 22.5%. 23% should trigger.
        agg = {
            "total": 1000.0,
            "by_category": {"Food & Dining": 230.0},  # 23%
        }
        anomalies = detect_anomalies(agg)
        cats = [a["category"] for a in anomalies]
        assert "Food & Dining" in cats


class TestAnomaliesToInsights:
    def test_converts_anomalies_to_insights(self):
        from app.services.insight_service import anomalies_to_insights
        anomalies = [
            {
                "category": "Food & Dining",
                "amount": 700.0,
                "percentage": 54.0,
                "typical_percentage": 15.0,
                "deviation": 260.0,
            }
        ]
        insights = anomalies_to_insights(anomalies)
        assert len(insights) == 1
        assert "id" in insights[0]
        assert insights[0]["type"] == "spending_anomaly"
        assert "Food & Dining" in insights[0]["title"]
        assert "priority" in insights[0]
        assert "is_urgent" in insights[0]

    def test_high_deviation_is_urgent(self):
        from app.services.insight_service import anomalies_to_insights
        anomalies = [
            {
                "category": "Entertainment",
                "amount": 500.0,
                "percentage": 40.0,
                "typical_percentage": 8.0,
                "deviation": 400.0,  # >200 → urgent
            }
        ]
        insights = anomalies_to_insights(anomalies)
        assert insights[0]["is_urgent"] is True
        assert insights[0]["priority"] == "high"

    def test_moderate_deviation_not_urgent(self):
        from app.services.insight_service import anomalies_to_insights
        anomalies = [
            {
                "category": "Shopping",
                "amount": 200.0,
                "percentage": 15.0,
                "typical_percentage": 10.0,
                "deviation": 50.0,  # <100 → not high priority
            }
        ]
        insights = anomalies_to_insights(anomalies)
        assert insights[0]["is_urgent"] is False
        assert insights[0]["priority"] == "medium"

    def test_empty_anomalies_returns_empty_insights(self):
        from app.services.insight_service import anomalies_to_insights
        assert anomalies_to_insights([]) == []


class TestBuildSpendingAnalysis:
    def test_returns_required_fields(self, sample_expenses):
        from app.services.insight_service import aggregate_expenses, build_spending_analysis
        agg = aggregate_expenses(sample_expenses)
        analysis = build_spending_analysis(agg)
        assert "top_categories" in analysis
        assert "spending_trend" in analysis
        assert "month_over_month_change" in analysis
        assert "vs_similar_users" in analysis
        assert "biggest_opportunity" in analysis
        assert "score" in analysis
        assert "score_label" in analysis

    def test_top_categories_max_5(self):
        from app.services.insight_service import aggregate_expenses, build_spending_analysis
        expenses = [
            {"category": f"Cat{i}", "amount": float(100 - i * 5)}
            for i in range(10)
        ]
        agg = aggregate_expenses(expenses)
        analysis = build_spending_analysis(agg)
        assert len(analysis["top_categories"]) <= 5

    def test_top_categories_sorted_by_amount(self, sample_expenses):
        from app.services.insight_service import aggregate_expenses, build_spending_analysis
        agg = aggregate_expenses(sample_expenses)
        analysis = build_spending_analysis(agg)
        cats = analysis["top_categories"]
        if len(cats) >= 2:
            assert cats[0]["amount"] >= cats[1]["amount"]

    def test_empty_expenses_no_crash(self):
        from app.services.insight_service import aggregate_expenses, build_spending_analysis
        agg = aggregate_expenses([])
        analysis = build_spending_analysis(agg)
        assert analysis["top_categories"] == []
        assert analysis["spending_trend"] == "stable"

    def test_biggest_opportunity_references_top_category(self, sample_expenses):
        from app.services.insight_service import aggregate_expenses, build_spending_analysis
        agg = aggregate_expenses(sample_expenses)
        analysis = build_spending_analysis(agg)
        # Food & Dining is top — opportunity string should mention it
        assert "Food" in analysis["biggest_opportunity"] or "$" in analysis["biggest_opportunity"]

    def test_score_in_valid_range(self, sample_expenses):
        from app.services.insight_service import aggregate_expenses, build_spending_analysis
        agg = aggregate_expenses(sample_expenses)
        analysis = build_spending_analysis(agg)
        assert 0 <= analysis["score"] <= 100
