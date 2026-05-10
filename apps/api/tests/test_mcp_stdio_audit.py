"""Audit coverage for MCP stdio transport (Fase 1.2)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import anyio

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _get_stdio_and_audit_deps():
    from mcp_stdio import MCPStdioServer
    from services.query_audit import QueryAuditService, reset_query_audit_service

    return MCPStdioServer, QueryAuditService, reset_query_audit_service


def setup_function() -> None:
    _, _, reset_query_audit_service = _get_stdio_and_audit_deps()
    reset_query_audit_service()


def teardown_function() -> None:
    _, _, reset_query_audit_service = _get_stdio_and_audit_deps()
    reset_query_audit_service()


def _invoke_stdio_tool(tool_name: str, arguments: dict) -> dict:
    MCPStdioServer, _, _ = _get_stdio_and_audit_deps()
    server = MCPStdioServer()
    sent: list[dict] = []
    server._send = lambda data: sent.append(data)
    anyio.run(
        server._handle_tools_call,
        {
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
        1,
    )
    assert len(sent) == 1
    return sent[0]


def _entry_by_path(entries: list, path: str):
    return next(entry for entry in entries if entry.path == path)


def test_stdio_consulta_persists_correlated_audit_entries_with_real_request_id() -> None:
    _, QueryAuditService, _ = _get_stdio_and_audit_deps()
    payload = _invoke_stdio_tool("consulta_fiscal", {"q": "tipo reducido iva"})

    assert "result" in payload

    entries = QueryAuditService().get_entries()
    assert len(entries) == 2

    http_entry = _entry_by_path(entries, "/v1/consulta")
    stdio_entry = _entry_by_path(entries, "/mcp/tools/consulta_fiscal")

    assert stdio_entry.request_id == http_entry.request_id
    assert stdio_entry.request_id not in {"", "unknown"}
    assert stdio_entry.user_id == http_entry.user_id == "mcp-client"
    assert stdio_entry.tool_name == "consulta_fiscal"
    assert '"q": "tipo reducido iva"' in stdio_entry.query_text
    assert stdio_entry.retrieved_chunks == http_entry.retrieved_chunks
    assert stdio_entry.sources == http_entry.sources
    assert stdio_entry.confidence == http_entry.confidence
    assert stdio_entry.completeness == http_entry.completeness
    assert stdio_entry.verified == http_entry.verified
    assert stdio_entry.response_summary.startswith("Consulta: tipo reducido iva")
    if http_entry.response_payload:
        assert http_entry.response_payload["consulta"] == "tipo reducido iva"
    assert stdio_entry.response_payload["result"]["structuredContent"]["consulta"] == "tipo reducido iva"
    assert stdio_entry.response_payload["result"]["content"][0]["type"] == "text"


def test_stdio_agente_consulta_keeps_agent_tool_name_while_correlating_request_id() -> None:
    _, QueryAuditService, _ = _get_stdio_and_audit_deps()
    payload = _invoke_stdio_tool(
        "agente_consulta",
        {"q": "tipo reducido iva", "tipo_entidad": "sociedad_valores"},
    )

    assert "result" in payload

    entries = QueryAuditService().get_entries()
    assert len(entries) == 2

    http_entry = _entry_by_path(entries, "/v1/consulta")
    stdio_entry = _entry_by_path(entries, "/mcp/tools/agente_consulta")

    assert stdio_entry.request_id == http_entry.request_id
    assert stdio_entry.request_id not in {"", "unknown"}
    assert http_entry.tool_name == "consulta_fiscal"
    assert stdio_entry.tool_name == "agente_consulta"
    assert stdio_entry.user_id == http_entry.user_id == "mcp-client"
    assert '"tipo_entidad": "sociedad_valores"' in stdio_entry.query_text


def test_stdio_returns_jsonrpc_error_when_audit_persistence_breaks() -> None:
    MCPStdioServer, _, _ = _get_stdio_and_audit_deps()
    server = MCPStdioServer()
    sent: list[dict] = []
    server._send = lambda data: sent.append(data)

    with patch("mcp_stdio._log_mcp_call", side_effect=RuntimeError("audit offline")):
        anyio.run(
            server._handle_tools_call,
            {
                "id": 1,
                "method": "tools/call",
                "params": {"name": "consulta_fiscal", "arguments": {"q": "tipo reducido iva"}},
            },
            1,
        )

    assert len(sent) == 1
    assert sent[0]["id"] == 1
    assert "error" in sent[0]
    assert sent[0]["error"]["code"] == -32603
    assert "audit" in sent[0]["error"]["message"].lower()
