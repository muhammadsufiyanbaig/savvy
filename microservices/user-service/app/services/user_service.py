"""
User service — pure business logic, no HTTP concerns.
All Kafka publishing failures are logged but never bubble up to the caller
so a Kafka outage never breaks core user operations.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from app.schemas.user import PasswordChange, UserCreate, UserUpdate

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Lazy Kafka producer — avoids startup crash when Kafka is down
# --------------------------------------------------------------------------- #
_event_producer = None


def _get_producer():
    global _event_producer
    if _event_producer is None:
        try:
            from app.events.producer import UserEventProducer
            _event_producer = UserEventProducer()
        except Exception as exc:
            logger.warning("Kafka producer init failed (non-fatal): %s", exc)
    return _event_producer


def _publish(method: str, *args, **kwargs) -> None:
    producer = _get_producer()
    if producer is None:
        return
    try:
        getattr(producer, method)(*args, **kwargs)
    except Exception as exc:
        logger.error("Kafka publish failed [%s]: %s", method, exc)


# --------------------------------------------------------------------------- #
# Service functions
# --------------------------------------------------------------------------- #

def create_user(db: Session, data: UserCreate) -> User:
    """Register a new user. Raises ValueError on conflict."""
    if db.query(User).filter(User.email == data.email).first():
        raise ValueError("Email already registered")
    if db.query(User).filter(User.username == data.username).first():
        raise ValueError("Username already taken")

    user = User(
        email=data.email,
        username=data.username,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        phone_number=data.phone_number,
        country=data.country,
        city=data.city,
        currency=data.currency,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _publish(
        "publish_user_created",
        {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "country": user.country,
            "city": user.city,
            "currency": user.currency,
        },
    )

    logger.info("User created: id=%s, email=%s", user.id, user.email)
    return user


def authenticate_user(db: Session, login_id: str, password: str) -> Optional[User]:
    """
    Authenticate by username OR email.
    Returns User on success, None on failure.
    Also updates last_login on success.
    """
    user = db.query(User).filter(
        or_(User.username == login_id, User.email == login_id)
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        return None

    user.last_login = datetime.utcnow()
    db.commit()
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id, User.is_active == True).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def count_users(db: Session) -> int:
    return db.query(User).count()


def update_user(db: Session, user: User, data: UserUpdate) -> User:
    """Apply partial profile update. Only sets fields that were provided."""
    changed = data.model_dump(exclude_unset=True)
    if not changed:
        return user

    for field, value in changed.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    _publish("publish_user_updated", user.id, changed)
    logger.info("User updated: id=%s, fields=%s", user.id, list(changed.keys()))
    return user


def change_password(db: Session, user: User, data: PasswordChange) -> None:
    """
    Change user password.
    Raises ValueError if current password is wrong.
    Bumps token_version to invalidate all existing JWTs immediately.
    """
    if not verify_password(data.current_password, user.hashed_password):
        raise ValueError("Current password is incorrect")
    user.hashed_password = get_password_hash(data.new_password)
    user.token_version = (user.token_version or 0) + 1
    db.commit()
    logger.info("Password changed: user_id=%s — all existing sessions invalidated", user.id)


def delete_user(db: Session, user: User) -> None:
    """Hard-delete the user record and publish the event."""
    user_id = user.id
    db.delete(user)
    db.commit()
    _publish("publish_user_deleted", user_id)
    logger.info("User deleted: id=%s", user_id)


def verify_email(db: Session, user: User) -> User:
    user.is_verified = True
    db.commit()
    db.refresh(user)
    logger.info("Email verified: user_id=%s", user.id)
    return user


def deactivate_user(db: Session, user: User) -> User:
    """Soft-delete — keeps record but blocks login."""
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


def promote_to_admin(db: Session, user: User) -> User:
    user.role = UserRole.ADMIN
    db.commit()
    db.refresh(user)
    return user
