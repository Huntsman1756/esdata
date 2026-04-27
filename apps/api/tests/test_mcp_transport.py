"""Regression coverage for MCP HTTP transport lifecycle."""

from __future__ import annotations

import pytest
from services.query_audit import QueryAuditService


async def _run_mcp_consulta_call(mcp_client, request_id: str):
    init_response = await mcp_client.post(
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
    assert session_id

    consulta_response = await mcp_client.post(
        "/mcp",
        headers={
            "Mcp-Session-Id": session_id,
            "x-request-id": request_id,
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
    assert consulta_response.headers.get("X-Request-ID") == request_id


@pytest.mark.asyncio
async def test_mcp_transport_first_request_persists_audit_row(mcp_client):
    await _run_mcp_consulta_call(mcp_client, "req-mcp-transport-001")

    entries = QueryAuditService().get_by_request_id("req-mcp-transport-001")
    assert len(entries) == 1


@pytest.mark.asyncio
async def test_mcp_transport_second_request_also_persists_audit_row(mcp_client):
    await _run_mcp_consulta_call(mcp_client, "req-mcp-transport-002")

    entries = QueryAuditService().get_by_request_id("req-mcp-transport-002")
    assert len(entries) == 1
