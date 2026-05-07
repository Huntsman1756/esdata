import os
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

from mcp_request_context import mcp_request_scope


_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def reset_mcp_rate_limit_state() -> None:
    _RATE_BUCKETS.clear()


def _required_api_key() -> str:
    return os.getenv("MCP_API_KEY", "").strip()


def _rate_limit_per_minute() -> int:
    raw = os.getenv("MCP_RATE_LIMIT_PER_MINUTE", "60").strip() or "60"
    return max(1, int(raw))


def _requires_sse_accept(request: Request) -> bool:
    return request.method == "GET" and request.url.path.rstrip("/") == "/mcp"


def _mcp_error_response(request: Request, content: dict, status_code: int) -> JSONResponse:
    response = JSONResponse(content, status_code=status_code)
    request_id = request.headers.get("x-request-id") or request.headers.get("X-Request-ID")
    if request_id:
        response.headers["x-request-id"] = request_id
    return response


async def guard_mcp_http(request: Request, call_next):
    if not request.url.path.startswith("/mcp"):
        return await call_next(request)

    request_id = request.headers.get("x-request-id") or request.headers.get("X-Request-ID")
    user_id = request.headers.get("x-user-id") or request.headers.get("X-User-ID")
    with mcp_request_scope(request_id=request_id, user_id=user_id):
        required_key = _required_api_key()
        if not required_key:
            if _requires_sse_accept(request):
                accept = request.headers.get("accept", "")
                if "text/event-stream" not in accept.lower():
                    return _mcp_error_response(
                        request,
                        {"detail": "MCP GET requires Accept: text/event-stream"},
                        406,
                    )
            return await call_next(request)

        provided_key = request.headers.get("X-API-Key", "")
        if provided_key != required_key:
            return _mcp_error_response(request, {"detail": "Invalid or missing MCP API key"}, 401)

        bucket_key = provided_key
        bucket = _RATE_BUCKETS[bucket_key]
        now = time.time()

        while bucket and now - bucket[0] > 60:
            bucket.popleft()

        if len(bucket) >= _rate_limit_per_minute():
            return _mcp_error_response(request, {"detail": "MCP rate limit exceeded"}, 429)

        bucket.append(now)

        if _requires_sse_accept(request):
            accept = request.headers.get("accept", "")
            if "text/event-stream" not in accept.lower():
                return _mcp_error_response(
                    request,
                    {"detail": "MCP GET requires Accept: text/event-stream"},
                    406,
                )

        return await call_next(request)
