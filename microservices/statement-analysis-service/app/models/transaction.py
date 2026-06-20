from typing import List, Optional
from pydantic import BaseModel, field_validator


class Transaction(BaseModel):
    """Extracted and categorized transaction."""

    date: str                           # YYYY-MM-DD
    description: str
    amount: float
    transaction_type: str               # "debit" | "credit"
    merchant: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    confidence_score: float = 0.0
    category_hint: Optional[str] = None
    tags: List[str] = []
    categorization_method: Optional[str] = None  # "vector" | "rule" | "ai"

    @field_validator("transaction_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("debit", "credit"):
            return "debit"              # safe default
        return v

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v: float) -> float:
        return abs(v)
