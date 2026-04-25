"""Unit tests for rate_limit middleware (TokenBucket + RateLimiter logic)."""

from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from middleware.rate_limit import TokenBucket, RateLimiter


class TestTokenBucket:
    """Verify token bucket algorithm behavior."""

    def test_initial_capacity(self):
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.tokens == 10
        assert bucket.capacity == 10

    def test_consume_success(self):
        bucket = TokenBucket(capacity=10, refill_rate=0.0)
        assert bucket.consume() is True
        assert bucket.tokens < 10

    def test_consume_exhausts(self):
        bucket = TokenBucket(capacity=3, refill_rate=0.0)
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is False

    def test_consume_multiple_tokens(self):
        bucket = TokenBucket(capacity=10, refill_rate=0.0)
        assert bucket.consume(5) is True
        assert bucket.consume(6) is False
        assert bucket.consume(5) is True

    def test_refill_over_time(self):
        bucket = TokenBucket(capacity=10, refill_rate=100.0)
        bucket.consume(10)
        assert bucket.tokens < 1
        # Mock monotonic to simulate time passing
        original = time.monotonic
        time.monotonic = lambda: original() + 0.1
        try:
            bucket._refill()
            assert bucket.tokens > 0
        finally:
            time.monotonic = original

    def test_refill_does_not_exceed_capacity(self):
        bucket = TokenBucket(capacity=10, refill_rate=1000.0)
        time.sleep(0.05)  # Would refill way more than capacity
        assert bucket.tokens <= 10


class TestRateLimiter:
    """Verify RateLimiter endpoint detection and client key extraction."""

    def test_health_endpoint_prefix(self):
        limiter = RateLimiter()
        assert limiter._get_endpoint_prefix("/health") == "/health"
        assert limiter._get_endpoint_prefix("/health/") == "/health"

    def test_v1_endpoint_prefix(self):
        limiter = RateLimiter()
        assert limiter._get_endpoint_prefix("/v1/cambios") == "/v1"
        assert limiter._get_endpoint_prefix("/v1/compliance/workflow") == "/v1"

    def test_mcp_endpoint_prefix(self):
        limiter = RateLimiter()
        assert limiter._get_endpoint_prefix("/mcp") == "/mcp"
        assert limiter._get_endpoint_prefix("/mcp/tools") == "/mcp"

    def test_default_endpoint_prefix(self):
        limiter = RateLimiter()
        assert limiter._get_endpoint_prefix("/unknown") == "default"
        assert limiter._get_endpoint_prefix("/") == "default"

    def test_client_key_from_forwarded_for(self):
        limiter = RateLimiter()
        from unittest.mock import MagicMock
        request = MagicMock()
        request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        request.client = None
        assert limiter._get_client_key(request) == "1.2.3.4"

    def test_client_key_from_real_ip(self):
        limiter = RateLimiter()
        from unittest.mock import MagicMock
        request = MagicMock()
        request.headers = {"x-real-ip": "10.0.0.1"}
        request.client = None
        assert limiter._get_client_key(request) == "10.0.0.1"

    def test_client_key_falls_back_to_host(self):
        limiter = RateLimiter()
        from unittest.mock import MagicMock
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"
        assert limiter._get_client_key(request) == "192.168.1.1"

    def test_client_key_unknown_when_no_info(self):
        limiter = RateLimiter()
        from unittest.mock import MagicMock
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert limiter._get_client_key(request) == "unknown"

    def test_default_limits_config(self):
        limiter = RateLimiter()
        assert limiter._endpoint_limits["/health"] == {"default": (100, 60)}
        assert limiter._endpoint_limits["/v1"] == {"default": (60, 60)}
        assert limiter._endpoint_limits["/mcp"] == {"default": (30, 60)}
        assert limiter._default_limit == (30, 60)

    def test_buckets_are_per_client_and_endpoint(self):
        limiter = RateLimiter()
        from unittest.mock import MagicMock
        req1 = MagicMock()
        req1.url.path = "/v1/cambios"
        req1.headers = {}
        req1.client = MagicMock()
        req1.client.host = "1.1.1.1"

        req2 = MagicMock()
        req2.url.path = "/v1/cambios"
        req2.headers = {}
        req2.client = MagicMock()
        req2.client.host = "2.2.2.2"

        bucket1 = limiter._get_bucket("1.1.1.1", "/v1")
        bucket2 = limiter._get_bucket("2.2.2.2", "/v1")
        assert bucket1 is not bucket2

    def test_bucket_reuse_same_client_endpoint(self):
        limiter = RateLimiter()
        bucket1 = limiter._get_bucket("1.1.1.1", "/v1")
        bucket2 = limiter._get_bucket("1.1.1.1", "/v1")
        assert bucket1 is bucket2
