from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import requests

API_DIR = Path(__file__).resolve().parents[1]


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def uvicorn_mcp_server(**env_overrides):
    port = _free_tcp_port()
    env = os.environ.copy()
    env.update(env_overrides)
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(API_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        ready = False
        for _ in range(50):
            try:
                response = requests.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
                if response.status_code == 200:
                    ready = True
                    break
            except requests.RequestException:
                time.sleep(0.1)

        if not ready:
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
            raise RuntimeError(
                "uvicorn test server did not become ready\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            )

        yield port
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def run_http_mcp_tool_call(
    *,
    tool_name: str,
    arguments: dict,
    request_id: str,
    user_id: str = "internal-http-mcp-user",
    mcp_api_key: str = "mcp-secret",
):
    with uvicorn_mcp_server(MCP_API_KEY=mcp_api_key, MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        session = requests.Session()
        handshake = session.get(
            f"http://127.0.0.1:{port}/mcp",
            headers={"Accept": "text/event-stream", "X-API-Key": mcp_api_key},
            timeout=5,
        )

        session_id = handshake.headers.get("mcp-session-id") or handshake.headers.get("Mcp-Session-Id")
        if not session_id:
            raise AssertionError("MCP handshake did not return a session id")

        rpc_headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "X-API-Key": mcp_api_key,
            "Mcp-Session-Id": session_id,
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

        tool_call = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                **rpc_headers,
                "x-request-id": request_id,
                "x-user-id": user_id,
            },
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            timeout=5,
        )

    return handshake, initialize, tool_call
