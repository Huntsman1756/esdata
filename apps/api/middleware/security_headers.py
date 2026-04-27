"""Security headers middleware for esdata API.

Adds standard security headers to every response:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 0
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: camera=(), microphone=(), geolocation=()
- Strict-Transport-Security (when ESDATA_HSTS_ENABLED=true)
- X-Request-ID: generated UUID if not provided
- X-Generated-By: AI component version (when AI-assisted)
- X-AI-Disclaimer: legal disclaimer for AI-generated content
"""

import logging
import os
import uuid

from fastapi import Request, Response
from services.ai_disclaimer import get_ai_headers
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # Generate request ID if not present
        request_id = request.headers.get("x-request-id")
        if not request_id:
            request_id = str(uuid.uuid4())
        response.headers["X-Request-ID"] = request_id

        # HSTS (only when explicitly enabled)
        if os.environ.get("ESDATA_HSTS_ENABLED", "").lower() == "true":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # AI labeling headers (only for AI-component responses)
        ai_headers = get_ai_headers(
            path=request.url.path,
            headers={k.lower(): v for k, v in request.headers.items()},
        )
        for key, value in ai_headers.items():
            response.headers[key] = value

        return response
