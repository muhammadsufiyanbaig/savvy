"""AI extraction unit tests — all AI calls mocked."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.ai.transaction_extractor import TransactionExtractor


# ── TransactionExtractor ──────────────────────────────────────────────────────

class TestTransactionExtractor:
    """Tests use mocked Claude/OpenAI responses."""

    _SAMPLE_AI_JSON = json.dumps([
        {
            "date": "2026-02-01",
            "description": "STARBUCKS COFFEE #1234",
            "amount": 5.75,
            "transaction_type": "debit",
            "merchant": "Starbucks",
            "category_hint": "Food & Dining",
        },
        {
            "date": "2026-02-02",
            "description": "AMAZON.COM*XY1234",
            "amount": 49.99,
            "transaction_type": "debit",
            "merchant": "Amazon",
            "category_hint": "Shopping",
        },
    ])

    def test_extract_from_structured_csv_data(self, sample_transactions):
        """If parser already produced structured rows, extractor uses them directly."""
        extractor = TransactionExtractor()
        parsed_data = {"text": "", "transactions": sample_transactions}
        result = extractor.extract(parsed_data)

        assert len(result) == 3
        starbucks = next(t for t in result if "STARBUCKS" in t["description"])
        assert starbucks["amount"] == 5.75
        assert starbucks["transaction_type"] == "debit"

    def test_extract_via_claude(self):
        """When only text is available, calls Claude and parses JSON."""
        extractor = TransactionExtractor()
        parsed_data = {
            "text": "02/01/2026 STARBUCKS 5.75\n02/02/2026 AMAZON 49.99",
            "transactions": [],
        }

        with patch("app.ai.claude_client.call_claude", return_value=self._SAMPLE_AI_JSON):
            result = extractor.extract(parsed_data)

        assert len(result) == 2
        assert result[0]["merchant"] == "Starbucks"
        assert result[1]["amount"] == 49.99

    def test_extract_falls_back_to_openai_when_claude_none(self):
        """If Claude returns None, tries OpenAI."""
        extractor = TransactionExtractor()
        parsed_data = {"text": "some bank statement text", "transactions": []}

        with patch("app.ai.claude_client.call_claude", return_value=None), \
             patch("app.ai.openai_client.call_openai", return_value=self._SAMPLE_AI_JSON):
            result = extractor.extract(parsed_data)

        assert len(result) == 2

    def test_extract_returns_empty_when_both_ai_fail(self):
        """If both Claude and OpenAI fail, returns empty list."""
        extractor = TransactionExtractor()
        parsed_data = {"text": "some statement text", "transactions": []}

        with patch("app.ai.claude_client.call_claude", return_value=None), \
             patch("app.ai.openai_client.call_openai", return_value=None):
            result = extractor.extract(parsed_data)

        assert result == []

    def test_extract_handles_invalid_json(self):
        """If AI returns non-JSON, returns empty list gracefully."""
        extractor = TransactionExtractor()
        parsed_data = {"text": "statement text", "transactions": []}

        with patch("app.ai.claude_client.call_claude", return_value="NOT JSON AT ALL"):
            result = extractor.extract(parsed_data)

        assert result == []

    def test_extract_normalises_negative_amount(self):
        extractor = TransactionExtractor()
        row = {"date": "2026-02-01", "description": "DEBIT", "amount": -25.50, "transaction_type": "debit"}
        normalised = extractor._normalise_row(row)
        assert normalised["amount"] == 25.50  # abs()

    def test_extract_normalises_invalid_amount(self):
        extractor = TransactionExtractor()
        row = {"date": "2026-02-01", "description": "TEST", "amount": "N/A", "transaction_type": "debit"}
        normalised = extractor._normalise_row(row)
        assert normalised["amount"] == 0.0

    def test_extract_normalises_invalid_txn_type(self):
        extractor = TransactionExtractor()
        row = {"date": "2026-02-01", "description": "TEST", "amount": 10.0, "transaction_type": "UNKNOWN"}
        normalised = extractor._normalise_row(row)
        assert normalised["transaction_type"] == "debit"  # safe default

    def test_extract_handles_missing_date(self):
        extractor = TransactionExtractor()
        row = {"description": "TEST", "amount": 10.0, "transaction_type": "debit"}
        normalised = extractor._normalise_row(row)
        assert normalised["date"] == "1900-01-01"  # safe default

    def test_extract_structured_takes_priority_over_text(self, sample_transactions):
        """Structured parser rows beat AI text extraction."""
        extractor = TransactionExtractor()
        parsed_data = {
            "text": "some pdf text that would be sent to AI",
            "transactions": sample_transactions,
        }

        called = []

        def track(*args, **kwargs):
            called.append(1)
            return None

        with patch("app.ai.claude_client.call_claude", side_effect=track):
            result = extractor.extract(parsed_data)

        # AI should NOT have been called
        assert called == []
        assert len(result) == 3


# ── Claude client ─────────────────────────────────────────────────────────────

class TestClaudeClient:
    def test_call_returns_none_when_no_api_key(self):
        """call_claude returns None when ANTHROPIC_API_KEY is empty."""
        with patch("app.ai.claude_client._get_client", return_value=None):
            from app.ai.claude_client import call_claude
            result = call_claude("test prompt")
        assert result is None

    def test_call_returns_response_text(self):
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='["result"]')]
        mock_client.messages.create.return_value = mock_msg

        with patch("app.ai.claude_client._get_client", return_value=mock_client):
            # Reset singleton
            import app.ai.claude_client as cc
            cc._client = mock_client

            from app.ai.claude_client import call_claude
            result = call_claude("test prompt")

        assert result == '["result"]'


# ── Retry decorator ───────────────────────────────────────────────────────────

class TestRetryDecorator:
    def test_succeeds_first_try(self):
        from app.utils.retry import retry_with_backoff

        counter = {"n": 0}

        @retry_with_backoff(max_retries=3, initial_delay=0.0)
        def fn():
            counter["n"] += 1
            return "ok"

        result = fn()
        assert result == "ok"
        assert counter["n"] == 1

    def test_retries_on_failure(self):
        from app.utils.retry import retry_with_backoff

        counter = {"n": 0}

        @retry_with_backoff(max_retries=3, initial_delay=0.0)
        def fn():
            counter["n"] += 1
            if counter["n"] < 3:
                raise ValueError("not yet")
            return "ok"

        result = fn()
        assert result == "ok"
        assert counter["n"] == 3

    def test_raises_after_max_retries(self):
        from app.utils.retry import retry_with_backoff

        @retry_with_backoff(max_retries=2, initial_delay=0.0)
        def fn():
            raise RuntimeError("always fails")

        with pytest.raises(RuntimeError, match="always fails"):
            fn()
