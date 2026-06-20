"""Categorisation unit tests — rule-based, confidence scoring, vector fallback."""

import pytest


# ── Rule categoriser ──────────────────────────────────────────────────────────

class TestRuleCategorizer:
    def test_starbucks(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("STARBUCKS COFFEE #1234")
        assert result["category"] == "Food & Dining"
        assert result["subcategory"] == "Coffee Shops"
        assert "coffee" in result["tags"]

    def test_mcdonalds(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("MCDONALD'S #12345 NEW YORK NY")
        assert result["category"] == "Food & Dining"
        assert result["subcategory"] == "Fast Food"

    def test_uber(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("UBER TRIP NYCABCDEF")
        assert result["category"] == "Transportation"
        assert result["subcategory"] == "Ride Sharing"

    def test_shell_gas(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("SHELL OIL 12345678 HOUSTON TX")
        assert result["category"] == "Transportation"
        assert result["subcategory"] == "Gas & Fuel"

    def test_amazon(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("AMAZON.COM*AB123456 AMZN.COM/BILL")
        assert result["category"] == "Shopping"
        assert result["subcategory"] == "Online Shopping"

    def test_netflix(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("NETFLIX.COM MONTHLY SUB")
        assert result["category"] == "Entertainment"
        assert result["subcategory"] == "Streaming"

    def test_verizon(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("VERIZON WIRELESS MONTHLY BILL")
        assert result["category"] == "Bills & Utilities"

    def test_payroll(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("DIRECT DEPOSIT PAYROLL ACME CORP")
        assert result["category"] == "Income"
        assert result["subcategory"] == "Salary"

    def test_venmo(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("VENMO PAYMENT TO JOHN")
        assert result["category"] == "Transfer"

    def test_cvs_pharmacy(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("CVS PHARMACY #12345")
        assert result["category"] == "Healthcare"
        assert result["subcategory"] == "Pharmacy"

    def test_planet_fitness(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("PLANET FITNESS MONTHLY")
        assert result["category"] == "Personal Care"

    def test_hilton_hotel(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("HILTON GARDEN INN CHICAGO")
        assert result["category"] == "Travel"
        assert result["subcategory"] == "Hotels"

    def test_delta_flight(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("DELTA AIR LINES TICKET NYC-LAX")
        assert result["category"] == "Travel"
        assert result["subcategory"] == "Flights"

    def test_unknown_merchant(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("XKCD9999 UNKNOWN VENDOR 0000")
        assert result["category"] == "Other"
        assert result["confidence_score"] < 0.5

    def test_category_hint_used_for_unknown(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("SOME UNKNOWN PLACE", category_hint="Healthcare")
        assert result["category"] == "Healthcare"
        assert result["categorization_method"] == "ai_hint"

    def test_confidence_score_range(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("STARBUCKS COFFEE")
        assert 0.0 <= result["confidence_score"] <= 1.0

    def test_empty_description(self):
        from app.categorization.rule_categorizer import categorise
        result = categorise("")
        assert result["category"] == "Other"
        assert result["confidence_score"] >= 0


# ── Confidence scorer ─────────────────────────────────────────────────────────

class TestConfidenceScorer:
    def test_high_level(self):
        from app.categorization.confidence_scorer import score_level
        assert score_level(0.95) == "high"
        assert score_level(0.85) == "high"

    def test_medium_level(self):
        from app.categorization.confidence_scorer import score_level
        assert score_level(0.80) == "medium"
        assert score_level(0.65) == "medium"

    def test_low_level(self):
        from app.categorization.confidence_scorer import score_level
        assert score_level(0.50) == "low"
        assert score_level(0.0) == "low"

    def test_combine_caps_at_one(self):
        from app.categorization.confidence_scorer import combine
        result = combine(1.0, 1.0, "vector")
        assert result <= 1.0

    def test_combine_floor_at_zero(self):
        from app.categorization.confidence_scorer import combine
        result = combine(0.0, 0.0, "rule")
        assert result >= 0.0

    def test_combine_vector_higher_than_rule(self):
        from app.categorization.confidence_scorer import combine
        vector_score = combine(0.8, 0.8, "vector")
        rule_score = combine(0.8, 0.8, "rule")
        assert vector_score > rule_score

    def test_count_by_level(self):
        from app.categorization.confidence_scorer import count_by_level
        scores = [0.90, 0.88, 0.72, 0.40, 0.30]
        counts = count_by_level(scores)
        assert counts["high"] == 2
        assert counts["medium"] == 1
        assert counts["low"] == 2

    def test_count_by_level_empty(self):
        from app.categorization.confidence_scorer import count_by_level
        counts = count_by_level([])
        assert counts == {"high": 0, "medium": 0, "low": 0}


# ── Vector categoriser (no ChromaDB) ─────────────────────────────────────────

class TestVectorCategorizer:
    def test_returns_none_when_no_client(self):
        from app.categorization.vector_categorizer import categorise
        result = categorise("STARBUCKS COFFEE", chroma_client=None)
        assert result is None

    def test_add_pattern_false_when_no_client(self):
        from app.categorization.vector_categorizer import add_pattern
        result = add_pattern("STARBUCKS", "Food & Dining", "Coffee", chroma_client=None)
        assert result is False

    def test_categorise_with_mock_chroma(self):
        from app.categorization.vector_categorizer import categorise

        mock_chroma = _make_mock_chroma(
            query_result={
                "ids": [["id1", "id2", "id3"]],
                "metadatas": [
                    [
                        {"category": "Food & Dining", "subcategory": "Coffee Shops"},
                        {"category": "Food & Dining", "subcategory": "Coffee Shops"},
                        {"category": "Other", "subcategory": ""},
                    ]
                ],
                "documents": [["STARBUCKS #111", "STARBUCKS #222", "CAFE LATTE"]],
                "distances": [[0.05, 0.08, 0.40]],
            }
        )

        result = categorise("STARBUCKS COFFEE", chroma_client=mock_chroma)
        assert result is not None
        assert result["category"] == "Food & Dining"
        assert result["confidence_score"] > 0

    def test_categorise_returns_none_on_empty_results(self):
        from app.categorization.vector_categorizer import categorise

        mock_chroma = _make_mock_chroma(
            query_result={"ids": [[]], "metadatas": [[]], "documents": [[]], "distances": [[]]}
        )

        result = categorise("RANDOM MERCHANT", chroma_client=mock_chroma)
        assert result is None

    def test_add_pattern_with_mock_chroma(self):
        from app.categorization.vector_categorizer import add_pattern

        mock_chroma = _make_mock_chroma()
        result = add_pattern("STARBUCKS", "Food & Dining", "Coffee Shops", chroma_client=mock_chroma)
        assert result is True


def _make_mock_chroma(query_result=None):
    """Helper: build a minimal mock ChromaDB client."""
    from unittest.mock import MagicMock

    mock_collection = MagicMock()
    if query_result:
        mock_collection.query.return_value = query_result
    else:
        mock_collection.query.return_value = {
            "ids": [[]], "metadatas": [[]], "documents": [[]], "distances": [[]]
        }
    mock_collection.upsert.return_value = None

    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    return mock_client


# ── Categorisation pipeline (rule → vector fallback) ─────────────────────────

class TestCategorizationPipeline:
    """Tests that processor integrates vector → rule fallback correctly."""

    def test_vector_result_takes_priority(self):
        from app.categorization import rule_categorizer, vector_categorizer

        mock_chroma = _make_mock_chroma(
            query_result={
                "ids": [["id1"]],
                "metadatas": [[{"category": "Healthcare", "subcategory": "Medical"}]],
                "documents": [["DOCTOR VISIT"]],
                "distances": [[0.1]],
            }
        )

        vec_result = vector_categorizer.categorise("UNUSUAL CLINIC VISIT", mock_chroma)
        assert vec_result is not None
        assert vec_result["category"] == "Healthcare"
        assert vec_result["categorization_method"] == "vector"

    def test_rule_fallback_when_vector_none(self):
        from app.categorization import rule_categorizer

        result = rule_categorizer.categorise("NETFLIX SUBSCRIPTION")
        assert result["category"] == "Entertainment"

    def test_full_pipeline_with_transactions(self, sample_transactions):
        """Simulate what statement_processor does for each transaction."""
        from app.categorization import confidence_scorer, rule_categorizer, vector_categorizer

        for raw in sample_transactions:
            # Vector returns None (no chroma)
            cat_result = vector_categorizer.categorise(raw["description"], chroma_client=None)
            if cat_result is None:
                cat_result = rule_categorizer.categorise(
                    raw["description"],
                    raw["amount"],
                    raw.get("category_hint"),
                )

            final = confidence_scorer.combine(
                cat_result.get("confidence_score", 0.5),
                1.0,
                cat_result.get("categorization_method", "rule"),
            )
            assert 0.0 <= final <= 1.0
            assert cat_result["category"]  # not empty
