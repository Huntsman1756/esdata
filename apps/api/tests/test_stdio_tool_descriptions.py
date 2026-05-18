from __future__ import annotations

from mcp_catalog import get_stdio_tool_definitions


def _tools_by_name() -> dict[str, dict]:
    return {tool["name"]: tool for tool in get_stdio_tool_definitions()}


def test_stdio_tools_list_contains_core_routing_tools() -> None:
    tools = _tools_by_name()
    for name in (
        "listar_perfiles_entidad",
        "obtener_obligaciones_perfil",
        "calendario_obligaciones_perfil",
        "buscar_modelos_aeat_catalogo",
        "buscar_norma_eu",
    ):
        assert name in tools


def test_obtener_obligaciones_description_blocks_calendar_and_catalog_fallback() -> None:
    description = _tools_by_name()["obtener_obligaciones_perfil"]["description"]

    assert "NO" in description
    assert "calendario_obligaciones_perfil" in description
    assert "buscar_modelos_aeat_catalogo" in description


def test_calendario_description_contains_period_triggers() -> None:
    description = _tools_by_name()["calendario_obligaciones_perfil"]["description"]

    assert "este trimestre" in description
    assert "Q3" in description


def test_catalog_description_says_it_does_not_indicate_obligation() -> None:
    description = _tools_by_name()["buscar_modelos_aeat_catalogo"]["description"]

    assert "NO indica si una entidad tiene obligación" in description


def test_all_core_stdio_descriptions_are_routing_grade() -> None:
    tools = _tools_by_name()
    for name in (
        "listar_perfiles_entidad",
        "obtener_obligaciones_perfil",
        "calendario_obligaciones_perfil",
        "buscar_modelos_aeat_catalogo",
        "buscar_norma_eu",
    ):
        assert len(tools[name]["description"]) > 100
