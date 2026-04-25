"""Tests for Fase 8 security middleware: rate limiting, security headers, CORS, API key auth."""

import os
from pathlib import Path
import sys
import importlib

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
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert r.status_code == 200
    assert "access-control-allow-origin" in r.headers


@pytest.mark.asyncio
async def test_rate_limiting_active_on_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health")

    assert r.status_code == 200
    assert "x-ratelimit-limit" in r.headers
    assert "x-ratelimit-remaining" in r.headers


@pytest.mark.asyncio
async def test_rate_limiting_active_on_v1():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios")

    assert r.status_code == 200
    assert "x-ratelimit-limit" in r.headers


@pytest.mark.asyncio
async def test_rate_limiting_active_on_mcp():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/mcp")

    assert "x-ratelimit-limit" in r.headers


@pytest.mark.asyncio
async def test_auth_disabled_allows_all_requests():
    """When auth is disabled (default), all endpoints return 200 (or their normal response)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios")

    assert r.status_code == 200


@pytest.mark.asyncio
async def test_auth_disabled_no_api_key_required():
    """When auth is disabled, requests without X-API-Key succeed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/compliance/workflow")

    assert r.status_code == 200


@pytest.mark.asyncio
async def test_health_is_public_path():
    """Health endpoint should always work, even with auth enabled."""
    original = dict(os.environ)
    os.environ["ESDATA_AUTH_ENABLED"] = "true"
    os.environ["ESDATA_API_KEY"] = "test-secret-key"
    try:
        import importlib
        import middleware.api_key_auth as auth_module
        importlib.reload(auth_module)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/health")

        assert r.status_code == 200
    finally:
        os.environ.clear()
        os.environ.update(original)
