"""
User Service API routes.

All endpoints live under /api/v1/users (prefix set in main.py).
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    blacklist_token,
    clear_login_failures,
    create_access_token,
    create_refresh_token,
    create_mfa_token,
    create_verification_token,
    generate_backup_codes,
    generate_mfa_secret,
    get_current_admin,
    get_current_user,
    get_totp_uri,
    is_login_locked,
    oauth2_scheme,
    record_failed_login,
    revoke_all_refresh_tokens,
    rotate_refresh_token,
    verify_backup_code,
    verify_mfa_token,
    verify_refresh_token,
    verify_totp,
    verify_verification_token,
)
from app.models.user import User
from app.schemas.user import (
    AccessTokenResponse,
    EmailVerificationRequest,
    MessageResponse,
    MfaCompleteRequest,
    MfaDisableRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    PasswordChange,
    RefreshTokenRequest,
    TokenPairResponse,
    TokenResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserSummary,
    UserUpdate,
)
from app.services import user_service as svc
from app.utils import audit
from fastapi import Request

logger = logging.getLogger(__name__)
router = APIRouter()


# --------------------------------------------------------------------------- #
# Public endpoints (no auth required)
# --------------------------------------------------------------------------- #

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
)
async def register(data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.

    - **email**: must be unique, valid email
    - **username**: 3-30 chars, alphanumeric + underscores, lowercase
    - **password**: min 8 chars, must include uppercase, lowercase, digit
    - **currency**: ISO 4217 code (default USD)
    """
    try:
        user = svc.create_user(db, data)
        audit.log("USER_REGISTER", user_id=user.id, resource_type="user", resource_id=user.id)
        return user
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT tokens",
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2-compatible login.

    - **username**: username or email
    - **password**: account password

    Returns access token (30 min) + refresh token (7 days).
    """
    identifier = form_data.username.lower()
    client_ip = request.client.host if request.client else "unknown"

    if is_login_locked(identifier):
        audit.log("LOGIN_BLOCKED", ip=client_ip, success=False, extra={"reason": "account_locked"})
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to too many failed attempts. Try again in 5 minutes.",
            headers={"Retry-After": "300"},
        )

    user = svc.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        count = record_failed_login(identifier)
        remaining = max(0, 5 - count)
        detail = "Invalid username or password"
        if remaining == 0:
            detail = "Invalid username or password. Account locked for 5 minutes."
        elif remaining <= 2:
            detail = f"Invalid username or password. {remaining} attempt(s) remaining before lockout."
        audit.log("LOGIN_FAILED", ip=client_ip, success=False, extra={"attempts_remaining": remaining})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account is deactivated"
        )

    clear_login_failures(identifier)

    # MFA check: if MFA is enabled, issue a short-lived intermediate token
    if user.mfa_enabled and user.mfa_secret:
        mfa_tok = create_mfa_token(user.id)
        audit.log("LOGIN_MFA_REQUIRED", user_id=user.id, ip=client_ip, resource_type="user", resource_id=user.id)
        return TokenResponse(mfa_required=True, mfa_token=mfa_tok)

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        token_version=user.token_version or 0,
    )
    refresh_token = create_refresh_token(user.id)

    audit.log("LOGIN_SUCCESS", user_id=user.id, ip=client_ip, resource_type="user", resource_id=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserSummary(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role.value,
        ),
    )


@router.post(
    "/token/refresh",
    response_model=TokenPairResponse,
    summary="Refresh access token (rotation — old refresh token invalidated)",
)
async def refresh_token(
    body: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """
    Exchange a refresh token for new access + refresh tokens.

    The presented refresh token is consumed (one-time use). If a previously used
    token is replayed, the account is locked immediately — indicates token theft.
    """
    try:
        user_id = rotate_refresh_token(body.refresh_token)
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("refresh_token_reuse:"):
            # Possible theft — bump token_version to invalidate all sessions
            try:
                uid = int(msg.split(":")[1])
                stolen_user = svc.get_user_by_id(db, uid)
                if stolen_user:
                    stolen_user.token_version = (stolen_user.token_version or 0) + 1
                    db.commit()
                    logger.warning("Refresh token reuse detected — all sessions invalidated for user_id=%s", uid)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or already-used refresh token",
        )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = svc.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        token_version=user.token_version or 0,
    )
    new_refresh_token = create_refresh_token(user.id)
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email with token",
)
async def verify_email(body: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Mark user email as verified using the token sent to them."""
    user_id = verify_verification_token(body.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_verified:
        return MessageResponse(message="Email already verified")

    svc.verify_email(db, user)
    return MessageResponse(message="Email verified successfully")


# --------------------------------------------------------------------------- #
# Authenticated user endpoints
# --------------------------------------------------------------------------- #

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (invalidate access token)",
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Blacklist the current access token so it can't be reused."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        blacklist_token(token)
    client_ip = request.client.host if request.client else "unknown"
    audit.log("LOGOUT", user_id=current_user.id, ip=client_ip)
    return MessageResponse(message="Logged out successfully")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Logout from all devices",
)
async def logout_all(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Revoke all refresh tokens — forces re-login on all devices."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        blacklist_token(token)
    revoke_all_refresh_tokens(current_user.id)
    return MessageResponse(message="Logged out from all devices")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the full profile of the authenticated user."""
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update editable profile fields.

    Only fields included in the request body are changed;
    omitted fields stay unchanged.
    """
    return svc.update_user(db, current_user, data)


@router.post(
    "/me/password",
    response_model=MessageResponse,
    summary="Change password",
)
async def change_password(
    request: Request,
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password — requires current password. Invalidates all existing sessions."""
    client_ip = request.client.host if request.client else "unknown"
    try:
        svc.change_password(db, current_user, data)
        audit.log("PASSWORD_CHANGE", user_id=current_user.id, ip=client_ip,
                  resource_type="user", resource_id=current_user.id)
        return MessageResponse(message="Password updated successfully. All other sessions have been logged out.")
    except ValueError as exc:
        audit.log("PASSWORD_CHANGE_FAILED", user_id=current_user.id, ip=client_ip,
                  success=False, extra={"reason": str(exc)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete(
    "/me",
    response_model=MessageResponse,
    summary="Delete account",
)
async def delete_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    **Permanently** delete the authenticated user's account.

    This action cannot be undone. All data associated with this account
    will be removed via cascading Kafka events to other services.
    """
    svc.delete_user(db, current_user)
    return MessageResponse(message="Account deleted successfully")


@router.post(
    "/me/send-verification",
    response_model=MessageResponse,
    summary="Request email verification link",
)
async def send_verification(current_user: User = Depends(get_current_user)):
    """
    Send email verification link to the user's email address via notification-service.
    """
    if current_user.is_verified:
        return MessageResponse(message="Email already verified")

    token = create_verification_token(current_user.id)

    try:
        from app.events.producer import UserEventProducer
        producer = UserEventProducer()
        producer.publish_verification_requested(
            user_id=current_user.id,
            email=current_user.email,
            token=token,
            full_name=current_user.full_name,
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Kafka publish failed (non-fatal): %s", exc)

    return MessageResponse(message="Verification email sent")


# --------------------------------------------------------------------------- #
# MFA endpoints
# --------------------------------------------------------------------------- #

@router.post(
    "/mfa/complete",
    response_model=TokenResponse,
    summary="Complete MFA login — second factor",
)
async def mfa_complete(
    body: MfaCompleteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Exchange mfa_token + TOTP code for full JWT access + refresh tokens."""
    import json

    client_ip = request.client.host if request.client else "unknown"

    user_id = verify_mfa_token(body.mfa_token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired MFA session")

    user = svc.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # Try TOTP code first, then backup codes
    code_valid = False
    if user.mfa_secret and verify_totp(user.mfa_secret, body.code):
        code_valid = True
    elif user.mfa_backup_codes:
        valid, updated_json = verify_backup_code(user.mfa_backup_codes, body.code)
        if valid:
            user.mfa_backup_codes = updated_json
            db.commit()
            code_valid = True

    if not code_valid:
        audit.log("LOGIN_MFA_FAILED", user_id=user_id, ip=client_ip, success=False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        token_version=user.token_version or 0,
    )
    refresh_tok = create_refresh_token(user.id)
    audit.log("LOGIN_SUCCESS", user_id=user.id, ip=client_ip, resource_type="user", resource_id=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_tok,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserSummary(id=user.id, email=user.email, username=user.username, role=user.role.value),
    )


@router.post(
    "/me/mfa/setup",
    response_model=MfaSetupResponse,
    summary="Begin MFA setup — returns TOTP secret + QR URI + backup codes",
)
async def mfa_setup(
    current_user: User = Depends(get_current_user),
):
    """
    Generate a new TOTP secret and backup codes. The secret is stored temporarily
    in Redis; call /me/mfa/verify within 10 minutes to activate MFA.
    """
    from app.core.security import get_redis

    secret = generate_mfa_secret()
    qr_uri = get_totp_uri(secret, current_user.email)
    plaintext_codes, _ = generate_backup_codes(8)

    # Store pending setup in Redis (10-min TTL) — not activated until verify
    r = get_redis()
    if r:
        import json
        r.setex(
            f"mfa_setup:{current_user.id}",
            600,
            json.dumps({"secret": secret, "backup_codes_plain": plaintext_codes}),
        )

    return MfaSetupResponse(secret=secret, qr_uri=qr_uri, backup_codes=plaintext_codes)


@router.post(
    "/me/mfa/verify",
    response_model=MessageResponse,
    summary="Confirm MFA setup with a TOTP code",
)
async def mfa_verify(
    body: MfaVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify the TOTP code to activate MFA. Invalidates all existing sessions."""
    import json
    from app.core.security import get_redis

    r = get_redis()
    if not r:
        raise HTTPException(status_code=503, detail="MFA setup requires Redis")

    pending_json = r.get(f"mfa_setup:{current_user.id}")
    if not pending_json:
        raise HTTPException(status_code=400, detail="No pending MFA setup found. Call /me/mfa/setup first.")

    pending = json.loads(pending_json)
    secret = pending["secret"]

    if not verify_totp(secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    # Activate MFA — hash and store backup codes
    from app.core.security import get_password_hash
    plaintext_codes = pending["backup_codes_plain"]
    hashed_codes = [get_password_hash(c) for c in plaintext_codes]

    current_user.mfa_secret = secret
    current_user.mfa_backup_codes = json.dumps(hashed_codes)
    current_user.mfa_enabled = True
    # Bump token_version — all existing sessions must re-authenticate with MFA
    current_user.token_version = (current_user.token_version or 0) + 1
    db.commit()

    r.delete(f"mfa_setup:{current_user.id}")
    return MessageResponse(message="MFA enabled successfully. All existing sessions have been logged out.")


@router.post(
    "/me/mfa/disable",
    response_model=MessageResponse,
    summary="Disable MFA — requires valid TOTP code",
)
async def mfa_disable(
    body: MfaDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable MFA. Requires current TOTP code to confirm identity."""
    if not current_user.mfa_enabled or not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled on this account")

    if not verify_totp(current_user.mfa_secret, body.code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_backup_codes = None
    current_user.token_version = (current_user.token_version or 0) + 1
    db.commit()
    return MessageResponse(message="MFA disabled. All sessions logged out.")


# --------------------------------------------------------------------------- #
# Admin-only endpoints
# --------------------------------------------------------------------------- #

@router.get(
    "/",
    response_model=UserListResponse,
    summary="List all users (admin)",
)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Paginated list of all users. Admin access required."""
    skip = (page - 1) * size
    users = svc.get_all_users(db, skip=skip, limit=size)
    total = svc.count_users(db)
    return UserListResponse(items=users, total=total, page=page, size=size)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID (admin)",
)
async def get_user_by_id(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve any user by ID. Admin access required."""
    user = svc.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Delete user by ID (admin)",
)
async def admin_delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Hard-delete any user. Admin access required."""
    user = svc.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    svc.delete_user(db, user)
    return MessageResponse(message=f"User {user_id} deleted")
