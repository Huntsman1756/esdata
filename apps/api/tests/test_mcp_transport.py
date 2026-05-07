"""Regression coverage for MCP HTTP transport lifecycle."""

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

from services.query_audit import QueryAuditService


API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


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


def _run_mcp_busqueda_call(port: int, request_id: str):
    session = requests.Session()
    handshake = session.get(
        f"http://127.0.0.1:{port}/mcp",
        headers={"Accept": "text/event-stream", "X-API-Key": "test-mcp-key"},
        timeout=5,
    )

    assert handshake.status_code in {200, 400}
    session_id = handshake.headers.get("Mcp-Session-Id") or handshake.headers.get("mcp-session-id")
    assert session_id

    init_response = session.post(
        f"http://127.0.0.1:{port}/mcp",
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "X-API-Key": "test-mcp-key",
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

    assert init_response.status_code == 200

    search_response = session.post(
        f"http://127.0.0.1:{port}/mcp",
        headers={
            "Mcp-Session-Id": session_id,
            "X-API-Key": "test-mcp-key",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "x-request-id": request_id,
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
        timeout=5,
    )

    assert search_response.status_code == 200, search_response.text
    assert search_response.headers.get("X-Request-ID") == request_id
    payload = search_response.json()
    assert payload.get("result")
    assert payload["result"].get("isError") is not True


@pytest.mark.asyncio
async def test_mcp_transport_first_request_persists_audit_row():
    async with _uvicorn_server(MCP_API_KEY="test-mcp-key", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        _run_mcp_busqueda_call(port, "req-mcp-transport-001")

    entries = QueryAuditService().get_by_request_id("req-mcp-transport-001")
    assert len(entries) == 1
    assert entries[0].path == "/v1/buscar"


@pytest.mark.asyncio
async def test_mcp_transport_second_request_also_persists_audit_row():
    async with _uvicorn_server(MCP_API_KEY="test-mcp-key", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        _run_mcp_busqueda_call(port, "req-mcp-transport-002")

    entries = QueryAuditService().get_by_request_id("req-mcp-transport-002")
    assert len(entries) == 1
    assert entries[0].path == "/v1/buscar"
