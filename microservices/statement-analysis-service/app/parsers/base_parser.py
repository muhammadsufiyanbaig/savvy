from abc import ABC, abstractmethod
from typing import Dict, List


class BaseParser(ABC):
    """Abstract base class for all bank-statement parsers."""

    @abstractmethod
    def parse(self, file_content: bytes) -> Dict:
        """Parse file bytes and return structured data.

        Returns a dict with at minimum:
          - "text": str  (raw text, may be empty)
          - "transactions": list of raw row dicts (may be empty)
          - "page_count" or "row_count": int
          - "metadata": dict (any extra info)
        """

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_amount(raw: str) -> float:
        """Convert a raw amount string like '$1,234.56' to 1234.56."""
        if raw is None:
            return 0.0
        cleaned = str(raw).replace("$", "").replace(",", "").strip()
        try:
            return abs(float(cleaned))
        except ValueError:
            return 0.0

    @staticmethod
    def _detect_transaction_type(raw: str) -> str:
        """Guess debit/credit from common column values."""
        if raw is None:
            return "debit"
        low = str(raw).lower().strip()
        if any(k in low for k in ("credit", "cr", "deposit", "refund")):
            return "credit"
        return "debit"
