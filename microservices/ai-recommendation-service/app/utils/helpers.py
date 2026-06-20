"""Shared helpers: JSON parsing, ID generation, prompt utilities."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def gen_id(prefix: str = "") -> str:
    short = str(uuid.uuid4())[:8]
    return f"{prefix}_{short}" if prefix else short


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def parse_json_safely(text: str, default: Any = None) -> Any:
    """Parse JSON from AI response; strip markdown fences if present."""
    if not text:
        return default
    # Strip ```json ... ``` fences
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        stripped = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        logger.debug("JSON parse failed: %s | text[:200]=%s", exc, text[:200])
        return default


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def format_currency(amount: float, currency: str = "USD") -> str:
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "PKR": "₨", "AED": "د.إ"}
    sym = symbols.get(currency, currency + " ")
    return f"{sym}{amount:,.2f}"
