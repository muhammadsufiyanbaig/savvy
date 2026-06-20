"""
Pydantic v2 schemas for the User Service.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# --------------------------------------------------------------------------- #
# Request schemas
# --------------------------------------------------------------------------- #

class UserCreate(BaseModel):
    """Registration payload."""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    currency: str = "USD"

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 30:
            raise ValueError("Username must be at most 30 characters")
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError(
                "Username may only contain lowercase letters, numbers, and underscores"
            )
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("currency")
    @classmethod
    def currency_valid(cls, v: str) -> str:
        return v.upper()


class UserUpdate(BaseModel):
    """Profile update payload — all fields optional."""
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    notification_enabled: Optional[bool] = None
    daily_reminder_time: Optional[str] = None

    @field_validator("daily_reminder_time")
    @classmethod
    def time_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("daily_reminder_time must be in HH:MM format")
        return v

    @field_validator("currency")
    @classmethod
    def currency_valid(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else v


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("New password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("New password must contain at least one digit")
        return v


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class EmailVerificationRequest(BaseModel):
    token: str


# MFA schemas
class MfaSetupResponse(BaseModel):
    secret: str
    qr_uri: str
    backup_codes: List[str]


class MfaVerifyRequest(BaseModel):
    code: str


class MfaCompleteRequest(BaseModel):
    mfa_token: str
    code: str


class MfaDisableRequest(BaseModel):
    code: str  # TOTP code required to disable MFA


# --------------------------------------------------------------------------- #
# Response schemas
# --------------------------------------------------------------------------- #

class UserResponse(BaseModel):
    """Full user profile returned to the authenticated user themselves."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    currency: str
    role: str
    is_active: bool
    is_verified: bool
    notification_enabled: bool
    daily_reminder_time: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class UserPublicResponse(BaseModel):
    """Minimal public profile."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: Optional[str] = None
    role: str
    created_at: datetime


class UserListResponse(BaseModel):
    """Paginated list of users (admin)."""
    items: List[UserResponse]
    total: int
    page: int
    size: int


# --------------------------------------------------------------------------- #
# Auth response schemas
# --------------------------------------------------------------------------- #

class UserSummary(BaseModel):
    id: int
    email: str
    username: str
    role: str


class TokenResponse(BaseModel):
    """Full login response including both tokens. When MFA is required, only mfa_token is set."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user: Optional[UserSummary] = None
    mfa_required: bool = False
    mfa_token: Optional[str] = None


class AccessTokenResponse(BaseModel):
    """Token-refresh response — access token only."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPairResponse(BaseModel):
    """Rotation response — new access + new refresh token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# --------------------------------------------------------------------------- #
# Generic response schemas
# --------------------------------------------------------------------------- #

class MessageResponse(BaseModel):
    message: str
    detail: Optional[Dict[str, Any]] = None
