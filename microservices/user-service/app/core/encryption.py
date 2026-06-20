"""
Application-layer field encryption using Fernet (AES-128-CBC + HMAC-SHA256).

Usage — in SQLAlchemy models:
    from app.core.encryption import EncryptedString
    phone_number = Column(EncryptedString, nullable=True)

Values are transparently encrypted on write and decrypted on read.
Encrypted values are stored as base64url strings prefixed with 'enc:'.

Key: FIELD_ENCRYPTION_KEY env var (any length string → SHA-256 → Fernet-safe key).
Dev fallback key is hard-coded and NOT safe for production.
"""

import base64
import hashlib
import logging
import os

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)

_PREFIX = "enc:"
_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is not None:
        return _fernet
    try:
        from cryptography.fernet import Fernet
        raw_key = os.environ.get("FIELD_ENCRYPTION_KEY", "savvy-dev-field-key-not-for-production")
        derived = hashlib.sha256(raw_key.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(derived)
        _fernet = Fernet(fernet_key)
        if "dev" in raw_key:
            logger.warning("FIELD_ENCRYPTION_KEY is using dev fallback — set a real key in production!")
        return _fernet
    except ImportError:
        logger.error("cryptography package not installed — field encryption disabled. Run: pip install cryptography")
        return None
    except Exception as exc:
        logger.error("Fernet init failed: %s — field encryption disabled", exc)
        return None


def encrypt(value: str) -> str:
    f = _get_fernet()
    if f is None:
        return value
    return _PREFIX + f.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value.startswith(_PREFIX):
        return value  # legacy plaintext — return as-is
    f = _get_fernet()
    if f is None:
        return value
    try:
        from cryptography.fernet import InvalidToken
        return f.decrypt(value[len(_PREFIX):].encode()).decode()
    except InvalidToken:
        logger.error("Fernet decryption failed — data may be corrupted or key changed")
        return ""
    except Exception as exc:
        logger.error("Decryption error: %s", exc)
        return ""


class EncryptedString(TypeDecorator):
    """SQLAlchemy TypeDecorator — transparently encrypts/decrypts string columns."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt(str(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt(value)
