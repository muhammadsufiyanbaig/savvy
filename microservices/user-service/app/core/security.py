"""
Security utilities: password hashing, JWT token management,
Redis-backed blacklisting/refresh, and FastAPI auth dependencies.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import redis as redis_lib
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# --------------------------------------------------------------------------- #
# Redis client (optional – degrades gracefully if unavailable)
# --------------------------------------------------------------------------- #
_redis: Optional[redis_lib.Redis] = None


def get_redis() -> Optional[redis_lib.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
            _redis.ping()
        except Exception as exc:
            logger.warning("Redis unavailable – token blacklist disabled: %s", exc)
            _redis = None
    return _redis


# --------------------------------------------------------------------------- #
# Token creation
# --------------------------------------------------------------------------- #
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    token_version: int = 0,
) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload.update({"exp": expire, "type": "access", "ver": token_version})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


_MAX_SESSIONS = 5  # max concurrent sessions per user


def create_refresh_token(user_id: int) -> str:
    import uuid
    jti = str(uuid.uuid4())
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expiry_ts = expire.timestamp()
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh", "jti": jti}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    r = get_redis()
    if r:
        try:
            ttl = int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())
            # One-time-use token lookup
            r.setex(f"rt:{jti}", ttl, str(user_id))

            # Concurrent session tracking: sorted set keyed by user, scored by expiry
            sessions_key = f"sessions:{user_id}"
            now_ts = datetime.utcnow().timestamp()
            pipe = r.pipeline()
            pipe.zremrangebyscore(sessions_key, 0, now_ts)   # purge expired
            pipe.zadd(sessions_key, {jti: expiry_ts})
            pipe.expire(sessions_key, ttl)
            pipe.execute()

            # Enforce concurrent session limit — evict oldest over the cap
            overflow = r.zcard(sessions_key) - _MAX_SESSIONS
            if overflow > 0:
                oldest_jtis = r.zrange(sessions_key, 0, overflow - 1)
                for old_jti in oldest_jtis:
                    r.delete(f"rt:{old_jti}")
                r.zremrangebyrank(sessions_key, 0, overflow - 1)
                logger.info("Evicted %d old session(s) for user_id=%s (cap=%d)", overflow, user_id, _MAX_SESSIONS)
        except Exception as exc:
            logger.warning("Could not store refresh token in Redis: %s", exc)

    return token


def create_verification_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(
        hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
    )
    payload = {"sub": str(user_id), "exp": expire, "type": "email_verification"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# --------------------------------------------------------------------------- #
# Token verification
# --------------------------------------------------------------------------- #
def _decode(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[dict]:
    payload = _decode(token)
    if not payload or payload.get("type") != "access":
        return None

    # Blacklist check
    r = get_redis()
    if r:
        try:
            if r.get(f"blacklist:{token}"):
                return None
        except Exception:
            pass

    return payload


def verify_refresh_token(token: str) -> Optional[int]:
    """Verify refresh token. Returns user_id or None. Does NOT consume the token."""
    payload = _decode(token)
    if not payload or payload.get("type") != "refresh":
        return None
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        return None


def rotate_refresh_token(token: str) -> Optional[int]:
    """
    Validate and consume a refresh token (rotation).

    - If JWT valid AND jti in Redis: delete jti, return user_id (caller must issue new tokens)
    - If JWT valid BUT jti NOT in Redis: token was already used — possible theft;
      lock the account via token_version bump (caller handles), return None
    - If JWT invalid: return None

    Returns user_id on success, raises ValueError on reuse-detected, returns None on bad token.
    """
    payload = _decode(token)
    if not payload or payload.get("type") != "refresh":
        return None

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        return None

    jti = payload.get("jti")
    r = get_redis()
    if r and jti:
        try:
            deleted = r.delete(f"rt:{jti}")
            if deleted == 0:
                # Token was already used or never registered — possible theft
                raise ValueError(f"refresh_token_reuse:{user_id}")
        except ValueError:
            raise
        except Exception as exc:
            logger.warning("Redis error during token rotation: %s — failing open", exc)

    return user_id


def verify_verification_token(token: str) -> Optional[int]:
    payload = _decode(token)
    if not payload or payload.get("type") != "email_verification":
        return None
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Token revocation (logout)
# --------------------------------------------------------------------------- #
def blacklist_token(token: str) -> None:
    """Add an access token to the Redis blacklist until it naturally expires."""
    r = get_redis()
    if not r:
        return
    try:
        # Decode without raising so we can extract expiry
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},
        )
        exp = payload.get("exp")
        if exp:
            ttl = int(exp - datetime.utcnow().timestamp())
            if ttl > 0:
                r.setex(f"blacklist:{token}", ttl, "1")
    except Exception as exc:
        logger.warning("Could not blacklist token: %s", exc)


def revoke_all_refresh_tokens(user_id: int) -> None:
    """Delete all refresh tokens and session entries for a user (force re-login everywhere)."""
    r = get_redis()
    if not r:
        return
    try:
        # Revoke all tracked JTIs from the sessions sorted set
        sessions_key = f"sessions:{user_id}"
        all_jtis = r.zrange(sessions_key, 0, -1)
        for jti in all_jtis:
            r.delete(f"rt:{jti}")
        r.delete(sessions_key)
        # Old-style keys (backward compat)
        for key in r.scan_iter(f"refresh:{user_id}:*"):
            r.delete(key)
    except Exception as exc:
        logger.warning("Could not revoke refresh tokens: %s", exc)


# --------------------------------------------------------------------------- #
# MFA / TOTP helpers
# --------------------------------------------------------------------------- #

def generate_mfa_secret() -> str:
    """Generate a random base32 TOTP secret."""
    import pyotp
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "Savvy") -> str:
    """Return otpauth:// URI for QR code generation."""
    import pyotp
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code. Allows ±1 window (30s tolerance)."""
    import pyotp
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    except Exception:
        return False


def generate_backup_codes(count: int = 8) -> tuple[list[str], list[str]]:
    """
    Generate backup codes.
    Returns (plaintext_list, hashed_list) — store hashed, show plaintext once.
    """
    import secrets
    plaintext = [f"{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}" for _ in range(count)]
    hashed = [get_password_hash(code) for code in plaintext]
    return plaintext, hashed


def verify_backup_code(stored_hashes_json: str, code: str) -> tuple[bool, str]:
    """
    Check a backup code against the stored hashed list.
    Returns (valid, updated_json) — removes the used code on success.
    """
    import json
    try:
        hashes = json.loads(stored_hashes_json)
    except Exception:
        return False, stored_hashes_json
    for i, h in enumerate(hashes):
        if verify_password(code, h):
            hashes.pop(i)
            return True, json.dumps(hashes)
    return False, stored_hashes_json


def create_mfa_token(user_id: int) -> str:
    """Short-lived (5 min) JWT issued after password check when MFA is required."""
    expire = datetime.utcnow() + timedelta(minutes=5)
    payload = {"sub": str(user_id), "exp": expire, "type": "mfa_required"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_mfa_token(token: str) -> Optional[int]:
    """Verify MFA intermediate token. Returns user_id or None."""
    payload = _decode(token)
    if not payload or payload.get("type") != "mfa_required":
        return None
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Brute-force login protection
# --------------------------------------------------------------------------- #
_BRUTE_FORCE_MAX = 5        # lock after this many consecutive failures
_BRUTE_FORCE_WINDOW = 300   # 5-minute sliding window


def is_login_locked(identifier: str) -> bool:
    """Return True if the identifier (username/email) is temporarily locked."""
    r = get_redis()
    if not r:
        return False
    try:
        count = r.get(f"login_fail:{identifier}")
        return int(count or 0) >= _BRUTE_FORCE_MAX
    except Exception:
        return False


def record_failed_login(identifier: str) -> int:
    """Increment failure counter and set/reset TTL. Returns current count."""
    r = get_redis()
    if not r:
        return 0
    key = f"login_fail:{identifier}"
    try:
        count = r.incr(key)
        if count == 1:
            r.expire(key, _BRUTE_FORCE_WINDOW)
        return count
    except Exception:
        return 0


def clear_login_failures(identifier: str) -> None:
    """Remove failure counter on successful login."""
    r = get_redis()
    if not r:
        return
    try:
        r.delete(f"login_fail:{identifier}")
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# FastAPI OAuth2 scheme & dependencies
# --------------------------------------------------------------------------- #
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Resolve the JWT Bearer token to a User ORM object."""
    from app.models.user import User  # local import avoids circular deps

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_access_token(token)
    if payload is None:
        raise credentials_exc

    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise credentials_exc

    # Try Redis cache first
    r = get_redis()
    if r:
        try:
            import json
            cached = r.get(f"user:{user_id_str}")
            if cached:
                # Still hit DB to return proper ORM object (cache used only for quick 404)
                pass
        except Exception:
            pass

    user = db.query(User).filter(User.id == int(user_id_str)).first()
    if user is None:
        raise credentials_exc
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    # Session invalidation: JWT ver must match current token_version in DB.
    # Password change bumps token_version → all older JWTs become invalid.
    if payload.get("ver", 0) != (user.token_version or 0):
        raise credentials_exc

    return user


def get_current_verified_user(
    current_user=Depends(get_current_user),
):
    """Like get_current_user but also requires email verification."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email first.",
        )
    return current_user


def get_current_admin(current_user=Depends(get_current_user)):
    """Require ADMIN role."""
    from app.models.user import UserRole

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user
