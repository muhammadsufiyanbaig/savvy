import sys
from typing import List, Optional
from pydantic_settings import BaseSettings

_INSECURE_KEY = "your-secret-key-change-in-production-min-32-chars!!"


class Settings(BaseSettings):
    SERVICE_NAME: str = "api-gateway"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Downstream service URLs
    USER_SERVICE_URL: str = "http://user-service:8001"
    FINANCE_SERVICE_URL: str = "http://finance-service:8002"
    BANK_SERVICE_URL: str = "http://bank-service:8003"
    STATEMENT_SERVICE_URL: str = "http://statement-analysis-service:8004"
    AI_SERVICE_URL: str = "http://ai-recommendation-service:8005"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8006"

    # JWT (decode-only — no user DB)
    SECRET_KEY: str = _INSECURE_KEY
    # During key rotation: set SECRET_KEY_PREVIOUS to old key; gateway accepts both
    # for the 24-hour dual-validity window, then remove it.
    SECRET_KEY_PREVIOUS: Optional[str] = None
    ALGORITHM: str = "HS256"

    # Rate limiting
    RATE_LIMIT_ANON: int = 60      # req/window — unauthenticated
    RATE_LIMIT_AUTH: int = 300     # req/window — authenticated
    RATE_LIMIT_WINDOW: int = 60    # window in seconds

    # Connection pool
    HTTP_POOL_MAX_CONNECTIONS: int = 100
    HTTP_POOL_MAX_KEEPALIVE: int = 20
    HTTP_TIMEOUT: float = 30.0

    # Redis
    REDIS_URL: str = "redis://redis:6379/4"

    # CORS — override via env var in production:
    # ALLOWED_ORIGINS=["https://app.savvy.com","https://savvy.com"]
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    class Config:
        env_file = ".env"


settings = Settings()

if settings.ENVIRONMENT == "production" and settings.SECRET_KEY == _INSECURE_KEY:
    sys.exit("FATAL: SECRET_KEY is the insecure default. Set SECRET_KEY env var before starting in production.")

# ── Service map: prefix → URL ──────────────────────────────────────────────────
SERVICE_MAP: dict = {
    "/api/v1/users":            settings.USER_SERVICE_URL,
    "/api/v1/expenses":         settings.FINANCE_SERVICE_URL,
    "/api/v1/savings":          settings.FINANCE_SERVICE_URL,
    "/api/v1/budgets":          settings.FINANCE_SERVICE_URL,
    "/api/v1/spending-limits":  settings.FINANCE_SERVICE_URL,
    "/api/v1/zakat":            settings.FINANCE_SERVICE_URL,
    "/api/v1/qurbani":          settings.FINANCE_SERVICE_URL,
    "/api/v1/cash-savings":     settings.FINANCE_SERVICE_URL,
    "/api/v1/assets":           settings.FINANCE_SERVICE_URL,
    "/api/v1/sadaqah":          settings.FINANCE_SERVICE_URL,
    "/api/v1/liabilities":      settings.FINANCE_SERVICE_URL,
    "/api/v1/hajj-umrah":       settings.FINANCE_SERVICE_URL,
    "/api/v1/financial-health": settings.FINANCE_SERVICE_URL,
    "/api/v1/banks":            settings.BANK_SERVICE_URL,
    "/api/v1/statements":       settings.STATEMENT_SERVICE_URL,
    "/api/v1/ai":               settings.AI_SERVICE_URL,
    "/api/v1/notifications":    settings.NOTIFICATION_SERVICE_URL,
}

# Sorted longest-first so /api/v1/spending-limits matches before /api/v1/savings
SORTED_PREFIXES = sorted(SERVICE_MAP.keys(), key=len, reverse=True)

# Public paths — skip JWT validation
PUBLIC_PATHS: frozenset = frozenset({
    "/api/v1/users/register",
    "/api/v1/users/login",
    "/api/v1/users/mfa/complete",   # second-factor login (uses mfa_token, not JWT)
    "/api/v1/users/verify-email",
    "/api/v1/users/refresh",
    "/api/v1/users/forgot-password",
    "/api/v1/users/reset-password",
    "/health",
    "/",
})
