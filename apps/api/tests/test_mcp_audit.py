"""End-to-end MCP audit verification for canonical HTTP MCP flow."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from services.query_audit import QueryAuditService, reset_query_audit_service
from _mcp_http_transport_harness import run_http_mcp_tool_call


def setup_function():
    reset_query_audit_service()


def teardown_function():
    reset_query_audit_service()


def test_mcp_get_norma_persists_audit_entry_with_request_id_correlation():
    handshake, initialize, tool_call = run_http_mcp_tool_call(
        tool_name="get_norma",
        arguments={"codigo": "LIVA"},
        request_id="req-mcp-audit-001",
        user_id="internal-mcp-user",
    )

    assert handshake.status_code in {200, 400}
    assert initialize.status_code == 200
    assert tool_call.status_code == 200
    assert tool_call.headers.get("X-Request-ID") == "req-mcp-audit-001"

    service = QueryAuditService()
    entries = service.get_entries()

    assert len(entries) == 1
    entry = entries[0]
    assert entry.request_id == "req-mcp-audit-001"
    assert entry.path == "/v1/legislacion/LIVA"
    assert entry.tool_name == "get_norma"
    assert entry.user_id == "internal-mcp-user"
    assert entry.query_text == "LIVA"
    assert entry.response_summary == "norma=LIVA"
    assert isinstance(entry.sources, list)
    assert isinstance(entry.confidence, dict)
