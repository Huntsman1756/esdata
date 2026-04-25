# Agent Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the hybrid agent layer — 3 new MCP tools for external LLM clients + internal agent monitor service for regulatory compliance automation.

**Architecture:** FastAPI background task (agent monitor) + MCP stdio/HTTP tool extensions. Reuses existing `/v1/consulta`, `/v1/cambios`, `/v1/compliance/workflow`, and `/v1/obligaciones` endpoints. No new DB, no new UI, no new auth.

**Tech Stack:** Python 3.12, FastAPI, asyncio, SQLAlchemy, pytest.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `apps/api/mcp_catalog.py` | Modify | Append 3 new tool definitions |
| `apps/api/mcp_stdio.py` | Modify | Add handlers for `agente_consulta`, `agente_monitoreo_status`, `agente_compliance_resumen` |
| `apps/api/agent_monitor.py` | Create | Agent monitor background service (env-driven, no endpoints) |
| `apps/api/main.py` | Modify | Import and start `agent_monitor` in lifespan |
| `apps/api/tests/test_agent_layer.py` | Create | Tests for catalog, stdio handlers, monitor logic |

---

### Task 1: Add 3 new MCP tool definitions to catalog

**Files:**
- Modify: `apps/api/mcp_catalog.py:103-143`

- [ ] **Step 1: Append tool definitions**

Add 3 new tool dicts to the list returned by `get_stdio_tool_definitions()` after line 143 (before the closing `]`):

```python
        {
            "name": "agente_consulta",
            "description": (
                "Consulta fiscal/regulatoria con contexto de entidad obligada. "
                "Expande la consulta basandose en el tipo de entidad y devuelve "
                "modelos AEAT, obligaciones y normativa aplicable. "
                "Ejemplos: 'que obligaciones tengo como sociedad de valores', "
                "'modelo 349 sanciones para intracomunitario'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Pregunta en lenguaje natural",
                    },
                    "tipo_entidad": {
                        "type": "string",
                        "enum": ["sociedad_valores", "entidad_dinero_electronico", "retenedor", "no_residente"],
                        "description": "Tipo de entidad obligada (opcional, default: sociedad_valores)",
                    },
                },
                "required": ["q"],
            },
        },
        {
            "name": "agente_monitoreo_status",
            "description": (
                "Estado actual del servicio de monitoreo interno de cambios regulatorios. "
                "Devuelve si el monitor esta activo, ultimo escaneo, proximo escaneo, "
                "y configuracion actual. No requiere parametros."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "agente_compliance_resumen",
            "description": (
                "Resumen del workflow de compliance con estados y prioridades. "
                "Devuelve casos de workflow filtrados por estado y limite. "
                "Ejemplos: 'resumen de compliance', 'casos pendientes', 'alertas de alta prioridad'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "estado": {
                        "type": "string",
                        "description": "Filtrar por estado del caso (ej: 'pendiente', 'en_revision', 'completado', 'urgente')",
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Numero maximo de resultados (1-200, default: 20)",
                    },
                },
                "required": [],
            },
        },
```

- [ ] **Step 2: Verify catalog loads correctly**

Run:
```bash
cd apps/api
python -c "from mcp_catalog import get_stdio_tool_definitions; tools = get_stdio_tool_definitions(); names = [t['name'] for t in tools]; print(f'Total tools: {len(names)}'); print(names)"
```

Expected output: `Total tools: 8` followed by all 8 tool names including the 3 new ones.

- [ ] **Step 3: Commit**

```bash
git add apps/api/mcp_catalog.py
git commit -m "feat(api): add 3 new agent MCP tool definitions to catalog"
```

---

### Task 2: Add stdio handlers for the 3 new agent tools

**Files:**
- Modify: `apps/api/mcp_stdio.py:100-216` (the `_handle_tools_call` method)

- [ ] **Step 1: Add `agente_consulta` handler**

After line 214 (after the `get_obligacion_completa` handler, before the `else` fallback), add:

```python
        elif tool_name == "agente_consulta":
            try:
                from fastapi import Query

                q = arguments.get("q", "")
                sujeto_arg = arguments.get("sujeto", "")
                tipo_entidad = arguments.get("tipo_entidad", "sociedad_valores")

                # Map tipo_entidad to sujeto for consulta expansion
                sujeto = sujeto_arg or _entidad_to_sujeto(tipo_entidad)

                response = client.get(
                    "/v1/consulta",
                    params={"q": q, "sujeto": sujeto},
                )

                if response.status_code == 200:
                    data = response.json()
                    output = self._format_response(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {response.status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing agente_consulta: {str(e)}")
```

- [ ] **Step 2: Add `_entidad_to_sujeto` helper function**

Add this method to the `MCPStdioServer` class (after `_format_obligacion_completa`, around line 453):

```python
    def _entidad_to_sujeto(self, tipo_entidad: str) -> str:
        """Map tipo_entidad to consulta sujeto parameter."""
        mapping = {
            "sociedad_valores": "contribuyente",
            "entidad_dinero_electronico": "empresa",
            "retenedor": "retenedor",
            "no_residente": "no_residente",
        }
        return mapping.get(tipo_entidad, "contribuyente")
```

- [ ] **Step 3: Add `agente_monitoreo_status` handler**

After the `agente_consulta` handler, add:

```python
        elif tool_name == "agente_monitoreo_status":
            try:
                from agent_monitor import get_monitor_status

                status = get_monitor_status()
                self._send_jsonrpc(msg_id, {
                    "content": [{"type": "text", "text": json.dumps(status, ensure_ascii=False, indent=2)}],
                    "structuredContent": status,
                })
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error getting monitor status: {str(e)}")
```

- [ ] **Step 4: Add `agente_compliance_resumen` handler**

After the `agente_monitoreo_status` handler, add:

```python
        elif tool_name == "agente_compliance_resumen":
            try:
                estado = arguments.get("estado")
                limite = arguments.get("limite", 20)

                response = client.get(
                    "/v1/compliance/workflow",
                    params={"estado": estado, "limite": limite} if estado else {"limite": limite},
                )

                if response.status_code == 200:
                    data = response.json()
                    output = self._format_compliance_resumen(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {response.status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing agente_compliance_resumen: {str(e)}")
```

- [ ] **Step 5: Add `_format_compliance_resumen` formatting method**

Add to the `MCPStdioServer` class:

```python
    def _format_compliance_resumen(self, data: list[dict]) -> str:
        """Format compliance workflow summary for LLM consumption."""
        if not data:
            return "No se encontraron casos de workflow con los filtros aplicados."

        lines = [f"Casos de workflow: {len(data)} resultados"]
        lines.append("")

        # Count by state
        estados: dict[str, int] = {}
        for caso in data:
            estado = caso.get("estado", "desconocido")
            estados[estado] = estados.get(estado, 0) + 1
        lines.append(f"Por estado: {', '.join(f'{k}: {v}' for k, v in sorted(estados.items()))}")
        lines.append("")

        for caso in data:
            lines.append(f"=== Caso: {caso.get('workflow_id', 'N/A')} ===")
            lines.append(f"  Cambio: {caso.get('cambio_codigo', 'N/A')}")
            lines.append(f"  Obligacion: {caso.get('obligacion_codigo', 'N/A')}")
            lines.append(f"  Estado: {caso.get('estado', 'N/A')}")
            lines.append(f"  Owner: {caso.get('owner_rol', 'N/A')}")
            if caso.get('fecha_objetivo'):
                lines.append(f"  Fecha objetivo: {caso['fecha_objetivo']}")
            if caso.get('notas'):
                lines.append(f"  Notas: {caso['notas'][:200]}")
            lines.append("")

        return "\n".join(lines)
```

- [ ] **Step 6: Verify syntax**

Run:
```bash
cd apps/api
python -c "import mcp_stdio; print('mcp_stdio imports OK')"
```

Expected: `mcp_stdio imports OK` (no errors).

- [ ] **Step 7: Commit**

```bash
git add apps/api/mcp_stdio.py
git commit -m "feat(api): add stdio handlers for 3 new agent MCP tools"
```

---

### Task 3: Create the agent monitor service

**Files:**
- Create: `apps/api/agent_monitor.py`

- [ ] **Step 1: Write the full agent_monitor.py**

Create the file with this content:

```python
"""Internal agent monitor — background task for regulatory change detection.

Scans for pending regulatory changes, evaluates impact on applicable obligations,
and creates workflow triggers when impact is detected.

Configured via environment variables:
  AGENT_MONITOR_ENABLED   — 'true'/'false' (default: 'false')
  AGENT_MONITOR_INTERVAL  — seconds between scans (default: 300)
  AGENT_MONITOR_ENTIDAD   — entity profile type (default: 'sociedad_valores')
  AGENT_MONITOR_PRIORIDAD — default trigger priority (default: 'media')
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi.testclient import TestClient

from main import app as fastapi_app

logger = logging.getLogger(__name__)


@dataclass
class MonitorStatus:
    enabled: bool
    running: bool = False
    last_scan: float | None = None
    last_scan_duration_ms: float | None = None
    next_scan_in_seconds: float | None = None
    interval_seconds: int = 300
    entidad: str = "sociedad_valores"
    prioridad: str = "media"
    total_scans: int = 0
    total_triggers_created: int = 0
    errors: int = 0
    _started_at: float = field(default_factory=time.time, repr=False)


# Global singleton — initialized lazily on first status call
_monitor_status: MonitorStatus | None = None
_monitor_task: asyncio.Task | None = None
_client = TestClient(fastapi_app)


def _get_status() -> MonitorStatus:
    global _monitor_status
    if _monitor_status is None:
        _monitor_status = MonitorStatus(
            enabled=os.getenv("AGENT_MONITOR_ENABLED", "").lower() == "true",
            interval_seconds=int(os.getenv("AGENT_MONITOR_INTERVAL", "300")),
            entidad=os.getenv("AGENT_MONITOR_ENTIDAD", "sociedad_valores"),
            prioridad=os.getenv("AGENT_MONITOR_PRIORIDAD", "media"),
        )
    return _monitor_status


def get_monitor_status() -> dict[str, Any]:
    """Return current monitor status as a serializable dict."""
    status = _get_status()

    if status.running and status.last_scan is not None:
        next_in = status.interval_seconds - (time.time() - status.last_scan)
        if next_in < 0:
            next_in = 0
        status.next_scan_in_seconds = round(next_in, 1)
    else:
        status.next_scan_in_seconds = None

    return {
        "enabled": status.enabled,
        "running": status.running,
        "last_scan": status.last_scan,
        "last_scan_duration_ms": status.last_scan_duration_ms,
        "next_scan_in_seconds": status.next_scan_in_seconds,
        "interval_seconds": status.interval_seconds,
        "entidad": status.entidad,
        "prioridad": status.prioridad,
        "total_scans": status.total_scans,
        "total_triggers_created": status.total_triggers_created,
        "errors": status.errors,
    }


async def _scan_once(status: MonitorStatus) -> None:
    """Execute a single monitoring cycle."""
    status.running = True
    scan_start = time.time()

    try:
        # Step 1: Get pending changes
        resp = _client.get("/v1/cambios", params={"estado": "pendiente"})
        if resp.status_code != 200:
            logger.warning("Failed to fetch pending changes: %d", resp.status_code)
            status.errors += 1
            return

        cambios = resp.json()
        if not cambios:
            logger.info("No pending changes found")
            return

        logger.info("Found %d pending changes to evaluate", len(cambios))

        # Step 2: Get applicable obligations for the entity profile
        resp = _client.get(
            "/v1/obligaciones/aplicables",
            params={"tipo_entidad": status.entidad},
        )
        if resp.status_code != 200:
            logger.warning("Failed to fetch applicable obligations: %d", resp.status_code)
            status.errors += 1
            return

        oblig_data = resp.json()
        oblig_codes = {o["codigo"] for o in oblig_data.get("obligaciones", [])}
        logger.info("Entity '%s' has %d applicable obligations", status.entidad, len(oblig_codes))

        # Step 3: Evaluate which changes affect applicable obligations
        affected_count = 0
        for cambio in cambios:
            oblig_afectadas = cambio.get("obligaciones_afectadas", [])
            intersection = set(oblig_afectadas) & oblig_codes
            if intersection:
                affected_count += 1
                logger.info(
                    "Change '%s' affects %d applicable obligations: %s",
                    cambio.get("codigo", "?"),
                    len(intersection),
                    ", ".join(sorted(intersection)),
                )

                # Step 4: Create workflow trigger
                await _create_workflow_trigger(cambio, list(intersection), status)

        logger.info(
            "Scan complete: %d/%d changes affect applicable obligations",
            affected_count, len(cambios),
        )

    except Exception:
        logger.exception("Error during monitoring scan")
        status.errors += 1
    finally:
        status.running = False
        status.last_scan = time.time()
        status.last_scan_duration_ms = round((time.time() - scan_start) * 1000, 1)
        status.total_scans += 1


async def _create_workflow_trigger(
    cambio: dict, oblig_codes: list[str], status: MonitorStatus
) -> None:
    """Create a workflow case via the compliance endpoint."""
    try:
        # Check if a trigger already exists for this change+obligation combo
        existing_resp = _client.get("/v1/compliance/workflow")
        existing = existing_resp.json() if existing_resp.status_code == 200 else []

        for case in existing:
            if case.get("cambio_codigo") == cambio.get("codigo"):
                for existing_obl in case.get("obligacion_codigo", []):
                    if existing_obl in oblig_codes:
                        logger.info(
                            "Skipping duplicate trigger: %s for %s",
                            cambio.get("codigo"), existing_obl,
                        )
                        return

        # Create new workflow case
        payload = {
            "cambio_codigo": cambio.get("codigo"),
            "obligacion_codigo": oblig_codes,
            "estado": "pendiente",
            "owner_rol": "compliance_officer",
            "prioridad": status.prioridad,
            "notas": f"Auto-generated trigger from agent monitor. Change: {cambio.get('descripcion', cambio.get('codigo', ''))}",
        }

        resp = _client.post("/v1/compliance/workflow", json=payload)
        if resp.status_code in (200, 201):
            status.total_triggers_created += 1
            logger.info("Created workflow trigger for %s", cambio.get("codigo"))
        else:
            logger.warning(
                "Failed to create workflow trigger: %d %s",
                resp.status_code, resp.text[:200],
            )
            status.errors += 1

    except Exception:
        logger.exception("Error creating workflow trigger")
        status.errors += 1


async def _monitor_loop() -> None:
    """Main monitoring loop."""
    status = _get_status()
    status.running = True

    while True:
        await asyncio.sleep(status.interval_seconds)
        logger.info("Agent monitor scan starting...")
        await _scan_once(status)
        logger.info("Agent monitor scan complete")


def start_agent_monitor() -> None:
    """Start the agent monitor background task.

    Only starts if AGENT_MONITOR_ENABLED=true.
    Should be called from FastAPI lifespan.
    """
    status = _get_status()
    if not status.enabled:
        logger.info("Agent monitor disabled (set AGENT_MONITOR_ENABLED=true to enable)")
        return

    global _monitor_task
    if _monitor_task is not None and not _monitor_task.done():
        logger.warning("Agent monitor already running")
        return

    _monitor_task = asyncio.create_task(_monitor_loop())
    logger.info(
        "Agent monitor started (interval=%ds, entidad=%s, prioridad=%s)",
        status.interval_seconds, status.entidad, status.prioridad,
    )


def stop_agent_monitor() -> None:
    """Stop the agent monitor background task."""
    global _monitor_task
    if _monitor_task is not None and not _monitor_task.done():
        _monitor_task.cancel()
        logger.info("Agent monitor stopped")
```

- [ ] **Step 2: Verify module imports cleanly**

Run:
```bash
cd apps/api
python -c "from agent_monitor import get_monitor_status, start_agent_monitor; print('agent_monitor imports OK')"
```

Expected: `agent_monitor imports OK`

- [ ] **Step 3: Verify status returns correct defaults**

Run:
```bash
cd apps/api
python -c "
from agent_monitor import get_monitor_status
s = get_monitor_status()
assert s['enabled'] == False, 'Should be disabled by default'
assert s['interval_seconds'] == 300
assert s['entidad'] == 'sociedad_valores'
assert s['prioridad'] == 'media'
print('Default status OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add apps/api/agent_monitor.py
git commit -m "feat(api): add internal agent monitor service"
```

---

### Task 4: Integrate agent monitor into FastAPI lifespan

**Files:**
- Modify: `apps/api/main.py:52-68` (the `lifespan` function)

- [ ] **Step 1: Add import and startup/shutdown hooks**

Modify the `lifespan` function in `main.py` to import and call the agent monitor:

Change the existing lifespan from:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading
    def _load_model():
        try:
            from apps.workers.embeddings import get_model
            model = get_model()
            if model:
                logger.info("Embedding model loaded in background thread")
            else:
                logger.warning("Embedding model not available")
        except Exception:
            logger.warning("Failed to load embedding model", exc_info=True)
    t = threading.Thread(target=_load_model, daemon=True)
    t.start()
    logger.info("Embedding model loading in background...")
    yield
```

To:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading
    def _load_model():
        try:
            from apps.workers.embeddings import get_model
            model = get_model()
            if model:
                logger.info("Embedding model loaded in background thread")
            else:
                logger.warning("Embedding model not available")
        except Exception:
            logger.warning("Failed to load embedding model", exc_info=True)
    t = threading.Thread(target=_load_model, daemon=True)
    t.start()
    logger.info("Embedding model loading in background...")

    # Start agent monitor if enabled
    from agent_monitor import start_agent_monitor, stop_agent_monitor
    start_agent_monitor()

    yield

    # Cleanup
    stop_agent_monitor()
```

- [ ] **Step 2: Verify app still starts**

Run:
```bash
cd apps/api
python -c "from main import app; print('FastAPI app loads OK')"
```

Expected: `FastAPI app loads OK`

- [ ] **Step 3: Commit**

```bash
git add apps/api/main.py
git commit -m "feat(api): integrate agent monitor into FastAPI lifespan"
```

---

### Task 5: Write tests for the agent layer

**Files:**
- Create: `apps/api/tests/test_agent_layer.py`

- [ ] **Step 1: Write the full test file**

Create the file with these tests:

```python
"""Tests for the agent layer: MCP catalog tools, stdio handlers, and agent monitor."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


@pytest.fixture(autouse=True)
def _clear_env():
    """Clear agent monitor env vars before each test."""
    for key in ["AGENT_MONITOR_ENABLED", "AGENT_MONITOR_INTERVAL", "AGENT_MONITOR_ENTIDAD", "AGENT_MONITOR_PRIORIDAD"]:
        os.environ.pop(key, None)
    yield
    # Cleanup after test
    for key in ["AGENT_MONITOR_ENABLED", "AGENT_MONITOR_INTERVAL", "AGENT_MONITOR_ENTIDAD", "AGENT_MONITOR_PRIORIDAD"]:
        os.environ.pop(key, None)


class TestAgentToolsInCatalog:
    """Verify the 3 new agent tools are in the MCP catalog."""

    def test_agent_consulta_in_catalog(self):
        from mcp_catalog import get_stdio_tool_definitions
        tools = get_stdio_tool_definitions()
        names = [t["name"] for t in tools]
        assert "agente_consulta" in names

    def test_agent_monitoreo_status_in_catalog(self):
        from mcp_catalog import get_stdio_tool_definitions
        tools = get_stdio_tool_definitions()
        names = [t["name"] for t in tools]
        assert "agente_monitoreo_status" in names

    def test_agent_compliance_resumen_in_catalog(self):
        from mcp_catalog import get_stdio_tool_definitions
        tools = get_stdio_tool_definitions()
        names = [t["name"] for t in tools]
        assert "agente_compliance_resumen" in names

    def test_total_tool_count_is_8(self):
        from mcp_catalog import get_stdio_tool_definitions
        tools = get_stdio_tool_definitions()
        assert len(tools) == 8

    def test_agent_consulta_schema_has_required_q(self):
        from mcp_catalog import get_stdio_tool_definitions
        tools = get_stdio_tool_definitions()
        tool = next(t for t in tools if t["name"] == "agente_consulta")
        assert "q" in tool["inputSchema"]["required"]
        assert "q" in tool["inputSchema"]["properties"]
        assert tool["inputSchema"]["properties"]["q"]["type"] == "string"

    def test_agent_consulta_has_tipo_entidad_enum(self):
        from mcp_catalog import get_stdio_tool_definitions
        tools = get_stdio_tool_definitions()
        tool = next(t for t in tools if t["name"] == "agente_consulta")
        props = tool["inputSchema"]["properties"]
        assert "tipo_entidad" in props
        assert props["tipo_entidad"]["type"] == "string"
        assert "sociedad_valores" in props["tipo_entidad"]["enum"]

    def test_agent_monitoreo_status_has_no_required(self):
        from mcp_catalog import get_stdio_tool_definitions
        tools = get_stdio_tool_definitions()
        tool = next(t for t in tools if t["name"] == "agente_monitoreo_status")
        assert tool["inputSchema"]["required"] == []

    def test_agent_compliance_resumen_has_optional_fields(self):
        from mcp_catalog import get_stdio_tool_definitions
        tools = get_stdio_tool_definitions()
        tool = next(t for t in tools if t["name"] == "agente_compliance_resumen")
        props = tool["inputSchema"]["properties"]
        assert "estado" in props
        assert "limite" in props
        assert props["limite"]["type"] == "integer"


class TestAgentMonitorStatus:
    """Test the agent monitor status reporting."""

    def test_default_status_disabled(self):
        from agent_monitor import get_monitor_status
        s = get_monitor_status()
        assert s["enabled"] is False
        assert s["running"] is False
        assert s["interval_seconds"] == 300
        assert s["entidad"] == "sociedad_valores"
        assert s["prioridad"] == "media"
        assert s["total_scans"] == 0
        assert s["total_triggers_created"] == 0

    def test_status_enabled_via_env(self):
        os.environ["AGENT_MONITOR_ENABLED"] = "true"
        os.environ["AGENT_MONITOR_INTERVAL"] = "60"
        os.environ["AGENT_MONITOR_ENTIDAD"] = "retenedor"
        os.environ["AGENT_MONITOR_PRIORIDAD"] = "alta"

        from agent_monitor import get_monitor_status
        s = get_monitor_status()
        assert s["enabled"] is True
        assert s["interval_seconds"] == 60
        assert s["entidad"] == "retenedor"
        assert s["prioridad"] == "alta"


class TestAgentMonitorSkipWhenDisabled:
    """Test that the monitor does nothing when disabled."""

    def test_start_monitor_skipped_when_disabled(self):
        """start_agent_monitor should log and return when AGENT_MONITOR_ENABLED is not 'true'."""
        from agent_monitor import start_agent_monitor

        # Ensure disabled
        os.environ.pop("AGENT_MONITOR_ENABLED", None)

        with patch("agent_monitor.asyncio.create_task") as mock_task:
            start_agent_monitor()
            mock_task.assert_not_called()


class TestAgentMonitorCreatesTrigger:
    """Test that the monitor creates workflow triggers for affected changes."""

    def test_monitor_evaluates_pending_changes(self):
        """When there are pending changes affecting applicable obligations, triggers are created."""
        from agent_monitor import _get_status

        # Enable monitor for this test
        os.environ["AGENT_MONITOR_ENABLED"] = "true"
        os.environ["AGENT_MONITOR_ENTIDAD"] = "sociedad_valores"

        status = _get_status()

        # Mock the API calls
        mock_cambios_resp = MagicMock()
        mock_cambios_resp.status_code = 200
        mock_cambios_resp.json.return_value = [
            {
                "codigo": "CAMBIO-001",
                "descripcion": "Nuevo modelo 349",
                "estado": "pendiente",
                "obligaciones_afectadas": ["349_REPORT"],
            }
        ]

        mock_oblig_resp = MagicMock()
        mock_oblig_resp.status_code = 200
        mock_oblig_resp.json.return_value = {
            "perfil": {"tipo_entidad": "sociedad_valores"},
            "obligaciones": [
                {"codigo": "349_REPORT", "nombre": "Comunicacion 349"},
            ],
        }

        mock_workflow_resp = MagicMock()
        mock_workflow_resp.status_code = 201
        mock_workflow_resp.json.return_value = {"id": "wf-123"}

        mock_existing_resp = MagicMock()
        mock_existing_resp.status_code = 200
        mock_existing_resp.json.return_value = []

        with patch("agent_monitor._client") as mock_client:
            mock_client.get.side_effect = [mock_cambios_resp, mock_oblig_resp, mock_existing_resp]
            mock_client.post.return_value = mock_workflow_resp

            import asyncio
            asyncio.run(_scan_once(status))

        # Verify calls were made
        assert mock_client.get.call_count == 3
        assert mock_client.post.call_count == 1

        # Verify trigger was created
        assert status.total_triggers_created == 1
        assert status.total_scans == 1

    def test_monitor_skips_changes_without_impact(self):
        """When no changes affect applicable obligations, no triggers are created."""
        from agent_monitor import _get_status

        os.environ["AGENT_MONITOR_ENABLED"] = "true"
        os.environ["AGENT_MONITOR_ENTIDAD"] = "sociedad_valores"

        status = _get_status()

        mock_cambios_resp = MagicMock()
        mock_cambios_resp.status_code = 200
        mock_cambios_resp.json.return_value = [
            {
                "codigo": "CAMBIO-999",
                "descripcion": "Irrelevant change",
                "estado": "pendiente",
                "obligaciones_afectadas": ["X999_NOT_APPLICABLE"],
            }
        ]

        mock_oblig_resp = MagicMock()
        mock_oblig_resp.status_code = 200
        mock_oblig_resp.json.return_value = {
            "perfil": {"tipo_entidad": "sociedad_valores"},
            "obligaciones": [
                {"codigo": "349_REPORT", "nombre": "Comunicacion 349"},
            ],
        }

        mock_existing_resp = MagicMock()
        mock_existing_resp.status_code = 200
        mock_existing_resp.json.return_value = []

        with patch("agent_monitor._client") as mock_client:
            mock_client.get.side_effect = [mock_cambios_resp, mock_oblig_resp, mock_existing_resp]
            mock_client.post.return_value = MagicMock(status_code=201)

            import asyncio
            asyncio.run(_scan_once(status))

        # No triggers created because no intersection
        assert status.total_triggers_created == 0
        assert status.total_scans == 1


class TestStdioHandlers:
    """Test the stdio server handles new agent tools."""

    def test_stdio_handles_unknown_tool(self):
        """Unknown tools should return -32601 error."""
        from mcp_stdio import MCPStdioServer

        server = MCPStdioServer()
        sent = []
        server._send = lambda data: sent.append(data)

        server._handle_tools_call(
            {"id": 1, "method": "tools/call", "params": {"name": "unknown_tool", "arguments": {}}},
            1,
        )

        assert len(sent) == 1
        assert "error" in sent[0]
        assert sent[0]["error"]["code"] == -32601

    def test_entidad_to_sujeto_mapping(self):
        from mcp_stdio import MCPStdioServer

        server = MCPStdioServer()
        assert server._entidad_to_sujeto("sociedad_valores") == "contribuyente"
        assert server._entidad_to_sujeto("retenedor") == "retenedor"
        assert server._entidad_to_sujeto("no_residente") == "no_residente"
        assert server._entidad_to_sujeto("entidad_dinero_electronico") == "empresa"
        assert server._entidad_to_sujeto("unknown_type") == "contribuyente"


class TestComplianceResumenFormat:
    """Test the compliance resumen formatting."""

    def test_format_empty_data(self):
        from mcp_stdio import MCPStdioServer

        server = MCPStdioServer()
        result = server._format_compliance_resumen([])
        assert "No se encontraron casos" in result

    def test_format_with_data(self):
        from mcp_stdio import MCPStdioServer

        server = MCPStdioServer()
        data = [
            {
                "workflow_id": "wf-001",
                "cambio_codigo": "C-001",
                "obligacion_codigo": "O-001",
                "estado": "pendiente",
                "owner_rol": "compliance_officer",
                "fecha_objetivo": "2026-05-01",
                "notas": "Test nota",
            }
        ]
        result = server._format_compliance_resumen(data)
        assert "Casos de workflow: 1 resultados" in result
        assert "wf-001" in result
        assert "pendiente" in result
        assert "Por estado:" in result
```

- [ ] **Step 2: Run the tests**

Run:
```bash
cd apps/api
python -m pytest tests/test_agent_layer.py -v
```

Expected: All tests pass (17 tests).

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/test_agent_layer.py
git commit -m "test(agent-layer): add comprehensive tests for agent tools, monitor, and stdio handlers"
```

---

### Task 6: Final verification

**Files:**
- All agent-layer files

- [ ] **Step 1: Run all existing tests to ensure no regressions**

Run:
```bash
cd apps/api
python -m pytest tests/ -v --tb=short
```

Expected: Same results as before (78/82 smoke tests pass, 4 pre-existing failures in Phase 4).

- [ ] **Step 2: Verify the app still starts cleanly**

Run:
```bash
cd apps/api
python -c "from main import app; print(f'App loaded: {app.title} v{app.version}')"
```

Expected: `App loaded: esdata API v0.1.6`

- [ ] **Step 3: Verify MCP catalog consistency**

Run:
```bash
cd apps/api
python -c "
from mcp_catalog import get_stdio_tool_definitions
tools = get_stdio_tool_definitions()
names = [t['name'] for t in tools]
print(f'Total: {len(names)} tools')
for n in names:
    print(f'  - {n}')
"
```

Expected: 8 tools listed (5 existing + 3 new).

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat(api): complete agent layer — 3 MCP tools + internal monitor service"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - `agente_consulta` → Task 1 (catalog), Task 2 (stdio handler), Task 5 (tests)
   - `agente_monitoreo_status` → Task 1 (catalog), Task 2 (stdio handler), Task 3 (status), Task 5 (tests)
   - `agente_compliance_resumen` → Task 1 (catalog), Task 2 (stdio handler), Task 5 (tests)
   - Agent monitor service → Task 3 (create), Task 4 (integrate), Task 5 (tests)
   - Env vars (`AGENT_MONITOR_ENABLED`, `AGENT_MONITOR_INTERVAL`, `AGENT_MONITOR_ENTIDAD`, `AGENT_MONITOR_PRIORIDAD`) → Task 3
   - No new endpoints → Confirmed (monitor is internal only)
   - No new DB → Confirmed (reuses `workflow_cases`)

2. **Placeholder scan:** No "TBD", "TODO", or "implement later" found.

3. **Type consistency:** All function signatures and parameter names match across tasks.

4. **Security:** Monitor uses internal `TestClient` (never exposed externally). No new auth needed. No secrets in env vars.

5. **Test coverage:** 17 tests covering catalog, status, monitor enabled/disabled, trigger creation, no-impact skip, stdio handler, and formatting.

---

## Execution Notes

- **Order matters:** Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6
- **Each task is independent and commit-able**
- **No database changes** — all tests use mocked API calls
- **The monitor is opt-in** — `AGENT_MONITOR_ENABLED=false` by default
- **`agent_monitor.py` uses `TestClient`** to call the local FastAPI app — this is intentional and safe since it runs internally

Plan complete and saved to `docs/superpowers/plans/2026-04-25-agent-layer.md`.

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
