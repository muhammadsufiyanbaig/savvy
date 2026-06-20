"""
AI input sanitiser — strips prompt injection attempts and dangerous content
from user-supplied text / context before it enters any AI prompt.
"""

import re
from typing import Any, Dict

# Known prompt injection phrase patterns
_INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(all\s+)?(previous|prior|above)\s+instructions?', re.I),
    re.compile(r'new\s+system\s+(prompt|instructions?)', re.I),
    re.compile(r'disregard\s+(all|everything|previous|prior)', re.I),
    re.compile(r'you\s+are\s+now\s+(?:a|an)\s+\w+', re.I),
    re.compile(r'act\s+as\s+(?:if\s+you\s+are|a|an)', re.I),
    re.compile(r'\bDAN\s+(?:mode|protocol|jailbreak)\b', re.I),
    re.compile(r'\bjailbreak\b', re.I),
    re.compile(r'reveal\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?)', re.I),
    re.compile(r'repeat\s+(?:all|everything|your)\s+(?:previous\s+)?(?:instructions?|prompt)', re.I),
    re.compile(r'<\s*system\s*>', re.I),
    re.compile(r'your\s+actual\s+instructions\s+are', re.I),
    re.compile(r'(?:pretend|roleplay|simulate)\s+(?:you\s+(?:are|have)\s+no)', re.I),
    re.compile(r'override\s+(?:your\s+)?(?:safety|ethical|previous)', re.I),
]

_INVISIBLE = re.compile(
    r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f'
    r'​-‏‪-‮⁠-⁤﻿]'
)

# PII patterns — stripped from context dicts before sending to AI
_PII_STRIP = [
    re.compile(r'\b\d{5}-\d{7}-\d\b'),                          # CNIC
    re.compile(r'(\+92|0)3\d{2}[-\s]?\d{7}\b'),                 # phone
    re.compile(r'\b[\w.+-]+@[\w-]+\.\w{2,}\b'),                 # email
    re.compile(r'\bPK\d{2}[A-Z]{4}\d{16}\b'),                   # IBAN
    re.compile(r'\b\d{14,19}\b'),                                # card/account number
]

# PII patterns for scanning AI output (stricter — any hit = discard response)
_PII_OUTPUT = _PII_STRIP  # same patterns serve both purposes


def sanitise_text(text: str, max_chars: int = 50_000, source: str = "input") -> str:
    """
    Clean user-supplied text.
    Raises ValueError on injection detection.
    """
    if not isinstance(text, str):
        text = str(text)
    text = text[:max_chars]
    text = _INVISIBLE.sub('', text)
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"Invalid content detected in {source}")
    return text.strip()


def anonymise_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strip PII from a context dict before sending to Claude.

    Rules:
    - Remove keys whose names suggest PII (email, phone, cnic, name, iban)
    - Scrub PII patterns from string values
    - Keep all numeric/financial fields intact
    """
    _PII_KEYS = {"email", "phone", "phone_number", "cnic", "full_name", "name", "iban", "account_number"}

    clean = {}
    for key, value in context.items():
        if key.lower() in _PII_KEYS:
            continue  # drop PII fields entirely
        if isinstance(value, str):
            for pattern in _PII_STRIP:
                value = pattern.sub('[REDACTED]', value)
        clean[key] = value
    return clean


def scan_output_for_pii(text: str) -> bool:
    """Return True if AI output appears to contain PII — caller should discard response."""
    for pattern in _PII_OUTPUT:
        if pattern.search(text):
            return True
    return False
