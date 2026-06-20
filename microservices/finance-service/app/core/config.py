import sys
from pydantic_settings import BaseSettings
from typing import List

_INSECURE_KEY = "your-secret-key-change-in-production-min-32-chars!!"


class Settings(BaseSettings):
    SERVICE_NAME: str = "Finance Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: List[str] = ["*"]

    DATABASE_URL: str = "postgresql://finance_service:finance_password@finance-db:5432/finance_db"
    REDIS_URL: str = "redis://redis:6379/1"

    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC_PREFIX: str = "financial_"
    KAFKA_GROUP_ID: str = "finance-service-group"

    # Must match user-service SECRET_KEY (shared JWT secret)
    SECRET_KEY: str = _INSECURE_KEY
    ALGORITHM: str = "HS256"

    # Service URLs
    USER_SERVICE_URL: str = "http://user-service:8001"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8006"
    AI_SERVICE_URL: str = "http://ai-service:8005"

    # Business config
    DEFAULT_CURRENCY: str = "USD"
    BUDGET_ALERT_THRESHOLD: float = 80.0
    SPENDING_LIMIT_ALERT_THRESHOLD: float = 80.0

    class Config:
        env_file = ".env"


settings = Settings()

if settings.ENVIRONMENT == "production" and settings.SECRET_KEY == _INSECURE_KEY:
    sys.exit("FATAL: SECRET_KEY is the insecure default. Set SECRET_KEY env var before starting in production.")
