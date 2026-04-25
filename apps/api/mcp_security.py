"""MCP HTTP guard — minimal API key + rate limit protection for /mcp endpoint."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Request
from fastapi.responses import JSONResponse


_RATE_BUCKETS: dict[str, Deque[float]] = defaultdict(deque)


def _required_api_key() -> str:
    return os.getenv("MCP_API_KEY", "").strip()


def _rate_limit() -> int:
    return int(os.getenv("MCP_RATE_LIMIT_PER_MINUTE", "60"))


async def guard_mcp_http(request: Request, call_next):
    if not request.url.path.startswith("/mcp"):
        return await call_next(request)

    required_key = _required_api_key()
    provided_key = request.headers.get("X-API-Key", "")

    if required_key and provided_key != required_key:
        return JSONResponse({"detail": "Invalid or missing MCP API key"}, status_code=401)

    if required_key:
        key = provided_key or (request.client.host if request.client else "unknown")
        bucket = _RATE_BUCKETS[key]
        now = time.time()
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= _rate_limit():
            return JSONResponse({"detail": "MCP rate limit exceeded"}, status_code=429)
        bucket.append(now)

    return await call_next(request)


def reset_mcp_rate_limit_state() -> None:
    _RATE_BUCKETS.clear()
