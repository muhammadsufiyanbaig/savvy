"""Logging filter that masks PII before any log record is written."""

import logging
import re

_RULES = [
    # Pakistani CNIC: 35202-1234567-9
    (re.compile(r'\b\d{5}-\d{7}-\d\b'), 'CNIC-REDACTED'),
    # Pakistan mobile: 0311-1234567 / +923111234567
    (re.compile(r'(\+92|0)3\d{2}[-\s]?\d{7}\b'), 'PHONE-REDACTED'),
    # Generic email
    (re.compile(r'\b[\w.+-]+@[\w-]+\.\w{2,}\b'), 'EMAIL-REDACTED'),
    # Pakistan IBAN: PK36SCBL0000001123456702
    (re.compile(r'\bPK\d{2}[A-Z]{4}\d{16}\b'), 'IBAN-REDACTED'),
    # Generic 14–19 digit card/account number
    (re.compile(r'\b\d{14,19}\b'), 'ACCT-REDACTED'),
    # JWT-like tokens (three base64 segments) — don't log tokens
    (re.compile(r'ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'), 'JWT-REDACTED'),
]


class PiiMaskingFilter(logging.Filter):
    """Attach to any logger/handler to auto-redact PII from every log line."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            for pattern, replacement in _RULES:
                msg = pattern.sub(replacement, msg)
            record.msg = msg
            record.args = ()
        except Exception:
            pass
        return True


def attach_pii_filter(logger_name: str = "") -> None:
    """Attach PiiMaskingFilter to the named logger (default: root logger)."""
    logging.getLogger(logger_name).addFilter(PiiMaskingFilter())
