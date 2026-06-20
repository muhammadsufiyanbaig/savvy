"""
Inject X-Request-ID on every request.
- If client sends one: reuse it (tracing continuity)
- If not: generate UUID4
Adds same ID to response so client can correlate logs.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())

        # Store on request state so other middleware/handlers can read it
        request.state.request_id = req_id

        # Mutate scope headers to inject downstream — cheapest way in Starlette
        headers = dict(request.scope.get("headers", []))
        headers[b"x-request-id"] = req_id.encode()
        request.scope["headers"] = list(headers.items())

        response = await call_next(request)
        response.headers["x-request-id"] = req_id
        return response
