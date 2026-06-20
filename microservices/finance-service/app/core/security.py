"""
JWT validation for Finance Service.
Decodes tokens issued by User Service using the shared SECRET_KEY.
Returns user_id (int) — no DB lookup needed.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# tokenUrl points to user-service login for Swagger UI convenience
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.USER_SERVICE_URL}/api/v1/users/login"
)


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """
    Validate Bearer JWT and return the user_id (int).
    Raises HTTP 401 on any validation failure.
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as err:
        logger.debug("JWT decode failed: %s", err)
        raise exc

    if payload.get("type") != "access":
        raise exc

    sub: Optional[str] = payload.get("sub")
    if sub is None:
        raise exc

    try:
        return int(sub)
    except ValueError:
        raise exc
