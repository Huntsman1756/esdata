"""Contract tests for MCP transport invariants."""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _get_app_and_audit_service():
    from main import app
    from services.query_audit import QueryAuditService, reset_query_audit_service

    return app, QueryAuditService, reset_query_audit_service


def setup_function() -> None:
    _, _, reset_query_audit_service = _get_app_and_audit_service()
    reset_query_audit_service()


def teardown_function() -> None:
    _, _, reset_query_audit_service = _get_app_and_audit_service()
    reset_query_audit_service()


@pytest.mark.asyncio
async def test_mcp_transport_preserves_request_id_header():
    app, query_audit_service_cls, _ = _get_app_and_audit_service()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/mcp",
            headers={"x-api-key": "test-mcp-key", "x-request-id": "req-mcp-contract-001"},
        )

    assert response.status_code == 406
    assert response.headers["x-request-id"] == "req-mcp-contract-001"
    assert query_audit_service_cls().get_by_request_id("req-mcp-contract-001") == []
