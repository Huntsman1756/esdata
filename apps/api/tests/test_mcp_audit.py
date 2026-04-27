"""End-to-end MCP audit verification for internal consulta flow."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from main import app
from services.query_audit import QueryAuditService, reset_query_audit_service


def setup_function():
    reset_query_audit_service()


def teardown_function():
    reset_query_audit_service()


@pytest.mark.asyncio
async def test_mcp_consulta_persists_audit_entry_with_request_id_correlation():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-mcp-key",
            "accept": "application/json",
            "content-type": "application/json",
        },
    ) as client:
        init_response = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1.0"},
                },
            },
        )

        assert init_response.status_code == 200
        session_id = init_response.headers.get("Mcp-Session-Id")
        assert session_id, "MCP initialize must return a session id"

        consulta_response = await client.post(
            "/mcp",
            headers={
                "Mcp-Session-Id": session_id,
                "x-request-id": "req-mcp-audit-001",
                "x-user-id": "internal-mcp-user",
            },
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "consulta_fiscal",
                    "arguments": {"q": "tipo reducido iva"},
                },
            },
        )

    assert consulta_response.status_code == 200
    assert consulta_response.headers.get("X-Request-ID") == "req-mcp-audit-001"

    service = QueryAuditService()
    entries = service.get_by_request_id("req-mcp-audit-001")

    assert len(entries) == 1
    entry = entries[0]
    assert entry.path == "/v1/consulta"
    assert entry.user_id == "internal-mcp-user"
    assert "tipo reducido iva" in entry.query_text.lower()
    assert entry.model_version == "esdata-ai-v1"
    assert entry.config_version == "consulta-faithfulness-v1"
    assert entry.response_summary
