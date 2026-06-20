"""Bank Service — FastAPI application."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core import database as _db

_MAX_BODY = 50 * 1024 * 1024  # 50 MB — bank statements can be large

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Bank Service starting…")
    _db.Base.metadata.create_all(bind=_db.engine)

    try:
        from app.events.consumer import start_consumer
        t = start_consumer()
        logger.info("Kafka consumer started: %s", t.name)
    except Exception as exc:
        logger.warning("Kafka consumer failed to start (non-fatal): %s", exc)

    yield
    logger.info("Bank Service shutting down…")


app = FastAPI(
    title="Savvy Bank Service",
    description="Bank account management and statement upload/download",
    version="1.0.0",
    lifespan=lifespan,
)

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


# ── Routers ───────────────────────────────────────────────────────────────────
from app.api.accounts import router as accounts_router
from app.api.statements import router as statements_router

PREFIX = "/api/v1/banks"

app.include_router(accounts_router, prefix=PREFIX)
app.include_router(statements_router, prefix=PREFIX)


@app.get("/health")
def health():
    return {"status": "ok", "service": "bank-service", "version": settings.VERSION}
