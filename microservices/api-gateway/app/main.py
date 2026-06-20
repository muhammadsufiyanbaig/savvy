"""
API Gateway — single entry point for all Savvy microservices.

Middleware stack (innermost first, outermost last = execution order top→bottom):
  1. RequestIDMiddleware   — inject X-Request-ID (~0µs)
  2. AuthMiddleware        — JWT pre-validation (~0.3ms, pure CPU)
  3. RateLimitMiddleware   — Redis pipeline check (~0.5ms)
  4. forward_request()     — proxy to downstream service

Total gateway overhead: ~1–2ms for authenticated requests with warm Redis.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.proxy.client import close_client, init_client
from app.proxy.router import forward_request

logger = logging.getLogger(__name__)


# ── Lifespan: warm up connection pool on startup ──────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_client()
    logger.info("API Gateway started — connection pool ready")
    yield
    await close_client()
    logger.info("API Gateway stopped")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Savvy API Gateway",
    version=settings.VERSION,
    description="Single entry point — routes requests to all Savvy microservices",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware (added last = executed first) ──────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Process-Time"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RequestIDMiddleware)

from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, include_in_schema=False)


# ── Latency header middleware ─────────────────────────────────────────────────

@app.middleware("http")
async def process_time_header(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - t0) * 1000:.2f}ms"
    return response


# ── Gateway endpoints ─────────────────────────────────────────────────────────

@app.get("/", tags=["gateway"])
async def root():
    return {
        "service": "Savvy API Gateway",
        "version": settings.VERSION,
        "status": "running",
        "upstream_services": [
            "user-service:8001",
            "finance-service:8002",
            "bank-service:8003",
            "statement-analysis-service:8004",
            "ai-recommendation-service:8005",
            "notification-service:8006",
        ],
    }


@app.get("/health", tags=["gateway"])
async def health():
    """Ping all upstream services concurrently and aggregate status."""
    from app.proxy.client import get_client

    service_urls = {
        "user":         settings.USER_SERVICE_URL,
        "finance":      settings.FINANCE_SERVICE_URL,
        "bank":         settings.BANK_SERVICE_URL,
        "statement":    settings.STATEMENT_SERVICE_URL,
        "ai":           settings.AI_SERVICE_URL,
        "notification": settings.NOTIFICATION_SERVICE_URL,
    }

    async def ping(name: str, base_url: str) -> tuple:
        t0 = time.perf_counter()
        try:
            client = get_client()
            resp = await client.get(f"{base_url}/health", timeout=5.0)
            ms = (time.perf_counter() - t0) * 1000
            return name, {"status": "healthy" if resp.status_code == 200 else "unhealthy",
                          "response_time_ms": round(ms, 1)}
        except Exception as exc:
            ms = (time.perf_counter() - t0) * 1000
            return name, {"status": "unreachable", "error": str(exc)[:80],
                          "response_time_ms": round(ms, 1)}

    results = await asyncio.gather(*[ping(n, u) for n, u in service_urls.items()])
    service_status = dict(results)
    overall = "healthy" if all(v["status"] == "healthy" for v in service_status.values()) else "degraded"

    return {
        "gateway": "healthy",
        "version": settings.VERSION,
        "overall_status": overall,
        "services": service_status,
    }


# ── Catch-all proxy route ─────────────────────────────────────────────────────

@app.api_route(
    "/api/v1/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    tags=["proxy"],
    include_in_schema=False,
)
async def proxy(request: Request):
    """Forward any /api/v1/** request to the appropriate upstream service."""
    return await forward_request(request)
