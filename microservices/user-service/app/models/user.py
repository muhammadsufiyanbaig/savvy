from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.encryption import EncryptedString
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    ADVISOR = "advisor"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)

    # Stored encrypted (AES-128-CBC via Fernet); FIELD_ENCRYPTION_KEY env var
    phone_number = Column(EncryptedString, nullable=True)

    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Location for AI recommendations
    country = Column(String)
    city = Column(String)
    currency = Column(String, default="USD")

    # Notification preferences
    notification_enabled = Column(Boolean, default=True)
    daily_reminder_time = Column(String)

    # Session invalidation on password/email change — bump this to kill all existing JWTs
    token_version = Column(Integer, default=0, nullable=False, server_default="0")

    # MFA / TOTP
    mfa_enabled = Column(Boolean, default=False, nullable=False, server_default="false")
    mfa_secret = Column(EncryptedString, nullable=True)          # active TOTP secret (base32)
    mfa_backup_codes = Column(Text, nullable=True)               # JSON array of bcrypt-hashed backup codes

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
