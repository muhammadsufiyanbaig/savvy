"""JWT decode only — notification service has no users table."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/notifications/token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> int:
    """Decode JWT Bearer token, return user_id. Raises 401 on failure."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise credentials_exc

    sub: str = payload.get("sub")
    if sub is None:
        raise credentials_exc

    try:
        return int(sub)
    except (TypeError, ValueError):
        raise credentials_exc
