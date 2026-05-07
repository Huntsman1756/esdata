"""Regression coverage for MCP HTTP transport lifecycle."""

from __future__ import annotations

from _mcp_http_transport_harness import run_http_mcp_tool_call


def test_mcp_transport_first_request_preserves_request_id_header():
    handshake, initialize, tool_call = run_http_mcp_tool_call(
        tool_name="list_modelos",
        arguments={},
        request_id="req-mcp-transport-001",
    )

    assert handshake.status_code in {200, 400}
    assert initialize.status_code == 200
    assert tool_call.status_code == 200
    assert tool_call.headers.get("X-Request-ID") == "req-mcp-transport-001"
    payload = tool_call.json()
    assert payload.get("result")
    assert payload["result"].get("isError") is not True


def test_mcp_transport_second_request_also_preserves_request_id_header():
    handshake, initialize, tool_call = run_http_mcp_tool_call(
        tool_name="list_modelos",
        arguments={},
        request_id="req-mcp-transport-002",
    )

    assert handshake.status_code in {200, 400}
    assert initialize.status_code == 200
    assert tool_call.status_code == 200
    assert tool_call.headers.get("X-Request-ID") == "req-mcp-transport-002"
    payload = tool_call.json()
    assert payload.get("result")
    assert payload["result"].get("isError") is not True
