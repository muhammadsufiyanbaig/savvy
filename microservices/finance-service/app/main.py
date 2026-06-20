"""Finance Service — FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core import database as _db

_MAX_BODY = 10 * 1024 * 1024

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Finance Service starting…")

    # Start Kafka consumer in background daemon thread
    try:
        from app.events.consumer import start_consumer
        consumer_thread = start_consumer()
        logger.info("Kafka consumer thread started: %s", consumer_thread.name)
    except Exception as exc:
        logger.warning("Kafka consumer failed to start (non-fatal): %s", exc)

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Finance Service shutting down…")


app = FastAPI(
    title="Savvy Finance Service",
    description="Expenses, savings goals, budgets, spending limits, zakat, qurbani",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


@app.middleware("http")
async def rls_user_id_middleware(request: Request, call_next):
    """
    Set `_current_user_id` context var so that `get_db` can issue
    `SET LOCAL app.user_id = X` before the first query — enabling PostgreSQL RLS.
    X-User-ID is injected by the api-gateway after JWT validation.
    """
    from app.core.database import _current_user_id
    uid = request.headers.get("x-user-id", "0")
    token = _current_user_id.set(uid)
    try:
        response = await call_next(request)
    finally:
        _current_user_id.reset(token)
    return response


# ── Routers ─��─────────────────────────────────────────────────────────────────
from app.api.expenses import router as expenses_router
from app.api.savings import router as savings_router
from app.api.cash_savings import router as cash_savings_router
from app.api.budgets import router as budgets_router
from app.api.spending_limits import router as spending_limits_router
from app.api.zakat import router as zakat_router
from app.api.qurbani import router as qurbani_router
from app.api.assets import router as assets_router
from app.api.sadaqah import router as sadaqah_router
from app.api.liabilities import router as liabilities_router
from app.api.hajj_umrah import router as hajj_umrah_router
from app.api.health_score import router as health_score_router

PREFIX = "/api/v1"

app.include_router(expenses_router, prefix=PREFIX)
app.include_router(savings_router, prefix=PREFIX)
app.include_router(cash_savings_router, prefix=PREFIX)
app.include_router(budgets_router, prefix=PREFIX)
app.include_router(spending_limits_router, prefix=PREFIX)
app.include_router(zakat_router, prefix=PREFIX)
app.include_router(qurbani_router, prefix=PREFIX)
app.include_router(assets_router, prefix=PREFIX)
app.include_router(sadaqah_router, prefix=PREFIX)
app.include_router(liabilities_router, prefix=PREFIX)
app.include_router(hajj_umrah_router, prefix=PREFIX)
app.include_router(health_score_router, prefix=PREFIX)


@app.get("/health")
def health(db: _db.SessionLocal = None):
    from sqlalchemy import text
    try:
        db = _db.SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "service": "finance-service"}
    except Exception as exc:
        logger.error("Health check DB failed: %s", exc)
        from fastapi.responses import JSONResponse
        return JSONResponse({"status": "unhealthy", "detail": "database unreachable"}, status_code=503)
