"""AI-powered transaction extraction with Claude → OpenAI → rule-based fallback."""

import json
import logging
from typing import Dict, List

from app.ai import claude_client, openai_client
from app.ai.input_sanitizer import sanitise
from app.ai.prompts import EXTRACTION_SYSTEM, extraction_user_message
from app.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class TransactionExtractor:
    """Extract structured transactions from raw bank-statement text."""

    # ── public ────────────────────────────────────────────────────────────────

    def extract(self, parsed_data: Dict) -> List[Dict]:
        """Return list of raw transaction dicts.

        Strategy:
          1. If parsed_data already has structured rows, use them.
          2. Otherwise send plain text to Claude / OpenAI.
          3. Fallback: return whatever rows the parser found (may be empty).
        """
        # Structured data from CSV/Excel parsers — no AI needed
        if parsed_data.get("transactions"):
            rows = parsed_data["transactions"]
            if rows:
                logger.debug("Using %d parser-extracted rows", len(rows))
                return [self._normalise_row(r) for r in rows]

        # PDF / plain text — needs AI
        text = parsed_data.get("text", "").strip()
        if text:
            try:
                text = sanitise(text, max_chars=50_000, source="bank statement")
            except ValueError as exc:
                logger.warning("Statement text rejected by sanitiser: %s", exc)
                return []
            ai_result = self._extract_via_ai(text)
            if ai_result:
                return ai_result

        logger.warning("AI extraction skipped or failed; returning parser rows")
        return [self._normalise_row(r) for r in parsed_data.get("transactions", [])]

    # ── private ───────────────────────────────────────────────────────────────

    @retry_with_backoff(max_retries=2, initial_delay=2.0, exceptions=(Exception,))
    def _call_ai(self, text: str) -> str:
        user_msg = extraction_user_message(text)
        # Try Claude with cached system prompt first (10× cheaper on cache hit)
        result = claude_client.call_claude_cached(EXTRACTION_SYSTEM, user_msg)
        if result:
            return result
        # Fallback to OpenAI — combine system + user into one prompt
        fallback_prompt = f"{EXTRACTION_SYSTEM}\n\n{user_msg}"
        result = openai_client.call_openai(fallback_prompt)
        if result:
            return result
        raise RuntimeError("Both Claude and OpenAI returned None")

    def _extract_via_ai(self, text: str) -> List[Dict]:
        try:
            raw = self._call_ai(text)
            if not raw:
                return []
            transactions = json.loads(raw)
            if not isinstance(transactions, list):
                return []
            return [self._normalise_row(t) for t in transactions if isinstance(t, dict)]
        except Exception as exc:
            logger.error("AI extraction parse error: %s", exc)
            return []

    @staticmethod
    def _normalise_row(row: Dict) -> Dict:
        """Ensure all expected keys exist with safe defaults."""
        try:
            amount = abs(float(row.get("amount", 0) or 0))
        except (TypeError, ValueError):
            amount = 0.0

        txn_type = str(row.get("transaction_type", "debit") or "debit").lower().strip()
        if txn_type not in ("debit", "credit"):
            txn_type = "debit"

        return {
            "date": str(row.get("date", "") or "").strip() or "1900-01-01",
            "description": str(row.get("description", "") or "").strip(),
            "amount": amount,
            "transaction_type": txn_type,
            "merchant": str(row.get("merchant", "") or "").strip() or None,
            "category_hint": str(row.get("category_hint", "") or "").strip() or None,
        }
