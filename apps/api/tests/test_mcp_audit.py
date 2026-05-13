"""End-to-end MCP audit verification for MCP HTTP tool calls."""

from __future__ import annotations

import os
import socket
import sqlite3
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
import requests

from apps.api.tests.conftest import TEST_DB_PATH

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from services.query_audit import reset_query_audit_service


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@asynccontextmanager
async def _uvicorn_server(**env_overrides):
    previous = {key: os.environ.get(key) for key in env_overrides}
    port = _free_tcp_port()
    env = os.environ.copy()
    env["APP_ENV"] = "test"
    env["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
    env["ESDATA_API_KEY"] = "test-secret-key"
    env["ESDATA_ALLOW_INSECURE_TEST_AUTH"] = "true"
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


def _audit_entries_for_request_id(request_id: str) -> list[sqlite3.Row]:
    connection = sqlite3.connect(TEST_DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT *
            FROM query_audit_log
            WHERE request_id = ?
            ORDER BY created_at ASC
            """,
            (request_id,),
        ).fetchall()
    finally:
        connection.close()
    return rows


@pytest.mark.asyncio
async def test_mcp_consulta_persists_audit_entry_with_request_id_correlation():
    async with _uvicorn_server(MCP_API_KEY="test-mcp-key", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        session = requests.Session()
        handshake = session.get(
            f"http://127.0.0.1:{port}/mcp",
            headers={"Accept": "text/event-stream", "X-API-Key": "test-mcp-key"},
            timeout=5,
        )

        assert handshake.status_code in {200, 400}
        session_id = handshake.headers.get("Mcp-Session-Id") or handshake.headers.get("mcp-session-id")
        assert session_id, "MCP initialize must return a session id"

        init_response = session.post(
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

        assert init_response.status_code == 200

        search_response = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "Mcp-Session-Id": session_id,
                "x-api-key": "test-mcp-key",
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
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
            timeout=5,
        )

    assert search_response.status_code == 200
    assert search_response.headers.get("X-Request-ID") == "req-mcp-audit-001"
    payload = search_response.json()
    assert payload.get("result")
    assert payload["result"].get("isError") is not True

    entries = _audit_entries_for_request_id("req-mcp-audit-001")

    assert len(entries) == 1
    entry = entries[0]
    assert entry["path"] == "/v1/buscar"
    assert "tipo reducido iva" in entry["query_text"].lower()
    assert entry["response_summary"]
