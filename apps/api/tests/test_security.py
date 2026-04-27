"""Tests for Fase 8/Fase 30 security middleware."""

import importlib
import os
from pathlib import Path
import sys

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


@pytest.mark.asyncio
async def test_security_headers_present():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health")

    assert r.status_code == 200
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-xss-protection"] == "0"
    assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "permissions-policy" in r.headers
    assert "x-request-id" in r.headers


@pytest.mark.asyncio
async def test_security_headers_include_request_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health")

    request_id = r.headers["x-request-id"]
    assert len(request_id) == 8  # truncated UUID hex


@pytest.mark.asyncio
async def test_security_headers_preserve_incoming_request_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers={"x-request-id": "my-custom-id-12345"})

    assert r.headers["x-request-id"] == "my-custom-id-12345"


@pytest.mark.asyncio
async def test_cors_preflight_works():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.options(
            "/health",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert r.status_code == 200
    assert "access-control-allow-origin" in r.headers


@pytest.mark.asyncio
async def test_rate_limiting_active_on_health():
    os.environ["ESDATA_RATE_LIMIT_ENABLED"] = "true"
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/health")

        assert r.status_code == 200
        assert "x-ratelimit-limit" in r.headers
        assert "x-ratelimit-remaining" in r.headers
    finally:
        os.environ["ESDATA_RATE_LIMIT_ENABLED"] = "false"


@pytest.mark.asyncio
async def test_rate_limiting_active_on_v1():
    os.environ["ESDATA_RATE_LIMIT_ENABLED"] = "true"
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/v1/cambios", headers={"x-api-key": "test-secret-key"})

        assert r.status_code == 200
        assert "x-ratelimit-limit" in r.headers
    finally:
        os.environ["ESDATA_RATE_LIMIT_ENABLED"] = "false"


@pytest.mark.asyncio
async def test_rate_limiting_active_on_mcp():
    os.environ["ESDATA_RATE_LIMIT_ENABLED"] = "true"
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/mcp", headers={"x-api-key": "test-mcp-key"})

        assert r.status_code != 401
        assert r.status_code != 429
        assert "x-ratelimit-limit" in r.headers
    finally:
        os.environ["ESDATA_RATE_LIMIT_ENABLED"] = "false"


@pytest.mark.asyncio
async def test_protected_v1_path_requires_api_key_by_default():
    """Protected routes must fail closed when no API key is provided."""
    original = dict(os.environ)
    os.environ["APP_ENV"] = "test"
    os.environ.pop("ESDATA_ALLOW_INSECURE_TEST_AUTH", None)
    os.environ["ESDATA_API_KEY"] = "test-secret-key"
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/v1/cambios")

        assert r.status_code == 401
    finally:
        os.environ.clear()
        os.environ.update(original)


@pytest.mark.asyncio
async def test_protected_v1_path_accepts_valid_api_key():
    """Protected routes should work when a valid API key is provided."""
    original = dict(os.environ)
    os.environ["APP_ENV"] = "test"
    os.environ["ESDATA_API_KEY"] = "test-secret-key"
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/v1/cambios", headers={"x-api-key": "test-secret-key"})

        assert r.status_code == 200
    finally:
        os.environ.clear()
        os.environ.update(original)


@pytest.mark.asyncio
async def test_health_is_public_path():
    """Health endpoint should always work, even with auth enabled."""
    original = dict(os.environ)
    os.environ["APP_ENV"] = "test"
    os.environ["ESDATA_API_KEY"] = "test-secret-key"
    os.environ["MCP_API_KEY"] = "mcp-test-key"
    try:
        import middleware.api_key_auth as auth_module
        importlib.reload(auth_module)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/health")

        assert r.status_code == 200
    finally:
        os.environ.clear()
        os.environ.update(original)


@pytest.mark.asyncio
async def test_rate_limit_rejects_before_executing_handler(monkeypatch):
    """A rate-limited request must not execute the protected handler."""
    from middleware.rate_limit import _rate_limiter, rate_limit_middleware

    hits = {"count": 0}
    protected_app = FastAPI()
    protected_app.middleware("http")(rate_limit_middleware)

    @protected_app.get("/v1/protected")
    async def protected_endpoint():
        hits["count"] += 1
        return {"ok": True}

    original_limits = dict(_rate_limiter._endpoint_limits)
    _rate_limiter._buckets.clear()
    monkeypatch.setenv("ESDATA_RATE_LIMIT_ENABLED", "true")
    _rate_limiter._endpoint_limits["/v1"] = {"default": (1, 60)}

    try:
        transport = ASGITransport(app=protected_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            first = await c.get("/v1/protected")
            second = await c.get("/v1/protected")

        assert first.status_code == 200
        assert second.status_code == 429
        assert hits["count"] == 1
    finally:
        _rate_limiter._endpoint_limits = original_limits
        _rate_limiter._buckets.clear()


def test_main_fails_to_import_when_api_key_missing_under_normal_runtime(monkeypatch):
    """Main app import must fail if runtime is configured without required API key."""
    original = dict(os.environ)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ESDATA_API_KEY", raising=False)
    monkeypatch.setenv("MCP_API_KEY", "mcp-test-key")

    try:
        sys.modules.pop("main", None)
        with pytest.raises(RuntimeError):
            import main as main_module
            importlib.reload(main_module)
    finally:
        sys.modules.pop("main", None)
        os.environ.clear()
        os.environ.update(original)
