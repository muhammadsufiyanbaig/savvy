from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "AI Recommendation Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8005
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # JWT (shared secret with all services)
    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars!!"
    ALGORITHM: str = "HS256"

    # AI
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # Redis
    REDIS_URL: str = "redis://localhost:6379/4"
    RECOMMENDATION_CACHE_TTL: int = 3600

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:29092"
    KAFKA_TOPIC_PREFIX: str = "financial_"
    KAFKA_GROUP_ID: str = "ai-service-group"

    # Market data
    YAHOO_FINANCE_ENABLED: bool = True
    ALPHA_VANTAGE_API_KEY: str = ""

    # Processing
    LANGGRAPH_ENABLED: bool = True
    WORKFLOW_TIMEOUT: int = 60
    CONFIDENCE_THRESHOLD: float = 0.75

    model_config = {"env_file": ".env"}


settings = Settings()
