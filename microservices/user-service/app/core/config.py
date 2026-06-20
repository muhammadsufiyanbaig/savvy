import sys
from pydantic_settings import BaseSettings
from typing import List

_INSECURE_KEY = "your-secret-key-change-in-production-min-32-chars!!"


class Settings(BaseSettings):
    SERVICE_NAME: str = "User Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    # In production K8s: override via ALLOWED_ORIGINS env var
    # user-service is ClusterIP-only, but keep this tight for defence-in-depth
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Database
    DATABASE_URL: str = "postgresql://user:password@user-db:5432/user_db"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC_PREFIX: str = "financial_"
    KAFKA_GROUP_ID: str = "user-service-group"

    # JWT
    SECRET_KEY: str = _INSECURE_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24

    class Config:
        env_file = ".env"


settings = Settings()

if settings.ENVIRONMENT == "production" and settings.SECRET_KEY == _INSECURE_KEY:
    sys.exit("FATAL: SECRET_KEY is the insecure default. Set SECRET_KEY env var before starting in production.")
