import os
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse


_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def reset_mcp_rate_limit_state() -> None:
    _RATE_BUCKETS.clear()


def _required_api_key() -> str:
    return os.getenv("MCP_API_KEY", "").strip()


def _rate_limit_per_minute() -> int:
    raw = os.getenv("MCP_RATE_LIMIT_PER_MINUTE", "60").strip() or "60"
    return max(1, int(raw))


async def guard_mcp_http(request: Request, call_next):
    if not request.url.path.startswith("/mcp"):
        return await call_next(request)

    required_key = _required_api_key()
    if not required_key:
        return await call_next(request)

    provided_key = request.headers.get("X-API-Key", "")
    if provided_key != required_key:
        return JSONResponse({"detail": "Invalid or missing MCP API key"}, status_code=401)

    bucket_key = provided_key
    bucket = _RATE_BUCKETS[bucket_key]
    now = time.time()

    while bucket and now - bucket[0] > 60:
        bucket.popleft()

    if len(bucket) >= _rate_limit_per_minute():
        return JSONResponse({"detail": "MCP rate limit exceeded"}, status_code=429)

    bucket.append(now)
    return await call_next(request)
