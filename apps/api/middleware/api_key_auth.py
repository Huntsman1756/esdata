"""API key authentication middleware for esdata API."""

import logging
import os

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from mcp_request_context import is_mcp_internal_request

logger = logging.getLogger(__name__)

# Paths that do NOT require authentication
PUBLIC_PATHS = (
    "/health",
    "/gpt-actions/modelos/openapi.json",
    "/gpt-actions/core/openapi.json",
    "/privacy",
    "/metrics",
)


def _is_public(path: str) -> bool:
    """Check if a path is public (no auth required)."""
    return path.startswith(PUBLIC_PATHS)


def _is_mcp_path(path: str) -> bool:
    """MCP uses its own dedicated guard and key."""
    return path.startswith("/mcp")


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Validate X-API-Key header on protected endpoints."""

    async def dispatch(self, request: Request, call_next) -> Response:
        app_env = os.environ.get("APP_ENV", "development").lower()
        api_key = os.environ.get("ESDATA_API_KEY", "")

        # Tests can opt into isolated bypasses; runtime stays fail-closed.
        if app_env == "test" and os.environ.get("ESDATA_ALLOW_INSECURE_TEST_AUTH", "").lower() == "true":
            return await call_next(request)

        path = request.url.path

        if _is_mcp_path(path):
            return await call_next(request)

        # MCP tool calls execute protected REST operations through an in-process
        # ASGI client. Those internal subrequests are already authorized by the
        # outer MCP guard and must not be challenged again with ESDATA_API_KEY.
        if is_mcp_internal_request():
            return await call_next(request)

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

        # Key validated: set principal on request state so query_audit_log
        # gets a meaningful user_id instead of 'anonymous'. Prefers the
        # explicit X-User-ID header (gateway/platform may inject per-call
        # identity), falls back to the API key label derived from env var name.
        header_user = request.headers.get("x-user-id") or request.headers.get("X-User-ID")
        if header_user:
            request.state.principal = header_user
        else:
            # Derive a stable, non-sensitive label from the key (first 4 chars).
            # This lets audit queries distinguish "dev-key" calls from "prod-key"
            # calls without leaking the full key.
            request.state.principal = f"apikey:{client_key[:4]}***"

        return await call_next(request)
