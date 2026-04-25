"""Request logging middleware for esdata API.

Logs every request with method, path, status, duration, and IP.
Uses standard Python logging with JSON-compatible format for easy aggregation.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("esdata.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with timing and client IP."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4())[:8])
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        ip = self._client_ip(request)

        log_data = {
            "type": "access",
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "status": response.status_code,
            "duration_ms": round(elapsed_ms, 2),
            "ip": ip,
            "user_agent": request.headers.get("user-agent", "")[:200],
        }

        logger.info(
            "%s %s %d %.2fms %s",
            ip,
            request.method,
            response.status_code,
            elapsed_ms,
            request.url.path,
            extra=log_data,
        )

        response.headers["x-request-id"] = request_id
        return response

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
