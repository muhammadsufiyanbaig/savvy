from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    SERVICE_NAME: str = "notification-service"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Database
    DATABASE_URL: str = "postgresql://user:password@notification-db:5432/notification_db"

    # Redis
    REDIS_URL: str = "redis://redis:6379/3"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC_PREFIX: str = "financial_"
    KAFKA_GROUP_ID: str = "notification-service-group"

    # JWT (shared secret — decode only, no user DB)
    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars!!"
    ALGORITHM: str = "HS256"

    # SMTP email (optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "notifications@savvy.com"
    SMTP_FROM_NAME: str = "Savvy"
    SMTP_USE_TLS: bool = True

    # OneSignal push (optional)
    ONESIGNAL_APP_ID: Optional[str] = None
    ONESIGNAL_API_KEY: Optional[str] = None

    # Notification settings
    MAX_NOTIFICATIONS_PER_PAGE: int = 50
    DEDUP_WINDOW_SECONDS: int = 60        # suppress identical notifs within window
    NOTIFICATION_TTL_DAYS: int = 30       # auto-expire old notifications
    UNREAD_COUNT_CACHE_TTL: int = 60      # Redis TTL for unread count cache

    class Config:
        env_file = ".env"


settings = Settings()
