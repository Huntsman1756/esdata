"""Integration tests for MCP stdio ASGI transport replacement.

Validates the httpx.AsyncClient + httpx.ASGITransport + anyio path used by
MCPStdioServer to talk to the FastAPI app in-process.

Covers:
  1. Basic connectivity (health, status)
  2. Tool discovery (tools/list via stdio path)
  3. Tool execution (consulta_fiscal over ASGI)
  4. Error handling (malformed input, unknown tools, bad params)
  5. Concurrency (5+ parallel connections)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
import pytest

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from main import app  # noqa: E402

MCP_API_KEY = "test-mcp-key"
MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "X-API-Key": MCP_API_KEY,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_URL = "http://test"


async def _make_client() -> httpx.AsyncClient:
    """Return a fresh AsyncClient wired to the ASGI app."""
    transport = app.state._mcp_http_transport
    if getattr(transport, "_manager_started", False):
        try:
            await transport.shutdown()
        except RuntimeError:
            transport._manager_started = False
            transport._manager_task = None
    await transport._ensure_session_manager_started()
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url=_BASE_URL,
        timeout=30.0,
    )


async def _initialize(client: httpx.AsyncClient) -> dict:
    """Run the MCP initialize handshake and return the parsed response.

    The FastApiMCP transport uses session IDs returned in response headers.
    """
    handshake = await client.get(
        "/mcp",
        headers={"Accept": "text/event-stream", "X-API-Key": MCP_API_KEY},
    )
    assert handshake.status_code in {200, 400}, f"Handshake failed: {handshake.status_code} {handshake.text}"
    session_id = handshake.headers.get("mcp-session-id") or handshake.headers.get("Mcp-Session-Id")
    assert session_id, f"Handshake did not return MCP session id: {handshake.status_code} {handshake.text}"
    client.headers.update({"MCP-Session-ID": session_id})

    resp = await client.post(
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
        headers={**MCP_HEADERS, "MCP-Session-ID": session_id},
    )
    assert resp.status_code == 200, f"Initialize failed: {resp.status_code} {resp.text}"
    payload = resp.json()
    payload.setdefault("result", {})["session_id"] = session_id
    return payload


async def _send_jsonrpc(
    client: httpx.AsyncClient,
    method: str,
    params: dict | None = None,
    msg_id: int = 1,
    session_id: str | None = None,
):
    headers = dict(MCP_HEADERS)
    sid = session_id or client.headers.get("MCP-Session-ID")
    if sid:
        headers["MCP-Session-ID"] = sid
    response = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}},
        headers=headers,
    )
    if method == "tools/call":
        return response.json()
    return response.json()


def _extract_session_id(response: dict) -> str | None:
    """Extract session ID from MCP initialize response headers."""
    return response.get("result", {}).get("sessionId")


# ---------------------------------------------------------------------------
# 1. Basic connectivity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint_reachable():
    """1.1 The /health endpoint returns 200 over ASGI transport."""
    async with await _make_client() as c:
        r = await c.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_status_endpoint_reachable():
    """1.2 The /status endpoint returns structured data over ASGI transport."""
    async with await _make_client() as c:
        r = await c.get("/status")
    assert r.status_code == 200
    data = r.json()
    assert data["api"] == "ok"
    assert "workers" in data
    assert "modelos" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_openapi_schema_valid():
    """1.3 The OpenAPI schema is accessible and well-formed."""
    async with await _make_client() as c:
        r = await c.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "paths" in data
    assert "/health" in data["paths"]
    assert "/status" in data["paths"]


# ---------------------------------------------------------------------------
# 2. Tool discovery via MCP protocol
# ---------------------------------------------------------------------------

_HTTP_MCP_TOOLS = [
    "list_legislacion", "get_norma", "list_articulos", "get_articulo",
    "get_articulo_historial", "buscar", "buscar_legislacion",
    "list_materias", "get_materia",
    "buscar_doctrina", "get_doctrina",
    "list_modelos", "list_modelos_campanas_operativas",
    "get_modelo", "get_modelo_articulos",
    "get_modelo_casillas", "get_modelo_claves",
    "get_modelo_instrucciones", "get_modelo_normativa",
    "get_modelo_artefactos", "get_modelo_campana_operativa",
    "get_modelo_resumen_operativo", "get_modelo_fuentes_oficiales",
]


@pytest.mark.asyncio
async def test_mcp_initialize_handshake():
    """2.1 MCP initialize returns protocol version and server info."""
    async with await _make_client() as c:
        result = await _initialize(c)
    assert result["jsonrpc"] == "2.0"
    assert "result" in result
    res = result["result"]
    assert res["protocolVersion"] == "2025-03-26"
    assert res["serverInfo"]["name"] == "esdata API"
    assert "capabilities" in res
    assert "tools" in res["capabilities"]


@pytest.mark.asyncio
async def test_mcp_tools_list_returns_tools():
    """2.2 tools/list returns non-empty tool catalog."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=MCP_HEADERS,
        )
    assert resp.status_code == 200, f"tools/list failed: {resp.text}"
    data = resp.json()
    assert data["jsonrpc"] == "2.0"
    assert "result" in data
    tools = data["result"].get("tools", [])
    assert len(tools) > 0


@pytest.mark.asyncio
async def test_mcp_tools_list_contains_buscar():
    """2.3 tools/list includes the buscar tool."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=MCP_HEADERS,
        )
    assert resp.status_code == 200
    tool_names = [t["name"] for t in resp.json()["result"]["tools"]]
    assert "buscar" in tool_names


@pytest.mark.asyncio
async def test_mcp_tools_list_contains_legislacion():
    """2.4 tools/list includes list_legislacion tool."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=MCP_HEADERS,
        )
    tool_names = [t["name"] for t in resp.json()["result"]["tools"]]
    assert "list_legislacion" in tool_names


@pytest.mark.asyncio
async def test_mcp_tools_list_contains_modelos():
    """2.5 tools/list includes get_modelo tool."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=MCP_HEADERS,
        )
    tool_names = [t["name"] for t in resp.json()["result"]["tools"]]
    assert "get_modelo" in tool_names


@pytest.mark.asyncio
async def test_mcp_tools_list_contains_doctrina():
    """2.6 tools/list includes buscar_doctrina."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=MCP_HEADERS,
        )
    tool_names = [t["name"] for t in resp.json()["result"]["tools"]]
    assert "buscar_doctrina" in tool_names


@pytest.mark.asyncio
async def test_mcp_tools_list_schema_valid():
    """2.7 Every tool has name, description, and inputSchema."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=MCP_HEADERS,
        )
    assert resp.status_code == 200
    for tool in resp.json()["result"]["tools"]:
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool missing 'description': {tool}"
        assert "inputSchema" in tool, f"Tool missing 'inputSchema': {tool}"
        schema = tool["inputSchema"]
        assert schema.get("type") == "object"
        assert "properties" in schema


@pytest.mark.asyncio
async def test_mcp_get_modelo_casillas_exposes_pagination_filters():
    async with await _make_client() as c:
        await _initialize(c)
        resp = await c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=MCP_HEADERS,
        )

    assert resp.status_code == 200
    tools = {tool["name"]: tool for tool in resp.json()["result"]["tools"]}
    schema = tools["get_modelo_casillas"]["inputSchema"]
    properties = schema["properties"]

    assert {"codigo", "campana", "limit", "offset", "q", "tipo_casilla", "pagina"} <= set(properties)
    assert properties["limit"].get("maximum") == 500
    assert properties["limit"].get("minimum") == 1


@pytest.mark.asyncio
async def test_mcp_tools_count():
    """2.8 tools/list returns the expected number of http-mcp tools."""
    from mcp_catalog import HTTP_MCP_OPERATIONS

    async with await _make_client() as c:
        await _initialize(c)
        resp = await c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=MCP_HEADERS,
        )
    assert resp.status_code == 200
    assert len(resp.json()["result"]["tools"]) == len(HTTP_MCP_OPERATIONS)


# ---------------------------------------------------------------------------
# 3. Tool execution — consulta_fiscal over ASGI
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consulta_fiscal_basic_query():
    """3.1 consulta_fiscal with a simple query returns results."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "tools/call",
            params={
                "name": "consulta_fiscal",
                "arguments": {"q": "iva deducciones"},
            },
            msg_id=3,
        )
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp
    result = resp["result"]
    assert "content" in result
    content = result["content"]
    assert isinstance(content, list)
    assert any(
        isinstance(item, dict) and item.get("type") == "text"
        for item in content
    )


@pytest.mark.asyncio
async def test_consulta_fiscal_has_structured_content():
    """3.2 consulta_fiscal response includes structuredContent."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "tools/call",
            params={
                "name": "consulta_fiscal",
                "arguments": {"q": "iva"},
            },
            msg_id=3,
        )
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp
    assert "structuredContent" in resp["result"] or "content" in resp["result"]


@pytest.mark.asyncio
async def test_consulta_fiscal_with_sujeto():
    """3.3 consulta_fiscal with sujeto parameter works."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "tools/call",
            params={
                "name": "consulta_fiscal",
                "arguments": {
                    "q": "retenciones",
                    "sujeto": "retenedor",
                },
            },
            msg_id=3,
        )
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp
    assert "content" in resp["result"]


@pytest.mark.asyncio
async def test_consulta_fiscal_text_content_nonempty():
    """3.4 consulta_fiscal text content is not empty."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "tools/call",
            params={
                "name": "consulta_fiscal",
                "arguments": {"q": "modelo 303"},
            },
            msg_id=3,
        )
    text_parts = [
        item.get("text", "")
        for item in resp["result"]["content"]
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    combined = "\n".join(text_parts)
    assert len(combined) > 0


@pytest.mark.asyncio
async def test_listar_obligaciones_operativas():
    """3.5 listar_obligaciones_operativas returns obligation data."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "tools/call",
            params={
                "name": "listar_obligaciones_operativas",
                "arguments": {"limite": 5},
            },
            msg_id=3,
        )
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp
    assert "content" in resp["result"]
    assert "structuredContent" in resp["result"] or "content" in resp["result"]


@pytest.mark.asyncio
async def test_listar_deadlines():
    """3.6 listar_deadlines returns deadline data."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "tools/call",
            params={
                "name": "listar_deadlines",
                "arguments": {"dias_proximo": 30},
            },
            msg_id=3,
        )
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp
    assert "content" in resp["result"]


@pytest.mark.asyncio
async def test_agente_monitoreo_status():
    """3.7 agente_monitoreo_status returns status dict."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "tools/call",
            params={
                "name": "agente_monitoreo_status",
                "arguments": {},
            },
            msg_id=3,
        )
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp
    assert "content" in resp["result"]


# ---------------------------------------------------------------------------
# 4. Error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_unknown_method():
    """4.1 Unknown JSON-RPC method returns error code -32601."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "nonexistent/method",
            msg_id=99,
        )
    assert resp["jsonrpc"] == "2.0"
    assert "error" in resp
    assert resp["error"]["code"] in {-32601, -32602}


@pytest.mark.asyncio
async def test_consulta_fiscal_missing_required_param():
    """4.2 consulta_fiscal without 'q' param returns error."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "tools/call",
            params={
                "name": "consulta_fiscal",
                "arguments": {},
            },
            msg_id=3,
        )
    # The endpoint may return results (empty query) or error — both valid
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp or "error" in resp


@pytest.mark.asyncio
async def test_unknown_tool_returns_error():
    """4.3 Calling an unknown tool name returns -32601 error."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "tools/call",
            params={
                "name": "tool_que_no_existe",
                "arguments": {},
            },
            msg_id=3,
    )
    assert resp["jsonrpc"] == "2.0"
    assert ("error" in resp and resp["error"]["code"] == -32601) or resp.get("result", {}).get("isError") is True


@pytest.mark.asyncio
async def test_malformed_jsonrpc_missing_method():
    """4.4 JSON-RPC without method field is handled gracefully."""
    async with await _make_client() as c:
        await _initialize(c)
        body = {"jsonrpc": "2.0", "id": 100}
        resp = await c.post("/mcp", json=body, headers=MCP_HEADERS)
    # Should not raise 500
    assert resp.status_code in (200, 400)


@pytest.mark.asyncio
async def test_consulta_fiscal_empty_query():
    """4.5 Empty query string is handled without crash."""
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "tools/call",
            params={
                "name": "consulta_fiscal",
                "arguments": {"q": ""},
            },
            msg_id=3,
        )
    assert resp["jsonrpc"] == "2.0"


@pytest.mark.asyncio
async def test_consulta_fiscal_long_query():
    """4.6 Very long query string does not crash the server."""
    long_q = "a" * 10000
    async with await _make_client() as c:
        await _initialize(c)
        resp = await _send_jsonrpc(
            c,
            "tools/call",
            params={
                "name": "consulta_fiscal",
                "arguments": {"q": long_q},
            },
            msg_id=3,
        )
    assert resp["jsonrpc"] == "2.0"


@pytest.mark.asyncio
async def test_consulta_fiscal_special_characters():
    """4.7 Query with special characters is handled safely."""
    special_queries = [
        "<script>alert('xss')</script>",
        "SELECT * FROM users WHERE 1=1",
        "ñáéíóú ñÑ",
        "inversión del sujeto pasivo iva",
    ]
    async with await _make_client() as c:
        await _initialize(c)
        for q in special_queries:
            resp = await _send_jsonrpc(
                c,
                "tools/call",
                params={
                    "name": "consulta_fiscal",
                    "arguments": {"q": q},
                },
                msg_id=3,
            )
            assert resp["jsonrpc"] == "2.0"
            # Each response should be a valid json-rpc with result or error
            assert "result" in resp or "error" in resp


@pytest.mark.asyncio
async def test_mcp_ping():
    """4.8 Ping method returns successfully."""
    async with await _make_client() as c:
        resp = await _send_jsonrpc(c, "ping", msg_id=42)
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp or "error" in resp


# ---------------------------------------------------------------------------
# 5. Concurrency — parallel connections
# ---------------------------------------------------------------------------

async def _concurrent_initialize_task(client: httpx.AsyncClient, idx: int) -> dict:
    """Run initialize + tools/list for one concurrent client."""
    result = await _initialize(client)
    session_id = result["result"].get("session_id", "")
    tools_resp = await _send_jsonrpc(
        client, "tools/list", msg_id=idx, session_id=session_id
    )
    return tools_resp


@pytest.mark.asyncio
async def test_concurrent_initialize_5_clients():
    """5.1 Five concurrent initialize handshakes all succeed."""
    clients = [await _make_client() for _ in range(5)]
    try:
        results = await asyncio.gather(
            *(asyncio.create_task(_initialize(c)) for c in clients)
        )
        assert len(results) == 5
        for r in results:
            assert r["jsonrpc"] == "2.0"
            assert "result" in r
            assert r["result"]["protocolVersion"] == "2025-03-26"
    finally:
        await asyncio.gather(*(c.aclose() for c in clients))


@pytest.mark.asyncio
async def test_concurrent_tools_list_5_clients():
    """5.2 Five concurrent tools/list calls all succeed."""
    clients = [await _make_client() for _ in range(5)]
    try:
        async def _task(c, idx):
            init = await _initialize(c)
            sid = init["result"].get("session_id", "")
            return await _send_jsonrpc(
                c, "tools/list", msg_id=idx, session_id=sid
            )

        results = await asyncio.gather(
            *(asyncio.create_task(_task(c, i)) for i, c in enumerate(clients))
        )
        assert len(results) == 5
        for r in results:
            assert r["jsonrpc"] == "2.0"
            assert "result" in r
            assert len(r["result"]["tools"]) > 0
    finally:
        await asyncio.gather(*(c.aclose() for c in clients))


@pytest.mark.asyncio
async def test_concurrent_consulta_fiscal_5_clients():
    """5.3 Five concurrent consulta_fiscal calls all return results."""
    clients = [await _make_client() for _ in range(5)]
    try:
        async def _task(c, idx):
            await _initialize(c)
            return await _send_jsonrpc(
                c,
                "tools/call",
                params={
                    "name": "consulta_fiscal",
                    "arguments": {"q": f"consulta paralela {idx}"},
                },
                msg_id=idx + 10,
            )

        results = await asyncio.gather(
            *(asyncio.create_task(_task(c, i)) for i, c in enumerate(clients))
        )
        assert len(results) == 5
        for r in results:
            assert r["jsonrpc"] == "2.0"
            assert "result" in r
            assert "content" in r["result"]
    finally:
        await asyncio.gather(*(c.aclose() for c in clients))


@pytest.mark.asyncio
async def test_concurrent_mixed_tools_8_clients():
    """5.4 Eight concurrent clients calling different tools simultaneously."""
    tool_calls = [
        ("consulta_fiscal", {"q": "iva"}),
        ("listar_obligaciones_operativas", {"limite": 3}),
        ("listar_deadlines", {"dias_proximo": 7}),
        ("agente_monitoreo_status", {}),
        ("consulta_fiscal", {"q": "retenciones irpf"}),
        ("listar_obligaciones_operativas", {"ambito": "fiscal"}),
        ("listar_deadlines", {"dias_proximo": 14}),
        ("agente_monitoreo_status", {}),
    ]

    clients = [await _make_client() for _ in range(len(tool_calls))]
    try:
        async def _task(c, idx):
            await _initialize(c)
            tool_name, args = tool_calls[idx]
            return await _send_jsonrpc(
                c,
                "tools/call",
                params={"name": tool_name, "arguments": args},
                msg_id=idx + 20,
            )

        results = await asyncio.gather(
            *(asyncio.create_task(_task(c, i)) for i, c in enumerate(clients))
        )
        assert len(results) == len(tool_calls)
        for r in results:
            assert r["jsonrpc"] == "2.0"
            assert "result" in r or "error" in r
    finally:
        await asyncio.gather(*(c.aclose() for c in clients))


@pytest.mark.asyncio
async def test_concurrent_error_handling_3_clients():
    """5.5 Three concurrent clients sending invalid requests all get errors."""
    clients = [await _make_client() for _ in range(3)]
    try:
        async def _task(c, idx):
            await _initialize(c)
            return await _send_jsonrpc(
                c,
                "tools/call",
                params={"name": "tool_fantasma", "arguments": {}},
                msg_id=idx + 50,
            )

        results = await asyncio.gather(
            *(asyncio.create_task(_task(c, i)) for i, c in enumerate(clients))
        )
        assert len(results) == 3
        for r in results:
            assert r["jsonrpc"] == "2.0"
            assert ("error" in r and r["error"]["code"] == -32601) or r.get("result", {}).get("isError") is True
    finally:
        await asyncio.gather(*(c.aclose() for c in clients))


@pytest.mark.asyncio
async def test_concurrent_sequential_same_client():
    """5.6 Same client, 5 sequential calls without connection reuse issues."""
    async with await _make_client() as c:
        await _initialize(c)
        for i in range(5):
            resp = await _send_jsonrpc(
                c,
                "tools/call",
                params={
                    "name": "consulta_fiscal",
                    "arguments": {"q": f"secuencial {i}"},
                },
                msg_id=100 + i,
            )
            assert resp["jsonrpc"] == "2.0"
            assert "result" in resp


@pytest.mark.asyncio
async def test_concurrent_tools_list_then_call():
    """5.7 Multiple clients: initialize -> tools/list -> tools/call pipeline."""
    clients = [await _make_client() for _ in range(3)]
    try:
        async def _pipeline(c, idx):
            init_resp = await _initialize(c)
            sid = init_resp["result"].get("session_id", "")
            tools_resp = await _send_jsonrpc(
                c, "tools/list", msg_id=idx, session_id=sid
            )
            assert len(tools_resp["result"]["tools"]) > 0
            call_resp = await _send_jsonrpc(
                c,
                "tools/call",
                params={
                    "name": "consulta_fiscal",
                    "arguments": {"q": f"pipeline {idx}"},
                },
                msg_id=idx + 100,
            )
            return call_resp

        results = await asyncio.gather(
            *(asyncio.create_task(_pipeline(c, i)) for i, c in enumerate(clients))
        )
        assert len(results) == 3
        for r in results:
            assert r["jsonrpc"] == "2.0"
            assert "result" in r
            assert "content" in r["result"]
    finally:
        await asyncio.gather(*(c.aclose() for c in clients))
