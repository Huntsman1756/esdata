"""Tests for MiCA emisor_token MCP routing and descriptions."""

from __future__ import annotations


class TestMCPEmisorTokenRouting:
    """Routing policy covers ART/EMT token issuer queries."""

    def test_routing_policy_contains_emisor_token(self):
        from mcp_catalog import MCP_TOOL_ROUTING_POLICY

        assert "emisor_token" in MCP_TOOL_ROUTING_POLICY
        assert "ART" in MCP_TOOL_ROUTING_POLICY
        assert "EMT" in MCP_TOOL_ROUTING_POLICY

    def test_routing_policy_contains_white_paper_trigger(self):
        from mcp_catalog import MCP_TOOL_ROUTING_POLICY

        assert "white paper" in MCP_TOOL_ROUTING_POLICY
        assert "ficha referenciada" in MCP_TOOL_ROUTING_POLICY

    def test_routing_policy_mentions_corpus_gap(self):
        from mcp_catalog import MCP_TOOL_ROUTING_POLICY

        assert "corpus documental" in MCP_TOOL_ROUTING_POLICY
        assert "obtener_documentos_cnmv_perfil('emisor_token')" in MCP_TOOL_ROUTING_POLICY

    def test_routing_policy_keeps_no_inventar(self):
        from mcp_catalog import MCP_TOOL_ROUTING_POLICY

        assert "NO inventar" in MCP_TOOL_ROUTING_POLICY or "no inventar" in MCP_TOOL_ROUTING_POLICY


class TestToolDescriptionEmisorToken:
    """obtener_obligaciones_perfil exposes emisor_token explicitly."""

    def test_tool_description_includes_emisor_token(self):
        from mcp_tools_perfil import OBTENER_OBLIGACIONES_PERFIL

        assert "emisor_token" in OBTENER_OBLIGACIONES_PERFIL.description
        assert "ART" in OBTENER_OBLIGACIONES_PERFIL.description
        assert "EMT" in OBTENER_OBLIGACIONES_PERFIL.description

    def test_tool_parameters_include_emisor_token(self):
        from mcp_tools_perfil import OBTENER_OBLIGACIONES_PERFIL

        assert "emisor_token" in OBTENER_OBLIGACIONES_PERFIL.parameters["perfil_codigo"]["enum"]

    def test_calendario_parameters_include_emisor_token(self):
        from mcp_tools_perfil import CALENDARIO_OBLIGACIONES_PERFIL

        assert "emisor_token" in CALENDARIO_OBLIGACIONES_PERFIL.parameters["perfil_codigo"]["enum"]

    def test_perfil_codigo_literal_includes_emisor_token(self):
        import mcp_tools_perfil

        assert "emisor_token" in mcp_tools_perfil.PerfilCodigo.__args__
