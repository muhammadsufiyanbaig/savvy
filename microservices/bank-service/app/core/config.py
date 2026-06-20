"""Bank Service configuration."""
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    SERVICE_NAME: str = "Bank Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    PORT: int = 8003
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Database
    DATABASE_URL: str = "postgresql://bank_service:bank_password@bank-db:5432/bank_db"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC_PREFIX: str = "financial_"
    KAFKA_GROUP_ID: str = "bank-service-group"

    # JWT — must match user-service SECRET_KEY
    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars!!"
    ALGORITHM: str = "HS256"

    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "financial-statements"
    S3_PRESIGNED_URL_EXPIRES: int = 3600   # 1 hour

    # File upload limits
    MAX_FILE_SIZE_BYTES: int = 52_428_800  # 50 MB
    ALLOWED_FILE_TYPES: List[str] = ["pdf", "csv", "xlsx", "xls"]

    # Service URLs
    USER_SERVICE_URL: str = "http://user-service:8001"

    class Config:
        env_file = ".env"


settings = Settings()
