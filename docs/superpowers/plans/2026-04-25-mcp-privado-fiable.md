# [REFERENCE] MCP Privado Fiable Implementation Plan

> Documento lateral de detalle MCP. No es la fuente activa de estado. La fuente activa unica de estado y ejecucion es `docs/master-execution-roadmap.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unificar la superficie MCP de `esdata` entre `stdio` y `HTTP`, añadir proteccion minima para `/mcp` y dejar tests/docs suficientes para uso personal y uso interno privado.

**Architecture:** Se extrae un nucleo compartido con el catalogo de herramientas y su ejecucion. `mcp_server.py` y `mcp_stdio.py` pasan a consumir esa capa compartida para evitar deriva. Sobre el transporte HTTP se añade una guarda minima con `API key` y `rate limit` sencillo, sin introducir autenticacion compleja.

**Tech Stack:** FastAPI, fastapi-mcp, FastAPI TestClient/ASGITransport, pytest, Python stdlib subprocess/env.

---

## File Map

- Modify: `apps/api/mcp_stdio.py`
- Modify: `apps/api/mcp_server.py`
- Modify: `apps/api/main.py`
- Create: `apps/api/mcp_catalog.py`
- Create: `apps/api/mcp_security.py`
- Create: `apps/api/tests/test_mcp_private.py`
- Modify: `README.md`
- Optional cleanup after verification: remove or deprecate ad hoc scripts `apps/api/test_mcp_tool.py`, `apps/api/test_mcp_tool2.py`, `apps/api/test_mcp_tools.py`, `apps/api/test_mcp_formats.py`, `apps/api/test_stdio_full.py`, `apps/api/test_mcp_http.py`

### Task 1: Add shared MCP catalog

**Files:**
- Create: `apps/api/mcp_catalog.py`
- Modify: `apps/api/mcp_stdio.py`
- Test: `apps/api/tests/test_mcp_private.py`

- [ ] **Step 1: Write the failing catalog parity test**

```python
def test_mcp_catalog_includes_expected_core_tools():
    from mcp_catalog import get_stdio_tool_definitions

    tool_names = {tool["name"] for tool in get_stdio_tool_definitions()}

    assert "consulta_fiscal" in tool_names
    assert "listar_obligaciones_operativas" in tool_names
    assert "listar_deadlines" in tool_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_mcp_private.py -k catalog -v`
Expected: FAIL with `ModuleNotFoundError` or missing symbol in `mcp_catalog`.

- [ ] **Step 3: Write minimal shared catalog implementation**

```python
# apps/api/mcp_catalog.py
from __future__ import annotations

from typing import Any


def get_stdio_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "consulta_fiscal",
            "description": "Consulta fiscal inteligente en lenguaje natural.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                    "sujeto": {"type": "string"},
                    "pais": {"type": "string"},
                    "tipo_operacion": {"type": "string"},
                },
                "required": ["q"],
            },
        },
        {
            "name": "listar_obligaciones_operativas",
            "description": "Lista obligaciones operativas estructuradas.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "listar_deadlines",
            "description": "Lista obligaciones proximas a vencer.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_obligacion_completa",
            "description": "Obtiene detalle completo de una obligacion.",
            "inputSchema": {
                "type": "object",
                "properties": {"codigo": {"type": "string"}},
                "required": ["codigo"],
            },
        },
    ]
```

- [ ] **Step 4: Update stdio to consume the shared catalog**

```python
# inside apps/api/mcp_stdio.py
from mcp_catalog import get_stdio_tool_definitions


def _handle_tools_list(self, msg_id: Any):
    self._send_jsonrpc(msg_id, {"tools": get_stdio_tool_definitions()})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest apps/api/tests/test_mcp_private.py -k catalog -v`
Expected: PASS

### Task 2: Add MCP HTTP guard (API key + rate limit)

**Files:**
- Create: `apps/api/mcp_security.py`
- Modify: `apps/api/main.py`
- Test: `apps/api/tests/test_mcp_private.py`

- [ ] **Step 1: Write failing auth tests**

```python
@pytest.mark.asyncio
async def test_mcp_http_rejects_missing_api_key_when_enabled():
    async with _client_with_env(MCP_API_KEY="secret", MCP_RATE_LIMIT_PER_MINUTE="20") as c:
        r = await c.get("/mcp")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_mcp_http_accepts_valid_api_key_when_enabled():
    async with _client_with_env(MCP_API_KEY="secret", MCP_RATE_LIMIT_PER_MINUTE="20") as c:
        r = await c.get("/mcp", headers={"X-API-Key": "secret"})
    assert r.status_code != 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest apps/api/tests/test_mcp_private.py -k "api_key" -v`
Expected: FAIL because `/mcp` does not yet enforce the header.

- [ ] **Step 3: Implement minimal MCP guard**

```python
# apps/api/mcp_security.py
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Request
from fastapi.responses import JSONResponse


_RATE_BUCKETS: dict[str, Deque[float]] = defaultdict(deque)


def _required_api_key() -> str:
    return os.getenv("MCP_API_KEY", "").strip()


def _rate_limit() -> int:
    return int(os.getenv("MCP_RATE_LIMIT_PER_MINUTE", "60"))


async def guard_mcp_http(request: Request, call_next):
    if not request.url.path.startswith("/mcp"):
        return await call_next(request)

    required_key = _required_api_key()
    provided_key = request.headers.get("X-API-Key", "")

    if required_key and provided_key != required_key:
        return JSONResponse({"detail": "Invalid or missing MCP API key"}, status_code=401)

    if required_key:
        key = provided_key or request.client.host if request.client else "unknown"
        bucket = _RATE_BUCKETS[key]
        now = time.time()
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= _rate_limit():
            return JSONResponse({"detail": "MCP rate limit exceeded"}, status_code=429)
        bucket.append(now)

    return await call_next(request)
```

- [ ] **Step 4: Wire guard into FastAPI**

```python
# inside apps/api/main.py
from mcp_security import guard_mcp_http

app.middleware("http")(guard_mcp_http)
```

- [ ] **Step 5: Run auth tests to verify they pass**

Run: `pytest apps/api/tests/test_mcp_private.py -k "api_key" -v`
Expected: PASS

### Task 3: Add rate limit test coverage

**Files:**
- Modify: `apps/api/tests/test_mcp_private.py`
- Modify: `apps/api/mcp_security.py`

- [ ] **Step 1: Write failing rate limit test**

```python
@pytest.mark.asyncio
async def test_mcp_http_rate_limits_repeated_requests():
    async with _client_with_env(MCP_API_KEY="secret", MCP_RATE_LIMIT_PER_MINUTE="2") as c:
        headers = {"X-API-Key": "secret"}
        first = await c.get("/mcp", headers=headers)
        second = await c.get("/mcp", headers=headers)
        third = await c.get("/mcp", headers=headers)

    assert first.status_code != 429
    assert second.status_code != 429
    assert third.status_code == 429
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_mcp_private.py -k rate_limit -v`
Expected: FAIL until the limiter is wired and state reset is handled.

- [ ] **Step 3: Add reset helper for deterministic tests**

```python
# in apps/api/mcp_security.py
def reset_mcp_rate_limit_state() -> None:
    _RATE_BUCKETS.clear()
```

```python
# in test fixture setup
from mcp_security import reset_mcp_rate_limit_state

reset_mcp_rate_limit_state()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/test_mcp_private.py -k rate_limit -v`
Expected: PASS

### Task 4: Add stdio and HTTP parity tests

**Files:**
- Create: `apps/api/tests/test_mcp_private.py`
- Modify: `apps/api/mcp_stdio.py`

- [ ] **Step 1: Write failing stdio parity tests**

```python
def test_stdio_tools_list_contains_expected_core_tools():
    response = run_stdio_exchange([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ])

    tools = response[-1]["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert "consulta_fiscal" in names
    assert "listar_deadlines" in names
```

- [ ] **Step 2: Run test to verify it fails or is incomplete**

Run: `pytest apps/api/tests/test_mcp_private.py -k stdio -v`
Expected: FAIL until stdio helpers/tests are implemented.

- [ ] **Step 3: Add reusable stdio test harness**

```python
def run_stdio_exchange(messages: list[dict]) -> list[dict]:
    proc = subprocess.Popen(
        [sys.executable, "mcp_stdio.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(API_DIR),
    )
    ...
```

- [ ] **Step 4: Add HTTP tools/list parity assertion**

```python
@pytest.mark.asyncio
async def test_http_and_stdio_share_same_core_tool_names():
    stdio_names = {...}
    async with _client_with_env() as c:
        r = await c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    http_names = {tool["name"] for tool in r.json()["result"]["tools"]}
    assert {"consulta_fiscal", "listar_obligaciones_operativas", "listar_deadlines"}.issubset(stdio_names)
    assert {"consulta_fiscal", "listar_obligaciones_operativas", "listar_deadlines"}.issubset(http_names)
```

- [ ] **Step 5: Run parity tests to verify they pass**

Run: `pytest apps/api/tests/test_mcp_private.py -k "stdio or parity" -v`
Expected: PASS

### Task 5: Document MCP modes and clean manual scripts status

**Files:**
- Modify: `README.md`
- Optional Modify/Delete: `apps/api/test_mcp_tool.py`, `apps/api/test_mcp_tool2.py`, `apps/api/test_mcp_tools.py`, `apps/api/test_mcp_formats.py`, `apps/api/test_stdio_full.py`, `apps/api/test_mcp_http.py`

- [ ] **Step 1: Write documentation expectations test note in plan**

```text
README must have separate sections for:
- MCP stdio local
- MCP HTTP privado
- GPT Actions
```

- [ ] **Step 2: Update README structure**

```md
### MCP stdio local
- ejecutar `python apps/api/mcp_stdio.py`
- pensado para uso personal con cliente local

### MCP HTTP privado
- exponer `/mcp` solo en entorno privado
- configurar `MCP_API_KEY`
- usar cabecera `X-API-Key`

### GPT Actions
- usar `docs/openapi-gpt.json`
- integracion separada de MCP
```

- [ ] **Step 3: Mark ad hoc scripts as legacy or remove them if replaced**

```python
# Legacy manual debug script. Prefer pytest apps/api/tests/test_mcp_private.py
```

- [ ] **Step 4: Run targeted verification**

Run: `pytest apps/api/tests/test_mcp_private.py -v`
Expected: PASS

Run: `pytest apps/api/tests/test_smoke.py -q`
Expected: PASS

- [ ] **Step 5: Final verification sweep**

Run: `pytest apps/api/tests/test_mcp_private.py apps/api/tests/test_smoke.py -q`
Expected: all tests PASS
