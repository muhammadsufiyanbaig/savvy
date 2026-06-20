import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

try:
    from shared.utils.pii_filter import attach_pii_filter
    attach_pii_filter()
except ImportError:
    pass

_MAX_BODY = 50 * 1024 * 1024  # 50 MB — PDF statements can be large


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.events.consumer import start_consumer
    start_consumer()
    yield


app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.VERSION,
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
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers.pop("server", None)
    return response

# ── Routes ─────────────────────────────────────────────────────────────────────

from app.api import statements as stmt_router  # noqa: E402

app.include_router(
    stmt_router.router,
    prefix="/api/v1/statements",
    tags=["statements"],
)


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
def health():
    from app.services import chroma_service, redis_service, s3_service

    def _check(fn):
        try:
            return "healthy" if fn() is not None else "unavailable"
        except Exception:
            return "unavailable"

    return {
        "status": "healthy",
        "service": "statement-analysis-service",
        "version": settings.VERSION,
        "dependencies": {
            "s3": _check(s3_service._get_s3),
            "chromadb": _check(chroma_service._get_chroma_client),
            "redis": _check(redis_service._get_redis_client),
            "claude_ai": "configured" if settings.ANTHROPIC_API_KEY else "not configured",
            "openai": "configured" if settings.OPENAI_API_KEY else "not configured",
        },
    }
