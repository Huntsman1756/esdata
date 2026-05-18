from __future__ import annotations

from mcp_catalog import MCP_TOOL_ROUTING_POLICY


def test_mcp_tool_routing_policy_is_importable() -> None:
    assert isinstance(MCP_TOOL_ROUTING_POLICY, str)


def test_mcp_tool_routing_policy_is_substantial() -> None:
    assert len(MCP_TOOL_ROUTING_POLICY) > 200


def test_mcp_tool_routing_policy_mentions_calendar_tool() -> None:
    assert "calendario_obligaciones_perfil" in MCP_TOOL_ROUTING_POLICY


def test_mcp_tool_routing_policy_contains_prohibitions() -> None:
    assert "NO" in MCP_TOOL_ROUTING_POLICY


def test_mcp_tool_routing_policy_contains_quarter_triggers() -> None:
    for trigger in ("este trimestre", "Q3", "qué vence"):
        assert trigger in MCP_TOOL_ROUTING_POLICY
