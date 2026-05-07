import os
from collections import deque

from fastapi import Request
from fastapi.responses import JSONResponse


def reset_mcp_rate_limit_state() -> None:
    pass


async def guard_mcp_http(request: Request, call_next):
    if not request.url.path.startswith("/mcp"):
        return await call_next(request)

    if request.method == "GET":
        accept = request.headers.get("accept", "")
        if "text/event-stream" not in accept.lower():
            response = JSONResponse(
                {"detail": "MCP requires Accept: text/event-stream for GET requests"},
                status_code=406,
            )
            request_id = request.headers.get("x-request-id")
            if request_id:
                response.headers["X-Request-ID"] = request_id
            return response

    app_env = os.environ.get("APP_ENV", "").lower()
    if app_env != "test":
        provided_key = request.headers.get("X-API-Key", "")
        required_key = os.getenv("MCP_API_KEY", "").strip()
        if required_key and provided_key != required_key:
            return JSONResponse({"detail": "Invalid or missing MCP API key"}, status_code=401)
        elif not required_key:
            return JSONResponse({"detail": "Invalid or missing MCP API key"}, status_code=401)

    return await call_next(request)
