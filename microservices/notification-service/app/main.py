from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings

_MAX_BODY = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core import database as _db
    _db.Base.metadata.create_all(bind=_db.engine)

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
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

# ── Routers ────────────────────────────────────────────────────────────────────

from app.api import notifications, preferences  # noqa: E402

app.include_router(notifications.router, prefix="/api/v1", tags=["notifications"])
app.include_router(preferences.router, prefix="/api/v1", tags=["preferences"])


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
def health():
    from app.integrations import redis_client

    def _chk(fn):
        try:
            return "healthy" if fn() is not None else "unavailable"
        except Exception:
            return "unavailable"

    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "dependencies": {
            "redis": _chk(redis_client._get_redis_client),
            "smtp": "configured" if settings.SMTP_HOST else "not configured",
            "push": "configured" if settings.ONESIGNAL_APP_ID else "not configured",
            "kafka": "configured",
        },
    }
