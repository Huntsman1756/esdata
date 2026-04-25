"""API key authentication middleware for esdata API.

Validates requests via the `X-API-Key` header against the value of
the `ESDATA_API_KEY` environment variable.

Public (unprotected) paths:
- /health
- /metrics (if exposed)
- /gpt-actions/*

Protected paths:
- Everything else, including all /v1/* endpoints and /mcp.

When auth is enabled and the key is missing or invalid, returns 401.
"""

import logging
import os

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Paths that do NOT require authentication
PUBLIC_PATHS = ("/health", "/metrics", "/gpt-actions")


def _is_public(path: str) -> bool:
    """Check if a path is public (no auth required)."""
    return path.startswith(PUBLIC_PATHS)


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Validate X-API-Key header on protected endpoints."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Read env vars on every request so tests can change them
        auth_enabled = os.environ.get("ESDATA_AUTH_ENABLED", "").lower() == "true"
        api_key = os.environ.get("ESDATA_API_KEY", "")

        # If auth is disabled entirely, skip all checks
        if not auth_enabled:
            return await call_next(request)

        path = request.url.path

        # Public paths are always allowed
        if _is_public(path):
            return await call_next(request)

        # Check API key
        client_key = request.headers.get("x-api-key", "")

        if not client_key:
            logger.warning("Missing API key for path: %s", path)
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "API key required. Provide it via the X-API-Key header.",
                },
            )

        if client_key != api_key:
            logger.warning("Invalid API key for path: %s", path)
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Invalid API key.",
                },
            )

        return await call_next(request)
