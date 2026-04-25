"""Rate limiting middleware for esdata API.

Uses an in-memory token bucket algorithm. Configurable per-endpoint via
ESDATA_RATE_LIMIT_* environment variables.

Default limits (when no env var override):
- /health: 100 req/min (public, no auth)
- /v1/*: 60 req/min (public API)
- /mcp*: 30 req/min (MCP endpoint)
- default: 30 req/min (catch-all)
"""

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict

from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(default=0.0, init=False)
    last_refill: float = field(default=0.0, init=False)

    def __post_init__(self):
        self.tokens = self.capacity
        self.last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiter:
    """In-memory rate limiter with per-client tracking."""

    def __init__(self) -> None:
        self._buckets: Dict[str, TokenBucket] = {}
        self._endpoint_limits: Dict[str, Dict[str, tuple[int, int]]] = {
            "/health": {"default": (100, 60)},
            "/v1": {"default": (60, 60)},
            "/mcp": {"default": (30, 60)},
        }
        self._default_limit: tuple[int, int] = (30, 60)  # (tokens, window_seconds)

    def _get_client_key(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Check X-Forwarded-For header first (behind reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        # Fall back to client host
        if request.client:
            return request.client.host
        return "unknown"

    def _get_endpoint_prefix(self, path: str) -> str:
        """Get the matching endpoint prefix for rate limit config."""
        if path.startswith("/health"):
            return "/health"
        if path.startswith("/mcp"):
            return "/mcp"
        if path.startswith("/v1"):
            return "/v1"
        return "default"

    def _get_bucket(self, client_key: str, endpoint: str) -> TokenBucket:
        """Get or create a token bucket for the client+endpoint combo."""
        bucket_key = f"{client_key}:{endpoint}"

        if bucket_key not in self._buckets:
            limits = self._endpoint_limits.get(endpoint, {})
            config = limits.get("default", self._default_limit)
            capacity, window = config
            rate = capacity / window
            self._buckets[bucket_key] = TokenBucket(
                capacity=capacity,
                refill_rate=rate,
            )

        return self._buckets[bucket_key]

    async def check_rate_limit(self, request: Request) -> Response | None:
        """Check if request is within rate limits.

        Returns a JSONResponse with 429 if rate limited, None otherwise.
        """
        client_key = self._get_client_key(request)
        endpoint_prefix = self._get_endpoint_prefix(request.url.path)
        bucket = self._get_bucket(client_key, endpoint_prefix)

        if not bucket.consume():
            logger.warning(
                "Rate limit exceeded: client=%s endpoint=%s path=%s",
                client_key,
                endpoint_prefix,
                request.url.path,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please slow down your requests.",
                    "retry_after": 1,
                },
                headers={"Retry-After": "1"},
            )

        return None


# Global rate limiter instance
_rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware for rate limiting.

    Usage: Add to main.py with:
        app.add_middleware(rate_limit_middleware)
    """
    # Allow disabling rate limiting via env var (e.g. in tests)
    if os.environ.get("ESDATA_RATE_LIMIT_ENABLED", "true").lower() == "false":
        return await call_next(request)

    response = await _rate_limiter.check_rate_limit(request)
    if response:
        return response

    response = await call_next(request)

    # Add rate limit headers to successful responses
    client_key = _rate_limiter._get_client_key(request)
    endpoint_prefix = _rate_limiter._get_endpoint_prefix(request.url.path)
    bucket = _rate_limiter._get_bucket(client_key, endpoint_prefix)

    response.headers["X-RateLimit-Limit"] = str(bucket.capacity)
    response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))

    return response
