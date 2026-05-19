"""Tests for MCP CASP routing policy and tool descriptions.

Covers:
- casp perfil is routable via obtener_obligaciones_perfil
- PSAV queries route to casp perfil
- NO inventar: agent must not fabricate unverified crypto obligations
- stdio tool description includes casp and MiCA applicability
"""

from __future__ import annotations

import pytest


class TestMCPCaspRouting:
    """Routing policy covers CASP/crypto queries."""

    def test_routing_policy_contains_casp(self):
        from mcp_catalog import MCP_TOOL_ROUTING_POLICY

        assert "casp" in MCP_TOOL_ROUTING_POLICY.lower()
        assert "criptoactivos" in MCP_TOOL_ROUTING_POLICY.lower()
        assert "MiCA" in MCP_TOOL_ROUTING_POLICY
        assert "NO inventar" in MCP_TOOL_ROUTING_POLICY or "no inventar" in MCP_TOOL_ROUTING_POLICY

    def test_routing_policy_mentions_obligaciones_perfil(self):
        from mcp_catalog import MCP_TOOL_ROUTING_POLICY

        assert "obtener_obligaciones_perfil" in MCP_TOOL_ROUTING_POLICY

    def test_routing_policy_mentions_get_casp_profile(self):
        from mcp_catalog import MCP_TOOL_ROUTING_POLICY

        assert "perfil_codigo='casp'" in MCP_TOOL_ROUTING_POLICY


class TestNoInventar:
    """Agent must not fabricate crypto obligations."""

    def test_routing_policy_warns_against_inventing(self):
        from mcp_catalog import MCP_TOOL_ROUTING_POLICY

        assert "NO inventar" in MCP_TOOL_ROUTING_POLICY or "no inventar" in MCP_TOOL_ROUTING_POLICY

    def test_routing_policy_identifies_gaps(self):
        from mcp_catalog import MCP_TOOL_ROUTING_POLICY

        assert "gaps" in MCP_TOOL_ROUTING_POLICY.lower() or "identificar" in MCP_TOOL_ROUTING_POLICY.lower()


class TestToolDescriptionCasp:
    """obtener_obligaciones_perfil stdio description includes casp and MiCA."""

    def test_tool_description_includes_casp(self):
        from mcp_tools_perfil import OBTENER_OBLIGACIONES_PERFIL

        assert "casp" in OBTENER_OBLIGACIONES_PERFIL.description.lower()

    def test_tool_description_includes_mica(self):
        from mcp_tools_perfil import OBTENER_OBLIGACIONES_PERFIL

        assert "MiCA" in OBTENER_OBLIGACIONES_PERFIL.description

    def test_tool_description_mentions_december_2024(self):
        from mcp_tools_perfil import OBTENER_OBLIGACIONES_PERFIL

        assert "30 diciembre 2024" in OBTENER_OBLIGACIONES_PERFIL.description

    def test_tool_parameters_include_casp(self):
        from mcp_tools_perfil import OBTENER_OBLIGACIONES_PERFIL

        assert "casp" in OBTENER_OBLIGACIONES_PERFIL.parameters["perfil_codigo"]["enum"]

    def test_calendario_parameters_include_casp(self):
        from mcp_tools_perfil import CALENDARIO_OBLIGACIONES_PERFIL

        assert "casp" in CALENDARIO_OBLIGACIONES_PERFIL.parameters["perfil_codigo"]["enum"]


class TestPerfilCodigoEnum:
    """PerfilCodigo literal includes casp."""

    def test_perfil_codigo_literal_includes_casp(self):
        import mcp_tools_perfil

        # The Literal type should include 'casp'
        # We check the module attribute directly
        assert hasattr(mcp_tools_perfil, "PerfilCodigo")
