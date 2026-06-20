from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "Statement Analysis Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8004
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # JWT (shared secret with all services)
    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars!!"
    ALGORITHM: str = "HS256"

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "savvy-statements"

    # AI Providers
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AI_PROVIDER: str = "claude"          # "claude" | "openai"
    AI_MODEL: str = "claude-3-sonnet-20240229"
    AI_MAX_RETRIES: int = 3
    AI_TIMEOUT_SECONDS: int = 60

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "transaction_patterns"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/3"
    REDIS_CACHE_TTL: int = 3600

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:29092"
    KAFKA_TOPIC_PREFIX: str = "financial_"
    KAFKA_GROUP_ID: str = "statement-service-group"

    # Processing limits
    MAX_FILE_SIZE_MB: int = 10
    MAX_TRANSACTIONS_PER_STATEMENT: int = 1000
    CONFIDENCE_THRESHOLD: float = 0.7

    model_config = {"env_file": ".env"}


settings = Settings()
