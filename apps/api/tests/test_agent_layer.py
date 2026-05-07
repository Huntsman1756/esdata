"""Tests for the agent layer: MCP catalog tools, stdio handlers, and agent monitor."""

import os
import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


@pytest.fixture(autouse=True)
def _clear_env():
    """Clear agent monitor env vars and reset cached status before each test."""
    for key in [
        "AGENT_MONITOR_ENABLED",
        "AGENT_MONITOR_INTERVAL",
        "AGENT_MONITOR_ENTIDAD",
        "AGENT_MONITOR_PRIORIDAD",
    ]:
        os.environ.pop(key, None)
    yield
    # Cleanup: clear env vars and reset singleton
    for key in [
        "AGENT_MONITOR_ENABLED",
        "AGENT_MONITOR_INTERVAL",
        "AGENT_MONITOR_ENTIDAD",
        "AGENT_MONITOR_PRIORIDAD",
    ]:
        os.environ.pop(key, None)
    import agent_monitor as am
    am._monitor_status = None
    am._monitor_task = None


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

        import agent_monitor as am
        am._monitor_status = None

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
        import agent_monitor as am

        # Enable monitor for this test
        os.environ["AGENT_MONITOR_ENABLED"] = "true"
        os.environ["AGENT_MONITOR_ENTIDAD"] = "sociedad_valores"

        # Reset cached singleton so env vars take effect
        am._monitor_status = None

        from agent_monitor import _get_status, _scan_once

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

        with patch.object(am, "_client") as mock_client:
            mock_client.get.side_effect = [
                mock_cambios_resp,
                mock_oblig_resp,
                mock_existing_resp,
            ]
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
        import agent_monitor as am

        os.environ["AGENT_MONITOR_ENABLED"] = "true"
        os.environ["AGENT_MONITOR_ENTIDAD"] = "sociedad_valores"

        am._monitor_status = None

        from agent_monitor import _get_status, _scan_once

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

        with patch.object(am, "_client") as mock_client:
            mock_client.get.side_effect = [
                mock_cambios_resp,
                mock_oblig_resp,
                mock_existing_resp,
            ]
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
            {
                "id": 1,
                "method": "tools/call",
                "params": {"name": "unknown_tool", "arguments": {}},
            },
            1,
        )

        assert len(sent) == 1
        assert "error" in sent[0]
        assert sent[0]["error"]["code"] == -32601

    def test_stdio_content_length_parser_consumes_header_separator(self, monkeypatch):
        from mcp_stdio import MCPStdioServer

        server = MCPStdioServer()
        sent = []
        server._send = lambda data: sent.append(data)

        payload = '{"jsonrpc":"2.0","id":1,"method":"ping"}'
        monkeypatch.setattr(sys, "stdin", io.StringIO(f"Content-Length: {len(payload)}\r\n\r\n{payload}"))

        server.run()

        assert sent == [{"jsonrpc": "2.0", "id": 1, "result": None}]

    def test_stdio_internal_requests_use_mcp_context(self, monkeypatch):
        from mcp_request_context import is_mcp_internal_request
        from mcp_stdio import MCPStdioServer

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"consulta": "q", "total_resultados": 0, "modelos": [], "resultados": []}

        observed = []

        def fake_get(*args, **kwargs):
            observed.append(is_mcp_internal_request())
            return FakeResponse()

        server = MCPStdioServer()
        server._send = lambda data: None
        monkeypatch.setattr("mcp_stdio.client.get", fake_get)

        server._handle_tools_call(
            {"params": {"name": "consulta_fiscal", "arguments": {"q": "iva"}}},
            1,
        )

        assert observed == [True]

    def test_stdio_audit_uses_error_status_for_unknown_tool(self, monkeypatch):
        from mcp_stdio import MCPStdioServer

        audited = []
        server = MCPStdioServer()
        server._send = lambda data: None

        def fake_log_mcp_call(**kwargs):
            audited.append(kwargs.get("status_code"))
            assert kwargs["response_payload"]["error"]["code"] == -32601

        monkeypatch.setattr("mcp_stdio._log_mcp_call", fake_log_mcp_call)

        server._handle_tools_call(
            {"params": {"name": "unknown_tool", "arguments": {}}},
            1,
        )

        assert audited == [500]

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
