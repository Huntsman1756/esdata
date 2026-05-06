"""End-to-end MCP audit verification for internal consulta flow."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
import requests
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from main import app  # noqa: E402
from mcp_request_context import mcp_internal_request  # noqa: E402
from services.query_audit import QueryAuditService, reset_query_audit_service  # noqa: E402


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


def setup_function():
    reset_query_audit_service()


def teardown_function():
    reset_query_audit_service()


@pytest.mark.asyncio
async def test_mcp_buscar_persists_single_boundary_audit_entry():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-key",
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

        buscar_response = await client.post(
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
                    "name": "buscar",
                    "arguments": {"q": "tipo reducido iva"},
                },
            },
        )

    assert buscar_response.status_code == 200
    assert buscar_response.headers.get("X-Request-ID") == "req-mcp-audit-001"

    service = QueryAuditService()
    entries = service.get_by_request_id("req-mcp-audit-001")

    assert len(entries) == 1
    entry = entries[0]
    assert entry.path == "/mcp/tools/call/buscar"
    assert not any(entry.path == "/v1/buscar" for entry in entries)
    assert entry.user_id == "internal-mcp-user"
    assert entry.query_text == '{"q": "tipo reducido iva"}'
    assert "tool=buscar" in entry.response_summary
    assert "http_status=200" in entry.response_summary


@pytest.mark.asyncio
async def test_mcp_consulta_persists_router_retrieval_audit_entry():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-key",
            "x-request-id": "req-mcp-consulta-audit-001",
            "x-user-id": "internal-mcp-user",
        },
    ) as client:
        with mcp_internal_request():
            consulta_response = await client.get("/v1/consulta?q=tipo+reducido+iva")

    assert consulta_response.status_code == 200
    entries = QueryAuditService().get_by_request_id("req-mcp-consulta-audit-001")
    consulta_entries = [entry for entry in entries if entry.path == "/v1/consulta"]

    assert len(consulta_entries) == 1
    assert consulta_entries[0].user_id == "internal-mcp-user"
    assert consulta_entries[0].retrieved_chunks


@pytest.mark.asyncio
async def test_mcp_boundary_audits_tool_without_router_level_audit():
    async with _uvicorn_server(MCP_API_KEY="test-mcp-key", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        session = requests.Session()
        handshake = session.get(
            f"http://127.0.0.1:{port}/mcp",
            headers={"Accept": "text/event-stream", "X-API-Key": "test-mcp-key"},
            timeout=5,
        )
        session_id = handshake.headers.get("Mcp-Session-Id") or handshake.headers.get("mcp-session-id")
        assert session_id

        session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "x-api-key": "test-mcp-key",
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "Mcp-Session-Id": session_id,
            },
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

        response = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "Mcp-Session-Id": session_id,
                "x-api-key": "test-mcp-key",
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "x-request-id": "req-mcp-audit-list-legislacion",
                "x-user-id": "internal-mcp-user",
            },
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "list_legislacion", "arguments": {}},
            },
            timeout=5,
        )

    assert response.status_code == 200
    entries = QueryAuditService().get_by_request_id("req-mcp-audit-list-legislacion")
    assert any(entry.path == "/mcp/tools/call/list_legislacion" for entry in entries)
    boundary_entry = next(entry for entry in entries if entry.path == "/mcp/tools/call/list_legislacion")
    assert boundary_entry.user_id == "internal-mcp-user"
    assert boundary_entry.query_text == "{}"
    assert boundary_entry.grounding_status == "success"
    assert "tool=list_legislacion" in boundary_entry.response_summary
    assert "http_status=200" in boundary_entry.response_summary
    assert boundary_entry.grounding_summary["tool"] == "list_legislacion"
    assert boundary_entry.grounding_summary["http_status"] == 200


@pytest.mark.asyncio
async def test_mcp_boundary_audits_unknown_tool_validation_failure():
    async with _uvicorn_server(MCP_API_KEY="test-mcp-key", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        session = requests.Session()
        handshake = session.get(
            f"http://127.0.0.1:{port}/mcp",
            headers={"Accept": "text/event-stream", "X-API-Key": "test-mcp-key"},
            timeout=5,
        )
        session_id = handshake.headers.get("Mcp-Session-Id") or handshake.headers.get("mcp-session-id")
        assert session_id

        session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "x-api-key": "test-mcp-key",
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "Mcp-Session-Id": session_id,
            },
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

        response = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "Mcp-Session-Id": session_id,
                "x-api-key": "test-mcp-key",
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "x-request-id": "req-mcp-audit-unknown-tool",
                "x-user-id": "internal-mcp-user",
            },
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "does_not_exist", "arguments": {"codigo": "LIVA"}},
            },
            timeout=5,
        )

    assert response.status_code in {200, 400}
    entries = QueryAuditService().get_by_request_id("req-mcp-audit-unknown-tool")
    assert any(entry.path == "/mcp/tools/call/does_not_exist" for entry in entries)
    boundary_entry = next(entry for entry in entries if entry.path == "/mcp/tools/call/does_not_exist")
    assert boundary_entry.user_id == "internal-mcp-user"
    assert boundary_entry.query_text == '{"codigo": "LIVA"}'
    assert boundary_entry.grounding_status in {"validation_error", "internal_error"}
    assert "tool=does_not_exist" in boundary_entry.response_summary


@pytest.mark.asyncio
async def test_mcp_boundary_audits_tool_without_request_id_header():
    async with _uvicorn_server(MCP_API_KEY="test-mcp-key", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        session = requests.Session()
        handshake = session.get(
            f"http://127.0.0.1:{port}/mcp",
            headers={"Accept": "text/event-stream", "X-API-Key": "test-mcp-key"},
            timeout=5,
        )
        session_id = handshake.headers.get("Mcp-Session-Id") or handshake.headers.get("mcp-session-id")
        assert session_id

        session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "x-api-key": "test-mcp-key",
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "Mcp-Session-Id": session_id,
            },
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

        response = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "Mcp-Session-Id": session_id,
                "x-api-key": "test-mcp-key",
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "x-user-id": "internal-mcp-user",
            },
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "list_legislacion", "arguments": {}},
            },
            timeout=5,
        )

    assert response.status_code in {200, 400}
    entries = QueryAuditService().get_entries(path="/mcp/tools/call/list_legislacion")
    assert any(entry.user_id == "internal-mcp-user" and entry.request_id for entry in entries)


@pytest.mark.asyncio
async def test_mcp_boundary_audits_batch_tool_calls():
    async with _uvicorn_server(MCP_API_KEY="test-mcp-key", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        session = requests.Session()
        handshake = session.get(
            f"http://127.0.0.1:{port}/mcp",
            headers={"Accept": "text/event-stream", "X-API-Key": "test-mcp-key"},
            timeout=5,
        )
        session_id = handshake.headers.get("Mcp-Session-Id") or handshake.headers.get("mcp-session-id")
        assert session_id

        session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "x-api-key": "test-mcp-key",
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "Mcp-Session-Id": session_id,
            },
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

        response = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "Mcp-Session-Id": session_id,
                "x-api-key": "test-mcp-key",
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "x-request-id": "req-mcp-audit-batch",
                "x-user-id": "internal-mcp-user",
            },
            json=[
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "list_legislacion", "arguments": {}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "does_not_exist", "arguments": {}},
                },
            ],
            timeout=5,
        )

    assert response.status_code in {200, 400}
    entries = QueryAuditService().get_by_request_id("req-mcp-audit-batch")
    paths = [entry.path for entry in entries]
    assert paths.count("/mcp/tools/call/list_legislacion") == 1
    assert paths.count("/mcp/tools/call/does_not_exist") == 1
    unknown_entry = next(entry for entry in entries if entry.path == "/mcp/tools/call/does_not_exist")
    assert unknown_entry.grounding_status != "success"
