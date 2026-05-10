import os
import json
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
import requests
from httpx import ASGITransport, AsyncClient
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from mcp_security import reset_mcp_rate_limit_state


API_DIR = Path(__file__).resolve().parents[1]


def _mcp_get(headers: dict[str, str] | None = None):
    with TestClient(app) as client:
        return client.get(
            "/mcp",
            headers={"Accept": "text/event-stream", **(headers or {})},
        )


def _core_operation_names() -> set[str]:
    from mcp_catalog import HTTP_MCP_OPERATIONS

    return set(HTTP_MCP_OPERATIONS)


def _mcp_rpc_headers(session_id: str, api_key: str) -> dict[str, str]:
    return {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "MCP-Session-ID": session_id,
    }


def _initialize_mcp_session(port: int, api_key: str = "secret") -> tuple[requests.Session, dict[str, str]]:
    session = requests.Session()
    handshake = session.get(
        f"http://127.0.0.1:{port}/mcp",
        headers={"Accept": "text/event-stream", "X-API-Key": api_key},
        timeout=5,
    )
    session_id = handshake.headers.get("mcp-session-id") or handshake.headers.get("Mcp-Session-Id")
    assert session_id

    rpc_headers = _mcp_rpc_headers(session_id, api_key)
    initialize = session.post(
        f"http://127.0.0.1:{port}/mcp",
        headers=rpc_headers,
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
        timeout=5,
    )
    assert initialize.status_code == 200
    return session, rpc_headers


def _mcp_structured_result(response: requests.Response) -> dict:
    payload = response.json()
    result = payload["result"]
    if "structuredContent" in result:
        return result["structuredContent"]
    content = result.get("content") or []
    text_items = [
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    assert text_items, payload
    return json.loads(text_items[0])


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@asynccontextmanager
async def _uvicorn_server(**env_overrides):
    previous = {key: os.environ.get(key) for key in env_overrides}
    port = _free_tcp_port()
    env = os.environ.copy()
    env.update(env_overrides)

    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(API_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        for _ in range(50):
            try:
                response = requests.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
                if response.status_code == 200:
                    yield port
                    break
            except requests.RequestException:
                time.sleep(0.1)
        else:
            raise RuntimeError("uvicorn test server did not become ready")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@asynccontextmanager
async def _client_with_env(**env_overrides):
    previous = {key: os.environ.get(key) for key in env_overrides}
    try:
        reset_mcp_rate_limit_state()
        for key, value in env_overrides.items():
            os.environ[key] = value
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        reset_mcp_rate_limit_state()
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.mark.asyncio
async def test_mcp_catalog_exposes_expected_core_http_operations():
    operation_names = _core_operation_names()

    assert "list_legislacion" in operation_names
    assert "buscar_doctrina" in operation_names
    assert "list_modelos" in operation_names
    assert "get_modelo_fuentes_oficiales" in operation_names


@pytest.mark.asyncio
async def test_mcp_http_rejects_missing_api_key_when_enabled():
    async with _uvicorn_server(MCP_API_KEY="secret", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        r = requests.get(
            f"http://127.0.0.1:{port}/mcp",
            headers={"Accept": "text/event-stream"},
            timeout=5,
        )

    assert r.status_code == 401


@pytest.mark.asyncio
async def test_mcp_http_accepts_valid_api_key_when_enabled():
    async with _uvicorn_server(MCP_API_KEY="secret", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        r = requests.get(
            f"http://127.0.0.1:{port}/mcp",
            headers={"Accept": "text/event-stream", "X-API-Key": "secret"},
            timeout=5,
        )

    assert r.status_code != 401


@pytest.mark.asyncio
async def test_mcp_http_rate_limits_repeated_requests():
    async with _client_with_env(MCP_API_KEY="secret", MCP_RATE_LIMIT_PER_MINUTE="2") as client:
        headers = {"X-API-Key": "secret", "Accept": "text/event-stream"}
        first = await client.get("/mcp", headers=headers)
        second = await client.get("/mcp", headers=headers)
        third = await client.get("/mcp", headers=headers)

    assert first.status_code != 429
    assert second.status_code != 429
    assert third.status_code == 429


@pytest.mark.asyncio
async def test_mcp_http_end_to_end_initialize_and_tools_list_with_api_key():
    async with _uvicorn_server(MCP_API_KEY="secret", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        session, rpc_headers = _initialize_mcp_session(port, "secret")

        tools = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers=rpc_headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            timeout=5,
        )
        assert tools.status_code == 200

        names = {tool["name"] for tool in tools.json()["result"]["tools"]}
        assert "buscar" in names
        assert "list_modelos" in names
        assert "list_domain_availability" in names
        assert "get_domain_availability" in names


@pytest.mark.asyncio
async def test_mcp_tool_call_domain_availability_exposes_explicit_empty_states():
    async with _uvicorn_server(MCP_API_KEY="secret", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        session, rpc_headers = _initialize_mcp_session(port, "secret")

        tool_call = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers=rpc_headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "list_domain_availability", "arguments": {"only_empty": True}},
            },
            timeout=5,
        )

    assert tool_call.status_code == 200
    structured = _mcp_structured_result(tool_call)
    statuses = {item["availability_status"] for item in structured["items"]}
    assert statuses <= {"workflow_empty", "allowed_empty", "configured_but_unavailable"}
    assert "not_available" not in statuses
    assert "operational_data" not in statuses
    assert structured["summary"].get("unknown", 0) == 0
    assert all(item["status"] == item["availability_status"] for item in structured["items"])


@pytest.mark.asyncio
async def test_mcp_consulta_empty_domain_fails_closed_without_invented_answer():
    async with _uvicorn_server(MCP_API_KEY="secret", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        session, rpc_headers = _initialize_mcp_session(port, "secret")

        tool_call = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers=rpc_headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "consulta_fiscal",
                    "arguments": {"q": "lista CASP MiCA autorizados en España"},
                },
            },
            timeout=5,
        )

    assert tool_call.status_code == 200
    structured = _mcp_structured_result(tool_call)
    confianza = structured["confianza"]
    availability = confianza["availability"]
    tables = {item["table"] for item in availability["tables"]}

    assert structured["total_resultados"] == 0
    assert structured["resultados"] == []
    assert structured["cited_chunks"] == []
    assert "NO VERIFICADO" in confianza["aviso"]
    assert availability["blocked"] is True
    assert "casp" in tables


@pytest.mark.asyncio
async def test_mcp_tool_call_can_execute_protected_rest_operation_without_rest_api_key_collision():
    async with _uvicorn_server(
        APP_ENV="production",
        ESDATA_API_KEY="rest-secret",
        MCP_API_KEY="mcp-secret",
        MCP_RATE_LIMIT_PER_MINUTE="20",
    ) as port:
        session = requests.Session()
        headers = {"Accept": "text/event-stream", "X-API-Key": "mcp-secret"}
        handshake = session.get(f"http://127.0.0.1:{port}/mcp", headers=headers, timeout=5)

        session_id = handshake.headers.get("mcp-session-id") or handshake.headers.get("Mcp-Session-Id")
        assert session_id

        rpc_headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "X-API-Key": "mcp-secret",
            "MCP-Session-ID": session_id,
        }

        initialize = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers=rpc_headers,
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
            timeout=5,
        )
        assert initialize.status_code == 200

        tool_call = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers=rpc_headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "list_modelos", "arguments": {}},
            },
            timeout=5,
        )

    assert tool_call.status_code == 200
    payload = tool_call.json()
    assert payload.get("result")
    assert payload["result"].get("isError") is not True
