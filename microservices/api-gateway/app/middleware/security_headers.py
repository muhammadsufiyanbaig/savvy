"""Inject security headers on every response from the API gateway."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        h = response.headers

        # Prevent MIME-type sniffing
        h["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        h["X-Frame-Options"] = "DENY"
        # Reflected XSS filter (legacy browsers)
        h["X-XSS-Protection"] = "1; mode=block"
        # Don't leak origin in Referer header to third parties
        h["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Disable unneeded browser features
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        # Force HTTPS for 1 year (only effective over TLS — no-op in plain HTTP dev)
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # CSP: only load resources from own origin; connect to Anthropic API only
        h["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' https://api.anthropic.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Isolate browsing context (defence against Spectre / cross-origin leaks)
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        h["Cross-Origin-Resource-Policy"] = "same-origin"

        # Remove server fingerprint
        h.pop("server", None)
        h.pop("x-powered-by", None)

        return response
