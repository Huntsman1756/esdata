"""Pending contract tests for MCP 2026-07-28 stateless HTTP compatibility.

These tests intentionally xfail until ESData implements a dual-stack stateless
MCP route. They protect the current decision: keep /mcp legacy intact and add
2026-07-28 support as an explicit transport/versioning block.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

pytestmark = pytest.mark.xfail(
    reason="MCP 2026-07-28 stateless transport is audited but not implemented yet",
    strict=True,
)


CLIENT = TestClient(app)
STATELESS_URL = "/mcp/stateless"
MCP_HEADERS = {
    "X-API-Key": "test-mcp-key",
    "MCP-Protocol-Version": "2026-07-28",
}


def _meta() -> dict:
    return {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientInfo": {
            "name": "esdata-contract-test",
            "version": "0.0.0",
        },
        "io.modelcontextprotocol/clientCapabilities": {
            "extensions": {},
        },
    }


def test_mcp_20260728_server_discover_is_stateless_and_does_not_issue_session_id():
    response = CLIENT.post(
        STATELESS_URL,
        headers={
            **MCP_HEADERS,
            "Mcp-Method": "server/discover",
            "Mcp-Name": "server/discover",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "server/discover",
            "params": {"_meta": _meta()},
        },
    )

    assert response.status_code == 200
    assert "mcp-session-id" not in {key.lower() for key in response.headers}
    result = response.json()["result"]
    assert "2026-07-28" in result["protocolVersions"]
    assert result["serverInfo"]["name"]


def test_mcp_20260728_tools_list_requires_no_handshake_and_returns_cache_metadata():
    response = CLIENT.post(
        STATELESS_URL,
        headers={
            **MCP_HEADERS,
            "Mcp-Method": "tools/list",
            "Mcp-Name": "tools/list",
        },
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {"_meta": _meta()},
        },
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert isinstance(result["tools"], list)
    assert isinstance(result["ttlMs"], int)
    assert result["ttlMs"] > 0
    assert result["cacheScope"] in {"public", "private"}


def test_mcp_20260728_tools_call_is_self_contained_and_rejects_session_header():
    response = CLIENT.post(
        STATELESS_URL,
        headers={
            **MCP_HEADERS,
            "Mcp-Method": "tools/call",
            "Mcp-Name": "buscar",
            "Mcp-Session-Id": "legacy-session-must-not-be-used",
        },
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "buscar",
                "arguments": {"q": "modelo 303"},
                "_meta": _meta()
                | {
                    "traceparent": "00-00000000000000000000000000000001-0000000000000001-01",
                    "tracestate": "esdata=test",
                    "baggage": "request.kind=mcp-contract",
                },
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32600
    assert "Mcp-Session-Id" in response.json()["error"]["message"]


def test_mcp_20260728_rejects_header_body_method_mismatch():
    response = CLIENT.post(
        STATELESS_URL,
        headers={
            **MCP_HEADERS,
            "Mcp-Method": "tools/list",
            "Mcp-Name": "tools/list",
        },
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "buscar",
                "arguments": {"q": "modelo 303"},
                "_meta": _meta(),
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32600
    assert "Mcp-Method" in response.json()["error"]["message"]


def test_mcp_20260728_rejects_missing_protocol_version():
    response = CLIENT.post(
        STATELESS_URL,
        headers={
            "X-API-Key": "test-mcp-key",
            "Mcp-Method": "tools/list",
            "Mcp-Name": "tools/list",
        },
        json={
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/list",
            "params": {"_meta": _meta()},
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32000
    assert "UnsupportedProtocolVersionError" in response.json()["error"]["message"]
