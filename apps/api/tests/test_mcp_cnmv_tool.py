import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app
from mcp_catalog import (
    HTTP_MCP_OPERATIONS,
    MCP_TOOL_ROUTING_POLICY,
    get_stdio_tool_definitions,
)


def test_mcp_catalog_includes_cnmv_perfil_http_operation():
    assert "obtener_documentos_cnmv_perfil" in HTTP_MCP_OPERATIONS


def test_stdio_tools_list_includes_cnmv_perfil_tool():
    tools = {tool["name"]: tool for tool in get_stdio_tool_definitions()}

    assert len(tools) >= 6
    assert "obtener_documentos_cnmv_perfil" in tools
    description = tools["obtener_documentos_cnmv_perfil"]["description"]
    assert "circulares" in description
    assert "guias tecnicas" in description
    assert "obtener_obligaciones_perfil" in description


def test_openapi_exposes_cnmv_perfil_operation_id():
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/v1/cnmv/perfil/{perfil_codigo}"]["get"]
    assert operation["operationId"] == "obtener_documentos_cnmv_perfil"


def test_routing_policy_mentions_cnmv_perfil_tool():
    assert "obtener_documentos_cnmv_perfil" in MCP_TOOL_ROUTING_POLICY
    assert "modelos normalizados ESI" in MCP_TOOL_ROUTING_POLICY
