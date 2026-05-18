from __future__ import annotations

import json
import os
import subprocess
import sys

from mcp_catalog import get_stdio_tool_definitions


def _tools_by_name() -> dict[str, dict]:
    return {tool["name"]: tool for tool in get_stdio_tool_definitions()}


def test_stdio_tools_list_returns_core_five_tools() -> None:
    tools = _tools_by_name()

    assert {
        "listar_perfiles_entidad",
        "obtener_obligaciones_perfil",
        "calendario_obligaciones_perfil",
        "buscar_modelos_aeat_catalogo",
        "buscar_norma_eu",
    } <= set(tools)


def test_calendario_description_length_gt_300_in_stdio_output() -> None:
    description = _tools_by_name()["calendario_obligaciones_perfil"]["description"]

    assert len(description) > 300


def test_obtener_obligaciones_description_length_gt_300_in_stdio_output() -> None:
    description = _tools_by_name()["obtener_obligaciones_perfil"]["description"]

    assert len(description) > 300


def test_no_core_stdio_tool_description_is_too_short() -> None:
    tools = _tools_by_name()

    for name in (
        "listar_perfiles_entidad",
        "obtener_obligaciones_perfil",
        "calendario_obligaciones_perfil",
        "buscar_modelos_aeat_catalogo",
        "buscar_norma_eu",
    ):
        assert len(tools[name]["description"]) >= 100


def test_stdio_tools_list_subprocess_returns_descriptions() -> None:
    env = os.environ.copy()
    env["APP_ENV"] = "test"
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

    completed = subprocess.run(
        [sys.executable, "apps/api/mcp_stdio.py"],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        env=env,
        timeout=15,
        check=True,
    )
    stdout = completed.stdout.decode("utf-8")
    _, _, body = stdout.partition("\r\n\r\n")
    assert body, stdout
    data = json.loads(body)
    tools = {tool["name"]: tool for tool in data["result"]["tools"]}

    assert len(tools["calendario_obligaciones_perfil"]["description"]) > 300
    assert len(tools["obtener_obligaciones_perfil"]["description"]) > 300
