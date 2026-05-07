"""Rate limiting middleware for esdata API.

Uses a token bucket algorithm. By default persists buckets in-memory.
When REDIS_URL is set, switches to a Redis-backed token bucket for
cross-instance shared state and persistence across restarts.

Configurable per-endpoint via ESDATA_RATE_LIMIT_* environment variables.

Default limits (when no env var override):
- /health: 100 req/min (public, no auth)
- /v1/*: 60 req/min (public API)
- /mcp*: 30 req/min (MCP endpoint)
- default: 30 req/min (catch-all)
"""

import logging
import os
import time
from dataclasses import dataclass, field

from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory token bucket (original implementation, unchanged logic)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Redis-backed token bucket
# ---------------------------------------------------------------------------

class RedisTokenBucket:
    """Token bucket backed by Redis using Lua scripting for atomicity.

    Uses a Lua script to atomically check and consume tokens in Redis,
    avoiding race conditions in distributed deployments.

    Redis keys:
        rl:{client_key}:{endpoint}  -> hash with 'tokens' and 'last_refill'
    """

    # Lua script for atomic token bucket operation.
    # Returns: [allowed (0/1), remaining_tokens, retry_after_seconds]
    LUA_SCRIPT = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local refill_rate = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local requested = tonumber(ARGV[4])

    local data = redis.call('HMGET', key, 'tokens', 'last_refill')
    local tokens = tonumber(data[1])
    local last_refill = tonumber(data[2])

    if tokens == nil then
        tokens = capacity
        last_refill = now
    end

    -- Refill tokens based on elapsed time
    local elapsed = now - last_refill
    if elapsed > 0 then
        tokens = math.min(capacity, tokens + elapsed * refill_rate)
        last_refill = now
    end

    local allowed = 0
    local retry_after = 0

    if tokens >= requested then
        tokens = tokens - requested
        allowed = 1
    else
        -- Calculate how long until one token is available
        local deficit = requested - tokens
        retry_after = math.ceil(deficit / refill_rate)
    end

    -- Persist state
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', last_refill)
    -- Set expiry to auto-clean stale buckets (2x window + buffer)
    redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) * 2 + 60)

    return {allowed, math.floor(tokens), retry_after}
    """

    def __init__(self, capacity: int, refill_rate: float, redis_client, key_prefix: str = "rl"):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._script = redis_client.register_script(self.LUA_SCRIPT)

    def _make_key(self, client_key: str, endpoint: str) -> str:
        return f"{self._key_prefix}:{client_key}:{endpoint}"

    def consume(self, client_key: str, endpoint: str, tokens: int = 1) -> tuple[bool, int, int]:
        """Try to consume tokens. Returns (allowed, remaining, retry_after_seconds)."""
        key = self._make_key(client_key, endpoint)
        now = time.time()
        result = self._script(
            keys=[key],
            args=[self.capacity, self.refill_rate, now, tokens],
        )
        allowed = bool(result[0])
        remaining = int(result[1])
        retry_after = int(result[2])
        return allowed, remaining, retry_after


# ---------------------------------------------------------------------------
# Redis connection helper
# ---------------------------------------------------------------------------

def _connect_redis(url: str):
    """Connect to Redis, returning None on failure with a warning."""
    try:
        import redis as redis_lib
        client = redis_lib.from_url(url, decode_responses=False, socket_connect_timeout=5, socket_timeout=5)
        client.ping()
        logger.info("Rate limiter connected to Redis at %s", url)
        return client
    except Exception as exc:
        logger.warning(
            "Redis connection failed (%s). Falling back to in-memory rate limiter.",
            exc,
        )
        return None


# ---------------------------------------------------------------------------
# Unified rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Rate limiter that uses Redis when available, falling back to in-memory."""

    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._endpoint_limits: dict[str, dict[str, tuple[int, int]]] = {
            "/health": {"default": (100, 60)},
            "/v1": {"default": (60, 60)},
            "/mcp": {"default": (30, 60)},
        }
        self._default_limit: tuple[int, int] = (30, 60)
        self._redis_client = None
        self._using_redis = False

        self._setup_backend()

    def _setup_backend(self) -> None:
        """Choose Redis or in-memory backend based on REDIS_URL."""
        redis_url = os.environ.get("REDIS_URL")
        if redis_url and self._connect_redis(redis_url) is not None:
            self._redis_client = _connect_redis(redis_url)
            self._using_redis = True
        else:
            logger.warning(
                "Rate limiter is in-memory only. Container restart resets all limits. "
                "Set REDIS_URL for Redis-backed rate limiting."
            )

    def _get_client_key(self, request: Request) -> str:
        """Extract client identifier from request."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
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
        """Get or create an in-memory token bucket (fallback)."""
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

        if self._using_redis and self._redis_client is not None:
            limits = self._endpoint_limits.get(endpoint_prefix, {})
            config = limits.get("default", self._default_limit)
            capacity, _ = config

            allowed, _unused, retry_after = RedisTokenBucket(
                capacity=capacity,
                refill_rate=capacity / 60,
                redis_client=self._redis_client,
            ).consume(client_key, endpoint_prefix)

            if not allowed:
                logger.warning(
                    "Rate limit exceeded (Redis): client=%s endpoint=%s path=%s",
                    client_key,
                    endpoint_prefix,
                    request.url.path,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please slow down your requests.",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            return None

        # In-memory fallback
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
    rate_enabled_env = os.environ.get("ESDATA_RATE_LIMIT_ENABLED")
    if rate_enabled_env is None and os.environ.get("APP_ENV", "").lower() == "test":
        rate_enabled = False
    else:
        rate_enabled = (rate_enabled_env or "true").lower() != "false"

    if rate_enabled:
        check = await _rate_limiter.check_rate_limit(request)
        if check:
            return check

    response = await call_next(request)

    # Add rate limit headers to successful responses
    client_key = _rate_limiter._get_client_key(request)
    endpoint_prefix = _rate_limiter._get_endpoint_prefix(request.url.path)

    if _rate_limiter._using_redis and _rate_limiter._redis_client is not None:
        limits = _rate_limiter._endpoint_limits.get(endpoint_prefix, {})
        config = limits.get("default", _rate_limiter._default_limit)
        capacity, _ = config
        _, remaining, _ = RedisTokenBucket(
            capacity=capacity,
            refill_rate=capacity / 60,
            redis_client=_rate_limiter._redis_client,
        ).consume(client_key, endpoint_prefix)
        response.headers["X-RateLimit-Limit"] = str(capacity)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
    else:
        bucket = _rate_limiter._get_bucket(client_key, endpoint_prefix)
        response.headers["X-RateLimit-Limit"] = str(bucket.capacity)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))

    return response
