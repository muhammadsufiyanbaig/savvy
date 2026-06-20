"""Pure-CPU JWT decode — zero I/O, called on every protected request."""

from typing import Optional
from jose import JWTError, jwt
from .config import settings


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate JWT. Tries SECRET_KEY first; falls back to SECRET_KEY_PREVIOUS
    during the 24-hour dual-validity rotation window.
    ~0.3ms — pure Python, no network, no DB.
    """
    keys = [settings.SECRET_KEY]
    if settings.SECRET_KEY_PREVIOUS:
        keys.append(settings.SECRET_KEY_PREVIOUS)
    for key in keys:
        try:
            return jwt.decode(token, key, algorithms=[settings.ALGORITHM])
        except JWTError:
            continue
    return None


def user_id_from_payload(payload: dict) -> Optional[int]:
    try:
        return int(payload.get("sub") or payload.get("user_id", 0))
    except (TypeError, ValueError):
        return None
