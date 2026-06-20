"""
User Service — FastAPI application entry point.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine

_MAX_BODY = 10 * 1024 * 1024  # 10 MB hard limit per request

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

# Attach PII masking filter to root logger — redacts CNIC, phone, email, IBAN from all logs
try:
    from shared.utils.pii_filter import attach_pii_filter
    attach_pii_filter()
except ImportError:
    pass  # shared module not on path — no-op

# Internal service auth middleware — validates HMAC signatures from api-gateway
try:
    from shared.utils.service_auth import InternalAuthMiddleware as _InternalAuthMiddleware
    _HAS_INTERNAL_AUTH = True
except ImportError:
    _HAS_INTERNAL_AUTH = False

# Dedicated audit logger: structured JSON, never masked (audit entries must not contain raw PII)
logging.getLogger("savvy.audit").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    logger.info("Starting %s v%s [%s]", settings.SERVICE_NAME, settings.VERSION, settings.ENVIRONMENT)

    # Create database tables (Alembic handles migrations in prod;
    # this is a dev/test safety net)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created")

    # Warm up Redis connection (non-fatal)
    from app.core.security import get_redis
    r = get_redis()
    if r:
        logger.info("Redis connection OK")
    else:
        logger.warning("Redis unavailable — token blacklisting disabled")

    yield

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("Shutting down %s", settings.SERVICE_NAME)


# --------------------------------------------------------------------------- #
# App factory
# --------------------------------------------------------------------------- #
app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    description=(
        "User management, authentication, and authorization service "
        "for the Savvy Financial Management System."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Internal service signature validation (added last = runs first)
if _HAS_INTERNAL_AUTH:
    app.add_middleware(_InternalAuthMiddleware)

from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, include_in_schema=False)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > _MAX_BODY:
        return JSONResponse({"detail": "Request body too large"}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers.pop("server", None)
    return response

# --------------------------------------------------------------------------- #
# Routers
# --------------------------------------------------------------------------- #
from app.api.users import router as users_router

app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])


# --------------------------------------------------------------------------- #
# Infrastructure endpoints
# --------------------------------------------------------------------------- #

@app.get("/", tags=["Info"])
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Info"])
async def health_check():
    """
    Returns service health including DB and Redis status.
    Used by Docker/Kubernetes liveness probes and the API Gateway.
    """
    health: dict = {"status": "healthy", "service": settings.SERVICE_NAME}

    # Database probe
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health["database"] = "healthy"
    except Exception as exc:
        health["database"] = f"unhealthy: {exc}"
        health["status"] = "degraded"

    # Redis probe
    from app.core.security import get_redis
    r = get_redis()
    health["redis"] = "healthy" if r else "unavailable"

    return health


# --------------------------------------------------------------------------- #
# Dev server entry point
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
