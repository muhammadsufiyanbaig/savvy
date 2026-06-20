"""
AI input sanitiser — strips prompt injection attempts and dangerous content
from user-supplied text before it enters any AI prompt.
"""

import re

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

# Unicode control and invisible characters that can hide injections
_INVISIBLE = re.compile(
    r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f'
    r'​-‏‪-‮⁠-⁤﻿]'
)

# HTML/XML tags (indirect injection via document content)
_HTML_TAGS = re.compile(r'<[^>]{0,200}>')


def sanitise(text: str, max_chars: int = 50_000, source: str = "input") -> str:
    """
    Clean user-supplied text before including in AI prompts.

    Steps:
    1. Truncate to max_chars
    2. Strip invisible / control Unicode characters
    3. Strip HTML / XML tags
    4. Raise ValueError if prompt injection pattern detected

    Returns cleaned text on success.
    Raises ValueError with a generic message on injection detection
    (caller should return 400 Bad Request without exposing the pattern).
    """
    if not isinstance(text, str):
        text = str(text)

    # 1. Truncate
    text = text[:max_chars]

    # 2. Strip invisible chars
    text = _INVISIBLE.sub('', text)

    # 3. Strip HTML/XML tags (replace with space to preserve word boundaries)
    text = _HTML_TAGS.sub(' ', text)

    # 4. Injection detection
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"Invalid content detected in {source}")

    return text.strip()
