#!/usr/bin/env python
"""Read-only MCP/API validation suite for scheduled maintenance checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import create_engine, text


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in (current.parent, *current.parents):
        if (parent / "apps" / "api").exists() and (parent / "scripts").exists():
            return parent
    return Path.cwd()


def _headers() -> dict[str, str]:
    api_key = os.getenv("ESDATA_API_KEY", "")
    return {"X-API-Key": api_key} if api_key else {}


def _mcp_headers() -> dict[str, str]:
    api_key = os.getenv("MCP_API_KEY") or os.getenv("ESDATA_API_KEY", "")
    return {"X-API-Key": api_key} if api_key else {}


def _request_with_retry(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    max_attempts: int = 5,
    **kwargs: Any,
) -> httpx.Response:
    response: httpx.Response | None = None
    for attempt in range(1, max_attempts + 1):
        response = client.request(method, path, **kwargs)
        if response.status_code != 429:
            return response
        if attempt == max_attempts:
            return response
        retry_after = response.headers.get("Retry-After")
        try:
            delay = max(1.0, float(retry_after or 1))
        except ValueError:
            delay = 1.0
        time.sleep(delay)
    assert response is not None
    return response


def _check_get(
    client: httpx.Client,
    path: str,
    required_text: str | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = _request_with_retry(client, "GET", path, params=params, headers=_headers())
    ok = response.status_code == 200
    if required_text is not None:
        ok = ok and required_text in response.text
    return {
        "path": path,
        "params": params or {},
        "status_code": response.status_code,
        "ok": ok,
    }


def _check_json_contract(
    client: httpx.Client,
    path: str,
    params: dict[str, Any] | None,
    validator,
    name: str,
) -> dict[str, Any]:
    response = _request_with_retry(client, "GET", path, params=params, headers=_headers())
    check: dict[str, Any] = {
        "name": name,
        "path": path,
        "params": params or {},
        "status_code": response.status_code,
        "ok": False,
    }
    if response.status_code != 200:
        check["error"] = response.text[:500]
        return check
    try:
        payload = response.json()
    except ValueError as exc:
        check["error"] = f"invalid_json: {exc}"
        return check

    ok, details = validator(payload)
    check["ok"] = ok
    check["details"] = details
    return check


def _check_mcp_transport(client: httpx.Client) -> dict[str, Any]:
    required_tools = {
        "consulta_fiscal",
        "list_modelos_por_supuesto",
        "list_domain_availability",
        "listar_perfiles_entidad",
        "obtener_obligaciones_perfil",
        "calendario_obligaciones_perfil",
        "buscar_norma_eu",
        "buscar_modelos_aeat_catalogo",
        "obtener_documentos_cnmv_perfil",
    }
    check: dict[str, Any] = {
        "name": "mcp_transport_tools_list",
        "path": "/mcp",
        "required_tools": sorted(required_tools),
        "ok": False,
    }
    headers = {
        "Accept": "text/event-stream",
        **_mcp_headers(),
    }
    try:
        # /mcp opens an SSE stream; do not wait for the response body to finish.
        if hasattr(client, "stream"):
            with client.stream("GET", "/mcp", headers=headers) as handshake:
                session_id = handshake.headers.get("mcp-session-id") or handshake.headers.get(
                    "Mcp-Session-Id"
                )
                check["handshake_status_code"] = handshake.status_code
                check["has_session_id"] = bool(session_id)
                if not session_id:
                    check["error"] = "missing_mcp_session_id"
                    return check
                if handshake.status_code not in {200, 400}:
                    check["error"] = f"unexpected_handshake_status: {handshake.status_code}"
                    return check
        else:
            handshake = _request_with_retry(client, "GET", "/mcp", headers=headers)
            session_id = handshake.headers.get("mcp-session-id") or handshake.headers.get(
                "Mcp-Session-Id"
            )
            check["handshake_status_code"] = handshake.status_code
            check["has_session_id"] = bool(session_id)
            if not session_id:
                check["error"] = "missing_mcp_session_id"
                return check
            if handshake.status_code not in {200, 400}:
                check["error"] = f"unexpected_handshake_status: {handshake.status_code}"
                return check
    except httpx.HTTPError as exc:
        check["error"] = f"handshake_failed: {exc}"
        return check

    rpc_headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Session-ID": session_id,
        **_mcp_headers(),
    }
    initialize = _request_with_retry(
        client,
        "POST",
        "/mcp",
        headers=rpc_headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "esdata-maintenance", "version": "1.0"},
            },
        },
    )
    check["initialize_status_code"] = initialize.status_code
    if initialize.status_code != 200:
        check["error"] = initialize.text[:500]
        return check

    tools = _request_with_retry(
        client,
        "POST",
        "/mcp",
        headers=rpc_headers,
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    check["tools_status_code"] = tools.status_code
    if tools.status_code != 200:
        check["error"] = tools.text[:500]
        return check

    try:
        payload = tools.json()
    except ValueError as exc:
        check["error"] = f"invalid_tools_json: {exc}"
        return check

    tool_names = {
        tool.get("name")
        for tool in ((payload.get("result") or {}).get("tools") or [])
        if isinstance(tool, dict)
    }
    missing = sorted(required_tools - tool_names)
    check["tool_count"] = len(tool_names)
    check["missing_tools"] = missing
    check["ok"] = not missing
    return check


def _check_stdio_tool_descriptions() -> dict[str, Any]:
    check: dict[str, Any] = {"name": "stdio_tool_description_routing_contract", "ok": False}
    try:
        root = _repo_root()
        api_path = root / "apps" / "api"
        if str(api_path) not in sys.path:
            sys.path.insert(0, str(api_path))
        from mcp_catalog import MCP_TOOL_ROUTING_POLICY, get_stdio_tool_definitions  # type: ignore

        tools = {tool.get("name"): tool for tool in get_stdio_tool_definitions()}
        expected = {
            "listar_perfiles_entidad",
            "obtener_obligaciones_perfil",
            "calendario_obligaciones_perfil",
            "buscar_norma_eu",
            "buscar_modelos_aeat_catalogo",
            "obtener_documentos_cnmv_perfil",
        }
        descriptions = {
            name: str((tools.get(name) or {}).get("description") or "") for name in expected
        }
        failures: list[dict[str, Any]] = []
        missing = sorted(expected - set(tools))
        if missing:
            failures.append({"check": "core_mcp_tools_registered", "missing": missing})
        for name, description in descriptions.items():
            if len(description) <= 100:
                failures.append(
                    {"check": "description_length_gt_100", "tool": name, "length": len(description)}
                )
        if "este trimestre" not in descriptions["calendario_obligaciones_perfil"]:
            failures.append({"check": "calendario_trigger_este_trimestre"})
        if "NO" not in descriptions["obtener_obligaciones_perfil"]:
            failures.append({"check": "obtener_obligaciones_no_prohibition"})
        if "calendario_obligaciones_perfil" not in descriptions["obtener_obligaciones_perfil"]:
            failures.append({"check": "obtener_mentions_calendar_tool"})
        if "NO indica si una entidad tiene obligación" not in descriptions["buscar_modelos_aeat_catalogo"]:
            failures.append({"check": "catalog_warning_no_obligation"})
        if "calendario_obligaciones_perfil" not in MCP_TOOL_ROUTING_POLICY:
            failures.append({"check": "routing_policy_importable"})
        if "obtener_documentos_cnmv_perfil" not in MCP_TOOL_ROUTING_POLICY:
            failures.append({"check": "cnmv_perfil_routing_policy"})
        if "circulares" not in descriptions["obtener_documentos_cnmv_perfil"]:
            failures.append({"check": "cnmv_perfil_description_circulares"})
        # MiCA CASP routing checks
        if "casp" not in MCP_TOOL_ROUTING_POLICY.lower():
            failures.append({"check": "routing_policy_contains_casp"})
        if "NO inventar" not in MCP_TOOL_ROUTING_POLICY and "no inventar" not in MCP_TOOL_ROUTING_POLICY:
            failures.append({"check": "routing_policy_no_inventar"})
        if "casp" not in descriptions.get("obtener_obligaciones_perfil", "").lower():
            failures.append({"check": "obtener_description_contains_casp"})
        if "MiCA" not in descriptions.get("obtener_obligaciones_perfil", ""):
            failures.append({"check": "obtener_description_contains_mica"})
        if "emisor_token" not in MCP_TOOL_ROUTING_POLICY:
            failures.append({"check": "routing_policy_contains_emisor_token"})
        if "emisor_token" not in descriptions.get("obtener_obligaciones_perfil", ""):
            failures.append({"check": "obtener_description_contains_emisor_token"})
        check.update(
            {
                "tool_count": len(tools),
                "description_lengths": {
                    name: len(description) for name, description in sorted(descriptions.items())
                },
                "failures": failures,
                "ok": not failures,
            }
        )
    except Exception as exc:
        check["error"] = str(exc)
    return check


def _check_db_scalar(database_url: str, name: str, sql: str, minimum: int) -> dict[str, Any]:
    check: dict[str, Any] = {"name": name, "ok": False, "minimum": minimum}
    try:
        engine = create_engine(database_url, future=True)
        with engine.connect() as conn:
            value = int(conn.execute(text(sql)).scalar() or 0)
    except Exception as exc:
        check["error"] = str(exc)
        return check
    check["value"] = value
    check["ok"] = value >= minimum
    return check


def _check_db_zero(database_url: str, name: str, sql: str) -> dict[str, Any]:
    check: dict[str, Any] = {"name": name, "ok": False, "expected": 0}
    try:
        engine = create_engine(database_url, future=True)
        with engine.connect() as conn:
            value = int(conn.execute(text(sql)).scalar() or 0)
    except Exception as exc:
        check["error"] = str(exc)
        return check
    check["value"] = value
    check["ok"] = value == 0
    return check


def _check_database_contracts() -> list[dict[str, Any]]:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return [{"name": "database_contracts_configured", "ok": False, "error": "DATABASE_URL missing"}]
    checks = [
        _check_db_scalar(
            database_url,
            "teac_resolucion_count_ge_500",
            "SELECT COUNT(*) FROM documento_interpretativo WHERE tipo_documento='resolucion_teac'",
            500,
        ),
        _check_db_scalar(
            database_url,
            "teac_url_oficial_coverage_ge_90_percent",
            """
            SELECT CASE
                WHEN COUNT(*) = 0 THEN 0
                ELSE FLOOR(100.0 * COUNT(*) FILTER (WHERE url_fuente IS NOT NULL) / COUNT(*))::int
            END
            FROM documento_interpretativo
            WHERE tipo_documento='resolucion_teac'
            """,
            90,
        ),
        _check_db_scalar(
            database_url,
            "sepblac_normativa_count_ge_5",
            "SELECT COUNT(*) FROM documento_interpretativo WHERE tipo_documento='normativa_sepblac'",
            5,
        ),
        _check_db_scalar(
            database_url,
            "sepblac_obligacion_count_ge_5",
            "SELECT COUNT(*) FROM documento_interpretativo WHERE tipo_documento='obligacion_sepblac'",
            5,
        ),
        _check_db_scalar(
            database_url,
            "sepblac_guia_count_ge_3",
            "SELECT COUNT(*) FROM documento_interpretativo WHERE tipo_documento='guia_operativa_sepblac'",
            3,
        ),
        _check_db_scalar(
            database_url,
            "rd_304_2014_article_count_ge_10",
            """
            SELECT COUNT(*)
            FROM articulo a JOIN norma n ON n.id=a.norma_id
            WHERE n.codigo='RD_304_2014'
            """,
            10,
        ),
        _check_db_scalar(
            database_url,
            "eu_norms_celex_count_ge_10",
            "SELECT COUNT(*) FROM norma WHERE celex IS NOT NULL AND tipo_norma IS NOT NULL",
            10,
        ),
        _check_db_scalar(
            database_url,
            "sociedad_valores_dora_obligation_ge_1",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='sociedad_valores'
              AND norma_codigo='32022R2554'
              AND source_url IS NOT NULL
            """,
            1,
        ),
        _check_db_scalar(
            database_url,
            "sociedad_valores_verified_ge_24",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='sociedad_valores'
              AND verified=true
            """,
            24,
        ),
        _check_db_zero(
            database_url,
            "all_profiles_pct_verified_ge_70",
            """
            SELECT COUNT(*)
            FROM (
                SELECT perfil_codigo,
                       100.0 * SUM(CASE WHEN verified THEN 1 ELSE 0 END)
                         / NULLIF(COUNT(*), 0) AS pct_verified
                FROM obligacion_perfil
                GROUP BY perfil_codigo
            ) profile_rates
            WHERE pct_verified < 70
            """,
        ),
        _check_db_scalar(
            database_url,
            "ifd_ifr_norms_loaded",
            "SELECT COUNT(*) FROM norma WHERE codigo IN ('32019R2033', '32019L2034')",
            2,
        ),
        _check_db_zero(
            database_url,
            "esi_prudential_not_primary_crr",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo IN ('sociedad_valores', 'agencia_valores')
              AND norma_codigo='32013R0575'
              AND descripcion ILIKE '%prudencial%'
            """,
        ),
        _check_db_zero(
            database_url,
            "modelo_289_uses_lgt_da22_ap1",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE descripcion ILIKE '%Modelo 289%'
              AND (
                  norma_codigo <> 'LGT'
                  OR articulo_referencia NOT LIKE 'DA 22.% ap. 1'
              )
            """,
        ),
        _check_db_zero(
            database_url,
            "evidence_limited_rows_have_notas",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE verified IS NOT true
              AND (notas IS NULL OR btrim(notas) = '')
            """,
        ),
        _check_db_scalar(
            database_url,
            "modelo_202_all_profiles_loaded",
            """
            SELECT COUNT(DISTINCT perfil_codigo)
            FROM obligacion_perfil
            WHERE modelo_aeat='202'
              AND perfil_codigo IN (
                  'sociedad_valores',
                  'agencia_valores',
                  'eaf',
                  'entidad_credito',
                  'empresa_servicios_pago',
                  'sgiic'
              )
            """,
            6,
        ),
        _check_db_scalar(
            database_url,
            "modelo_202_profiles_verified_or_fail_closed_6",
            """
            SELECT COUNT(DISTINCT perfil_codigo)
            FROM obligacion_perfil
            WHERE modelo_aeat='202'
              AND perfil_codigo IN (
                  'sociedad_valores',
                  'agencia_valores',
                  'eaf',
                  'entidad_credito',
                  'empresa_servicios_pago',
                  'sgiic'
              )
              AND (
                  (
                      verified IS true
                      AND source_hash IS NOT NULL
                      AND capture_date IS NOT NULL
                  )
                  OR (
                      verified IS NOT true
                      AND safe_to_answer IS NOT true
                      AND source_url IS NOT NULL
                      AND source_hash IS NULL
                      AND capture_date IS NOT NULL
                      AND notas ILIKE '%fail-closed until source_hash and capture_date are loaded%'
                  )
              )
            """,
            6,
        ),
        _check_db_zero(
            database_url,
            "trimestral_obligations_have_plazo",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE periodicidad='trimestral'
              AND plazo_descripcion IS NULL
            """,
        ),
        _check_db_scalar(
            database_url,
            "rts1_norma_loaded",
            "SELECT COUNT(*) FROM norma WHERE celex='32017R0587'",
            1,
        ),
        _check_db_scalar(
            database_url,
            "rts2_norma_loaded",
            "SELECT COUNT(*) FROM norma WHERE celex='32017R0583'",
            1,
        ),
        _check_db_scalar(
            database_url,
            "sociedad_valores_rts1_rts2_obligations_ge_4",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='sociedad_valores'
              AND norma_codigo IN ('32017R0587','32017R0583')
            """,
            4,
        ),
        _check_db_zero(
            database_url,
            "rts1_rts2_obligations_all_parcial",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE norma_codigo IN ('32017R0587','32017R0583')
              AND completeness <> 'parcial'
            """,
        ),
        _check_db_zero(
            database_url,
            "rts1_rts2_obligations_verified_or_fail_closed",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE norma_codigo IN ('32017R0587','32017R0583')
              AND NOT (
                  (
                      verified IS true
                      AND source_hash IS NOT NULL
                      AND capture_date IS NOT NULL
                  )
                  OR (
                      verified IS NOT true
                      AND safe_to_answer IS NOT true
                      AND completeness = 'parcial'
                      AND source_url ILIKE '%eur-lex%'
                      AND source_hash IS NULL
                      AND capture_date IS NOT NULL
                      AND notas ILIKE '%fail-closed until source_hash and capture_date are loaded%'
                  )
              )
            """,
        ),
        _check_db_zero(
            database_url,
            "rts1_rts2_obligations_source_url_eurlex",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE norma_codigo IN ('32017R0587','32017R0583')
              AND source_url NOT ILIKE '%eur-lex%'
            """,
        ),
        _check_db_zero(
            database_url,
            "eaf_has_zero_rts1_rts2_obligations",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='eaf'
              AND norma_codigo IN ('32017R0587','32017R0583')
            """,
        ),
        _check_db_zero(
            database_url,
            "empresa_servicios_pago_has_zero_rts1_rts2_obligations",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='empresa_servicios_pago'
              AND norma_codigo IN ('32017R0587','32017R0583')
            """,
        ),
        _check_db_scalar(
            database_url,
            "dora_rts_1774_norma_loaded",
            "SELECT COUNT(*) FROM norma WHERE celex='32024R1774'",
            1,
        ),
        _check_db_scalar(
            database_url,
            "dora_rts_1773_norma_loaded",
            "SELECT COUNT(*) FROM norma WHERE celex='32024R1773'",
            1,
        ),
        _check_db_zero(
            database_url,
            "dora_weak_duplicate_removed",
            "SELECT COUNT(*) FROM norma WHERE codigo='DORA_2022_2535'",
        ),
        _check_db_scalar(
            database_url,
            "agencia_valores_dora_obligations_ge_3",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='agencia_valores'
              AND norma_codigo='32022R2554'
            """,
            3,
        ),
        _check_db_scalar(
            database_url,
            "eaf_dora_obligations_ge_2",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='eaf'
              AND norma_codigo='32022R2554'
            """,
            2,
        ),
        _check_db_zero(
            database_url,
            "eaf_dora_obligations_all_parcial",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='eaf'
              AND norma_codigo='32022R2554'
              AND completeness <> 'parcial'
            """,
        ),
        _check_db_zero(
            database_url,
            "dora_weak_duplicate_no_obligation_references",
            "SELECT COUNT(*) FROM obligacion_perfil WHERE norma_codigo='DORA_2022_2535'",
        ),
        _check_db_zero(
            database_url,
            "dora_obligations_no_article_ranges",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE norma_codigo='32022R2554'
              AND (
                  articulo_referencia LIKE 'arts.%'
                  OR articulo_referencia LIKE '%-%'
              )
            """,
        ),
        _check_db_zero(
            database_url,
            "all_profiles_have_dora_obligation",
            """
            SELECT COUNT(*)
            FROM perfil_entidad pe
            WHERE pe.activo IS true
              AND pe.codigo NOT IN ('casp', 'emisor_token')
              AND NOT EXISTS (
                  SELECT 1
                  FROM obligacion_perfil op
                  WHERE op.perfil_codigo = pe.codigo
                    AND op.norma_codigo='32022R2554'
              )
            """,
        ),
        _check_db_scalar(
            database_url,
            "dora_art_28_30_profiles_ge_5",
            """
            SELECT COUNT(DISTINCT perfil_codigo)
            FROM obligacion_perfil
            WHERE norma_codigo='32022R2554'
              AND articulo_referencia IN ('art. 28','art. 30')
            """,
            5,
        ),
        # ── MiCA CASP (Sprint M) ──
        _check_db_scalar(
            database_url,
            "mica_canonical_norma_loaded",
            "SELECT COUNT(*) FROM norma WHERE celex='32023R1114' AND tipo_norma='reglamento_ue'",
            1,
        ),
        _check_db_zero(
            database_url,
            "mica_weak_duplicate_removed",
            "SELECT COUNT(*) FROM norma WHERE codigo='MICA_2023_1114'",
        ),
        _check_db_scalar(
            database_url,
            "casp_perfil_exists",
            "SELECT COUNT(*) FROM perfil_entidad WHERE codigo='casp'",
            1,
        ),
        _check_db_scalar(
            database_url,
            "casp_obligations_ge_6",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='casp'
              AND norma_codigo='32023R1114'
            """,
            6,
        ),
        _check_db_zero(
            database_url,
            "casp_obligations_verified_or_fail_closed",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='casp'
              AND norma_codigo='32023R1114'
              AND NOT (
                  (
                      verified IS true
                      AND source_hash IS NOT NULL
                      AND capture_date IS NOT NULL
                  )
                  OR (
                      verified IS NOT true
                      AND safe_to_answer IS NOT true
                      AND completeness = 'parcial'
                      AND source_url ILIKE '%eur-lex%'
                      AND source_hash IS NULL
                      AND capture_date IS NOT NULL
                      AND notas ILIKE '%fail-closed until source_hash and capture_date are loaded%'
                  )
              )
            """,
        ),
        _check_db_scalar(
            database_url,
            "mica_rts_loaded_ge_3",
            "SELECT COUNT(*) FROM norma WHERE norma_padre_celex='32023R1114'",
            3,
        ),
        _check_db_scalar(
            database_url,
            "casp_art_59_present",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='casp'
              AND norma_codigo='32023R1114'
              AND (articulo_referencia LIKE '%59%' OR articulo_referencia LIKE '%autorizaci%')
            """,
            1,
        ),
        _check_db_scalar(
            database_url,
            "casp_art_70_present",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='casp'
              AND norma_codigo='32023R1114'
              AND (articulo_referencia LIKE '%70%' OR articulo_referencia LIKE '%custodia%')
            """,
            1,
        ),
        _check_db_scalar(
            database_url,
            "casp_pbc_completeness_parcial",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='casp'
              AND norma_codigo='32023R1114'
              AND obligacion_tipo='PBC_FT'
              AND completeness='parcial'
            """,
            1,
        ),
        # MiCA token issuers (Sprint N)
        _check_db_scalar(
            database_url,
            "emisor_token_perfil_exists",
            "SELECT COUNT(*) FROM perfil_entidad WHERE codigo='emisor_token'",
            1,
        ),
        _check_db_scalar(
            database_url,
            "emisor_token_obligations_ge_8",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='emisor_token'
              AND norma_codigo='32023R1114'
            """,
            8,
        ),
        _check_db_zero(
            database_url,
            "emisor_token_obligations_verified_or_fail_closed",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='emisor_token'
              AND norma_codigo='32023R1114'
              AND NOT (
                  (
                      verified IS true
                      AND source_hash IS NOT NULL
                      AND capture_date IS NOT NULL
                  )
                  OR (
                      verified IS NOT true
                      AND safe_to_answer IS NOT true
                      AND completeness = 'parcial'
                      AND source_url ILIKE '%eur-lex%'
                      AND source_hash IS NULL
                      AND capture_date IS NOT NULL
                      AND notas ILIKE '%fail-closed until source_hash and capture_date are loaded%'
                  )
              )
            """,
        ),
        _check_db_scalar(
            database_url,
            "emisor_token_art_18_present",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='emisor_token'
              AND norma_codigo='32023R1114'
              AND articulo_referencia='art. 18'
            """,
            1,
        ),
        _check_db_scalar(
            database_url,
            "emisor_token_art_48_present",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='emisor_token'
              AND norma_codigo='32023R1114'
              AND articulo_referencia='art. 48'
            """,
            1,
        ),
        _check_db_scalar(
            database_url,
            "emisor_token_emt_obligations_parcial",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE perfil_codigo='emisor_token'
              AND norma_codigo='32023R1114'
              AND articulo_referencia IN ('art. 48', 'art. 51', 'art. 55')
              AND completeness='parcial'
            """,
            3,
        ),
        _check_db_scalar(
            database_url,
            "emisor_token_art_base_obligations_present_3",
            """
            SELECT COUNT(DISTINCT articulo_referencia)
            FROM obligacion_perfil
            WHERE perfil_codigo='emisor_token'
              AND norma_codigo='32023R1114'
              AND articulo_referencia IN ('art. 18', 'art. 19', 'art. 35')
            """,
            3,
        ),
        _check_db_scalar(
            database_url,
            "emisor_token_art_base_obligations_verified_or_fail_closed_3",
            """
            SELECT COUNT(DISTINCT articulo_referencia)
            FROM obligacion_perfil
            WHERE perfil_codigo='emisor_token'
              AND norma_codigo='32023R1114'
              AND articulo_referencia IN ('art. 18', 'art. 19', 'art. 35')
              AND (
                  (
                      verified IS true
                      AND source_hash IS NOT NULL
                      AND capture_date IS NOT NULL
                  )
                  OR (
                      verified IS NOT true
                      AND safe_to_answer IS NOT true
                      AND completeness = 'parcial'
                      AND source_url ILIKE '%eur-lex%'
                      AND source_hash IS NULL
                      AND capture_date IS NOT NULL
                      AND notas ILIKE '%fail-closed until source_hash and capture_date are loaded%'
                  )
              )
            """,
            3,
        ),
        _check_db_scalar(
            database_url,
            "obligacion_perfil_total_ge_190",
            "SELECT COUNT(*) FROM obligacion_perfil",
            190,
        ),
        _check_db_scalar(
            database_url,
            "modelo_289_normativa_ge_4",
            """
            SELECT COUNT(*)
            FROM modelo_normativa mn
            JOIN aeat_modelo am ON am.id = mn.modelo_id
            WHERE am.codigo='289'
            """,
            4,
        ),
        _check_db_scalar(
            database_url,
            "modelo_289_instrucciones_ge_5",
            """
            SELECT COUNT(*)
            FROM modelo_instruccion mi
            JOIN modelo_campana mc ON mc.id = mi.campana_id
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE am.codigo='289'
            """,
            5,
        ),
        _check_db_scalar(
            database_url,
            "modelo_289_reglas_inclusion_ge_6",
            """
            SELECT COUNT(*)
            FROM modelo_regla_inclusion mri
            JOIN modelo_campana mc ON mc.id = mri.campana_id
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE am.codigo='289'
            """,
            6,
        ),
        _check_db_scalar(
            database_url,
            "modelo_289_trigger_keywords_ge_8",
            """
            SELECT COUNT(*)
            FROM modelo_trigger_keyword mtk
            JOIN aeat_modelo am ON am.id = mtk.modelo_id
            WHERE am.codigo='289'
            """,
            8,
        ),
        _check_db_scalar(
            database_url,
            "modelo_289_casillas_ge_20",
            """
            SELECT COUNT(*)
            FROM modelo_casilla mcasi
            JOIN modelo_campana mc ON mc.id = mcasi.campana_id
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE am.codigo='289'
            """,
            20,
        ),
        _check_db_scalar(
            database_url,
            "modelo_289_instrucciones_nilreport",
            """
            SELECT COUNT(*)
            FROM modelo_instruccion mi
            JOIN modelo_campana mc ON mc.id = mi.campana_id
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE am.codigo='289'
              AND (
                  mi.titulo ILIKE '%NilReport%'
                  OR mi.contenido ILIKE '%NilReport%'
                  OR mi.titulo ILIKE '%declaracion negativa%'
                  OR mi.contenido ILIKE '%declaracion negativa%'
              )
            """,
            1,
        ),
        _check_db_scalar(
            database_url,
            "modelo_289_reglas_include_exclusion",
            """
            SELECT COUNT(*)
            FROM modelo_regla_inclusion mri
            JOIN modelo_campana mc ON mc.id = mri.campana_id
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE am.codigo='289'
              AND mri.decision='EXCLUIR'
            """,
            1,
        ),
        _check_db_scalar(
            database_url,
            "modelo_289_profile_obligations_expected_4",
            """
            SELECT COUNT(DISTINCT perfil_codigo)
            FROM obligacion_perfil
            WHERE modelo_aeat='289'
              AND perfil_codigo IN (
                  'sociedad_valores',
                  'agencia_valores',
                  'eaf',
                  'entidad_credito'
              )
            """,
            4,
        ),
        _check_db_scalar(
            database_url,
            "modelo_289_profile_obligations_verified_or_fail_closed_4",
            """
            SELECT COUNT(DISTINCT perfil_codigo)
            FROM obligacion_perfil
            WHERE modelo_aeat='289'
              AND perfil_codigo IN (
                  'sociedad_valores',
                  'agencia_valores',
                  'eaf',
                  'entidad_credito'
              )
              AND (
                  (
                      verified IS true
                      AND source_hash IS NOT NULL
                      AND capture_date IS NOT NULL
                  )
                  OR (
                      verified IS NOT true
                      AND safe_to_answer IS NOT true
                      AND source_hash IS NULL
                      AND capture_date IS NOT NULL
                      AND notas ILIKE '%fail-closed until source_hash and capture_date are loaded%'
                  )
              )
            """,
            4,
        ),
        _check_db_zero(
            database_url,
            "modelo_289_profile_obligations_no_extra_profiles",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE modelo_aeat='289'
              AND perfil_codigo NOT IN (
                  'sociedad_valores',
                  'agencia_valores',
                  'eaf',
                  'entidad_credito'
              )
            """,
        ),
        _check_db_zero(
            database_url,
            "cnmv_rows_missing_sujeto_obligado",
            """
            SELECT COUNT(*)
            FROM documento_interpretativo
            WHERE organismo_emisor='CNMV'
              AND tipo_fuente='cnmv'
              AND (
                  sujeto_obligado IS NULL
                  OR cardinality(sujeto_obligado) = 0
              )
            """,
        ),
        _check_db_scalar(
            database_url,
            "cnmv_sociedad_valores_docs_ge_50",
            """
            SELECT COUNT(*)
            FROM documento_interpretativo
            WHERE organismo_emisor='CNMV'
              AND tipo_fuente='cnmv'
              AND 'sociedad_valores' = ANY(sujeto_obligado)
            """,
            50,
        ),
        _check_db_scalar(
            database_url,
            "cnmv_sgiic_docs_ge_20",
            """
            SELECT COUNT(*)
            FROM documento_interpretativo
            WHERE organismo_emisor='CNMV'
              AND tipo_fuente='cnmv'
              AND 'sgiic' = ANY(sujeto_obligado)
            """,
            20,
        ),
        _check_db_scalar(
            database_url,
            "cnmv_obligacion_perfil_ge_6",
            """
            SELECT COUNT(*)
            FROM obligacion_perfil op
            JOIN norma n ON n.codigo = op.norma_codigo
            WHERE n.tipo_norma='circular_cnmv'
               OR op.norma_codigo ILIKE 'CNMV%'
            """,
            6,
        ),
        _check_db_scalar(
            database_url,
            "cnmv_modelo_normalizado_esi_links_ge_8",
            """
            SELECT COUNT(*)
            FROM cnmv_obligation_link
            WHERE tipo_obligacion='modelo_normalizado_esi'
            """,
            8,
        ),
    ]
    return checks


def _validate_domain_availability(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    allowed_empty = {"workflow_empty", "allowed_empty", "configured_but_unavailable"}
    items = payload.get("items") or []
    statuses = {item.get("availability_status") for item in items}
    legacy = statuses & {"not_available", "operational_data"}
    mismatched = [
        item.get("table")
        for item in items
        if item.get("status") != item.get("availability_status")
    ]
    summary = payload.get("summary") or {}
    details = {
        "total": payload.get("total"),
        "summary": summary,
        "statuses": sorted(str(status) for status in statuses),
        "legacy_statuses": sorted(legacy),
        "mismatched_status_tables": mismatched[:20],
    }
    ok = (
        isinstance(items, list)
        and statuses <= allowed_empty
        and not legacy
        and not mismatched
        and summary.get("unknown", 0) == 0
    )
    return ok, details


def _validate_empty_domain_abstention(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    confianza = payload.get("confianza") or {}
    availability = confianza.get("availability") or {}
    tables = availability.get("tables") or []
    table_names = {item.get("table") for item in tables}
    details = {
        "total_resultados": payload.get("total_resultados"),
        "cited_chunks": len(payload.get("cited_chunks") or []),
        "review_required": confianza.get("review_required"),
        "blocked": availability.get("blocked"),
        "tables": sorted(str(name) for name in table_names),
        "aviso": confianza.get("aviso"),
    }
    ok = (
        payload.get("total_resultados") == 0
        and payload.get("resultados") == []
        and payload.get("cited_chunks") == []
        and confianza.get("review_required") is True
        and "NO VERIFICADO" in (confianza.get("aviso") or "")
        and availability.get("blocked") is True
        and "wallet_custodian" in table_names
    )
    return ok, details


def _validate_direct_empty_domain_envelope(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    details = {
        "table": payload.get("table"),
        "availability_status": payload.get("availability_status"),
        "status": payload.get("status"),
        "safe_to_answer": payload.get("safe_to_answer"),
        "total": payload.get("total"),
        "items_count": len(payload.get("items") or []),
    }
    ok = (
        payload.get("availability_status")
        in {"workflow_empty", "allowed_empty", "configured_but_unavailable"}
        and payload.get("status") == payload.get("availability_status")
        and payload.get("safe_to_answer") is False
        and payload.get("items") == []
        and payload.get("total") == 0
    )
    return ok, details


def _validate_available_domain_not_blocked(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    confianza = payload.get("confianza") or {}
    details = {
        "total_resultados": payload.get("total_resultados"),
        "has_availability_block": "availability" in confianza,
        "aviso": confianza.get("aviso"),
    }
    return "availability" not in confianza, details


def _validate_modelos_por_supuesto(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    modelos = payload.get("modelos") or []
    clasificaciones = {item.get("clasificacion") for item in modelos}
    codigos = {item.get("codigo") for item in modelos}
    excluded = {item.get("codigo") for item in payload.get("excluded_modelos") or []}
    confidence = payload.get("confidence") or {}
    details = {
        "status": payload.get("status"),
        "verified": payload.get("verified"),
        "codigos": sorted(str(codigo) for codigo in codigos),
        "clasificaciones": sorted(str(value) for value in clasificaciones),
        "excluded": sorted(str(codigo) for codigo in excluded),
        "review_required": confidence.get("review_required"),
    }
    ok = (
        payload.get("status") in {"evidence_limited", "no_verified"}
        and payload.get("verified") is False
        and confidence.get("review_required") is True
        and "confirmado" not in clasificaciones
        and {"100", "111", "115", "190"} <= excluded
        and {"216", "296"} <= codigos
    )
    return ok, details


def _validate_modelo_casillas_pagination(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    casillas = payload.get("casillas") or []
    confidence = payload.get("confidence") or {}
    details = {
        "codigo": payload.get("codigo"),
        "returned": len(casillas),
        "total": payload.get("total"),
        "limit": payload.get("limit"),
        "offset": payload.get("offset"),
        "has_more": payload.get("has_more"),
        "classification": payload.get("classification"),
        "verified": payload.get("verified"),
        "review_required": confidence.get("review_required"),
        "notice": payload.get("obligation_notice"),
    }
    ok = (
        payload.get("codigo") == "100"
        and payload.get("limit") == 25
        and payload.get("offset") == 0
        and len(casillas) <= 25
        and isinstance(payload.get("total"), int)
        and "obligatoria" in (payload.get("obligation_notice") or "")
        and (
            payload.get("verified") is True
            or confidence.get("review_required") is True
        )
    )
    return ok, details


def _validate_modelo_detail_bounded(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    details = {
        "codigo": payload.get("codigo"),
        "casillas_returned": len(payload.get("casillas") or []),
        "casillas_total": payload.get("casillas_total"),
        "casillas_limit": payload.get("casillas_limit"),
        "articulos_returned": len(payload.get("articulos") or []),
        "articulos_total": payload.get("articulos_total"),
        "articulos_limit": payload.get("articulos_limit"),
        "articulos_has_more": payload.get("articulos_has_more"),
    }
    ok = (
        payload.get("codigo") == "100"
        and payload.get("casillas_limit") == 25
        and len(payload.get("casillas") or []) <= 25
        and isinstance(payload.get("casillas_total"), int)
        and payload.get("articulos_limit") == 10
        and len(payload.get("articulos") or []) <= 10
        and isinstance(payload.get("articulos_total"), int)
        and "articulos_has_more" in payload
        and "articulos_next_offset" in payload
    )
    return ok, details


def _validate_modelo_290_fatca_contract(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    claves = payload.get("claves") or []
    instrucciones = payload.get("instrucciones") or []
    reglas = payload.get("reglas_inclusion") or []
    regla_text = " ".join(str(regla.get("supuesto") or "") for regla in reglas).lower()
    decisions = {regla.get("decision") for regla in reglas}
    details = {
        "codigo": payload.get("codigo"),
        "verified": payload.get("verified"),
        "completeness": payload.get("completeness"),
        "obligation_context_source_urls": [
            item.get("source_url")
            for item in (payload.get("obligation_context") or [])
            if isinstance(item, dict)
        ],
        "claves": len(claves),
        "instrucciones": len(instrucciones),
        "reglas_inclusion": len(reglas),
        "decisions": sorted(str(value) for value in decisions),
    }
    ok = (
        payload.get("codigo") == "290"
        and payload.get("verified") is True
        and payload.get("completeness") == "completa"
        and len(claves) > 0
        and len(instrucciones) > 0
        and len(reglas) > 0
        and "pasiva" in regla_text
        and "activa" in regla_text
        and {"INCLUIR", "EXCLUIR"} <= decisions
        and not any(
            "BOE-A-2014-12328" in str(url)
            for url in details["obligation_context_source_urls"]
        )
    )
    return ok, details


def _validate_fatca_query_routes_to_290(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    modelos = payload.get("modelos") or []
    codigos = [item.get("codigo") for item in modelos]
    details = {
        "status": payload.get("status"),
        "safe_to_answer": payload.get("safe_to_answer"),
        "codigos": codigos,
        "total_modelos": len(modelos),
        "evidence_notice": payload.get("evidence_notice"),
    }
    ok = (
        payload.get("status") in {"matched", "evidence_limited", "no_verified"}
        and "290" in codigos
        and not ({"216", "296"} & set(codigos))
    )
    return ok, details


def _validate_completed_aeat_model(expected_codigo: str):
    def validator(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        details = {
            "codigo": payload.get("codigo"),
            "verified": payload.get("verified"),
            "completeness": payload.get("completeness"),
            "claves": len(payload.get("claves") or []),
            "instrucciones": len(payload.get("instrucciones") or []),
        }
        ok = (
            payload.get("codigo") == expected_codigo
            and payload.get("verified") is True
            and payload.get("completeness") == "completa"
            and len(payload.get("claves") or []) > 0
            and len(payload.get("instrucciones") or []) > 0
        )
        return ok, details

    return validator


def _validate_any_completed_aeat_model(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    modelos = payload.get("modelos") or []
    completed = [
        item.get("codigo")
        for item in modelos
        if item.get("completeness") == "completa" and item.get("verified") is True
    ]
    details = {
        "total": payload.get("total"),
        "completed": completed[:20],
        "completed_count": len(completed),
    }
    return len(completed) > 0, details


def _validate_list_pagination(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    list_key = "normas" if "normas" in payload else "modelos" if "modelos" in payload else None
    items = payload.get(list_key or "") or []
    details = {
        "list_key": list_key,
        "returned": len(items),
        "total": payload.get("total"),
        "limit": payload.get("limit"),
        "offset": payload.get("offset"),
        "has_more": payload.get("has_more"),
        "next_offset": payload.get("next_offset"),
    }
    ok = (
        list_key is not None
        and payload.get("limit") == 5
        and payload.get("offset") == 0
        and len(items) <= 5
        and isinstance(payload.get("total"), int)
        and "has_more" in payload
    )
    return ok, details


def _validate_obligaciones_aplicables_contract(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    confidence = payload.get("confidence") or {}
    total = payload.get("total")
    details = {
        "total": total,
        "returned": len(payload.get("obligaciones") or []),
        "status": payload.get("status"),
        "verified": payload.get("verified"),
        "review_required": confidence.get("review_required"),
        "limit": payload.get("limit"),
        "offset": payload.get("offset"),
    }
    if total == 0:
        ok = (
            payload.get("status") == "evidence_limited"
            and payload.get("verified") is False
            and confidence.get("review_required") is True
            and "No interpretar" in (confidence.get("aviso") or "")
        )
    else:
        ok = (
            payload.get("status") == "matched"
            and payload.get("verified") is True
            and len(payload.get("obligaciones") or []) <= payload.get("limit", 0)
        )
    return ok, details


def _validate_perfil_list(payload: Any) -> tuple[bool, dict[str, Any]]:
    items = payload if isinstance(payload, list) else []
    codigos = {item.get("codigo") for item in items if isinstance(item, dict)}
    details = {
        "returned": len(items),
        "codigos": sorted(str(codigo) for codigo in codigos),
    }
    expected = {
        "sociedad_valores",
        "agencia_valores",
        "sgiic",
        "eaf",
        "entidad_credito",
        "empresa_servicios_pago",
    }
    return len(items) >= 6 and expected <= codigos, details


def _validate_perfil_obligaciones(
    *,
    minimum_total: int,
    expected_perfil: str = "sociedad_valores",
    required_types: set[str] | None = None,
    required_modelos: set[str] | None = None,
    required_text: set[str] | None = None,
    forbidden_text: set[str] | None = None,
) -> Any:
    def validator(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        obligaciones = payload.get("obligaciones") or []
        tipos = {item.get("obligacion_tipo") for item in obligaciones if isinstance(item, dict)}
        modelos = {
            item.get("modelo_aeat")
            for item in obligaciones
            if isinstance(item, dict) and item.get("modelo_aeat")
        }
        missing_source = [
            item.get("descripcion")
            for item in obligaciones
            if isinstance(item, dict) and not item.get("source_url")
        ]
        descriptions = [
            str(item.get("descripcion") or "").lower()
            for item in obligaciones
            if isinstance(item, dict)
        ]
        details = {
            "perfil": (payload.get("perfil") or {}).get("codigo"),
            "total": payload.get("total"),
            "returned": len(obligaciones),
            "safe_to_answer": payload.get("safe_to_answer"),
            "tipos": sorted(str(tipo) for tipo in tipos),
            "modelos": sorted(str(modelo) for modelo in modelos),
            "missing_source_url": missing_source[:20],
            "evidence_notice_present": bool(payload.get("evidence_notice")),
            "required_text": sorted(required_text or []),
            "forbidden_text": sorted(forbidden_text or []),
        }
        ok = (
            (payload.get("perfil") or {}).get("codigo") == expected_perfil
            and isinstance(payload.get("total"), int)
            and payload.get("total", 0) >= minimum_total
            and len(obligaciones) >= minimum_total
            and not missing_source
            and "safe_to_answer" in payload
            and bool(payload.get("evidence_notice"))
        )
        if required_types:
            ok = ok and required_types <= tipos
        if required_modelos:
            ok = ok and required_modelos <= modelos
        if required_text:
            ok = ok and all(
                any(needle.lower() in description for description in descriptions)
                for needle in required_text
            )
        if forbidden_text:
            ok = ok and not any(
                needle.lower() in description
                for needle in forbidden_text
                for description in descriptions
            )
        return ok, details

    return validator


def _validate_perfil_calendar(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    calendario = payload.get("calendario") or {}
    expected_keys = {"diaria", "mensual", "trimestral", "semestral", "anual", "ad_hoc", "continua"}
    details = {
        "perfil": (payload.get("perfil") or {}).get("codigo"),
        "keys": sorted(calendario),
        "anual": len(calendario.get("anual") or []),
        "continua": len(calendario.get("continua") or []),
        "mensual": len(calendario.get("mensual") or []),
        "trimestral": len(calendario.get("trimestral") or []),
    }
    ok = (
        (payload.get("perfil") or {}).get("codigo") == "sociedad_valores"
        and expected_keys <= set(calendario)
        and len(calendario.get("anual") or []) > 0
        and len(calendario.get("continua") or []) > 0
        and (
            len(calendario.get("mensual") or []) > 0
            or len(calendario.get("trimestral") or []) > 0
        )
    )
    return ok, details


def _validate_sociedad_valores_fiscal_routing(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    obligaciones = payload.get("obligaciones") or []
    modelos = {
        item.get("modelo_aeat")
        for item in obligaciones
        if isinstance(item, dict) and item.get("modelo_aeat")
    }
    modelo_202_items = [
        item
        for item in obligaciones
        if isinstance(item, dict) and item.get("modelo_aeat") == "202"
    ]
    modelo_202_accepted_states = [
        _profile_obligation_acceptance_state(item)
        for item in modelo_202_items
        if isinstance(item, dict)
    ]
    details = {
        "perfil": (payload.get("perfil") or {}).get("codigo"),
        "modelos": sorted(str(modelo) for modelo in modelos),
        "modelo_202_count": len(modelo_202_items),
        "modelo_202_verified": [item.get("verified") for item in modelo_202_items],
        "modelo_202_accepted_states": modelo_202_accepted_states,
    }
    ok = (
        (payload.get("perfil") or {}).get("codigo") == "sociedad_valores"
        and "202" in modelos
        and not ({"123", "124"} & modelos)
        and any(state in {"verified", "fail_closed"} for state in modelo_202_accepted_states)
    )
    return ok, details


def _profile_obligation_acceptance_state(item: dict[str, Any]) -> str:
    notice = str(item.get("evidence_notice") or item.get("obligation_evidence_notice") or "")
    if (
        item.get("verified") is True
        and item.get("source_hash")
        and item.get("capture_date")
    ):
        return "verified"
    if (
        item.get("verified") is False
        and item.get("safe_to_answer") is False
        and item.get("review_required") is True
        and item.get("source_hash") is None
        and bool(item.get("source_url"))
        and bool(item.get("capture_date"))
        and "evidence_limited" in notice
        and "falta hash" in notice.lower()
    ):
        return "fail_closed"
    return "invalid"


def _validate_aeat_catalogo_layer(payload: Any) -> tuple[bool, dict[str, Any]]:
    items = payload if isinstance(payload, list) else []
    first = items[0] if items and isinstance(items[0], dict) else {}
    details = {
        "returned": len(items),
        "codigo": first.get("codigo"),
        "keys": sorted(first.keys()) if isinstance(first, dict) else [],
    }
    ok = (
        len(items) == 1
        and first.get("codigo") == "123"
        and "verified" not in first
        and "evidence_notice" not in first
    )
    return ok, details


def _validate_modelo_289_obligation_context(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    context = payload.get("obligation_context") or []
    sociedad_items = [
        item
        for item in context
        if isinstance(item, dict) and item.get("perfil_codigo") == "sociedad_valores"
    ]
    details = {
        "codigo": payload.get("codigo"),
        "form_completeness": payload.get("form_completeness"),
        "obligation_context_count": len(context),
        "sociedad_valores_context": sociedad_items[:1],
    }
    sociedad_item = sociedad_items[0] if sociedad_items else {}
    notice = str(sociedad_item.get("obligation_evidence_notice") or "")
    verified_ok = (
        sociedad_item.get("verified") is True
        and sociedad_item.get("source_hash")
        and sociedad_item.get("capture_date")
        and "Verificado" in notice
    )
    fail_closed_ok = (
        sociedad_item.get("verified") is False
        and sociedad_item.get("safe_to_answer") is False
        and sociedad_item.get("review_required") is True
        and not sociedad_item.get("source_hash")
        and sociedad_item.get("capture_date")
        and "evidence_limited" in notice
        and "falta hash" in notice
    )
    details["accepted_state"] = (
        "verified" if verified_ok else "fail_closed" if fail_closed_ok else "invalid"
    )
    ok = (
        payload.get("codigo") == "289"
        and "form_completeness" in payload
        and len(sociedad_items) == 1
        and (verified_ok or fail_closed_ok)
    )
    return ok, details


def _validate_aeat_catalogo_289_crs(payload: Any) -> tuple[bool, dict[str, Any]]:
    items = payload if isinstance(payload, list) else []
    first = items[0] if items and isinstance(items[0], dict) else {}
    details = {
        "returned": len(items),
        "codigo": first.get("codigo"),
        "instrucciones_count": first.get("instrucciones_count"),
        "claves_count": first.get("claves_count"),
        "reglas_inclusion_count": first.get("reglas_inclusion_count"),
        "keys": sorted(first.keys()) if isinstance(first, dict) else [],
    }
    ok = (
        len(items) == 1
        and first.get("codigo") == "289"
        and int(first.get("instrucciones_count") or 0) >= 5
        and int(first.get("reglas_inclusion_count") or 0) >= 6
        and "obligation_context" not in first
    )
    return ok, details


def _validate_calendar_q3_structured(payload: Any) -> tuple[bool, dict[str, Any]]:
    items = payload if isinstance(payload, list) else []
    modelos = {
        item.get("modelo_aeat")
        for item in items
        if isinstance(item, dict) and item.get("modelo_aeat")
    }
    missing_plazo = [
        item.get("descripcion")
        for item in items
        if isinstance(item, dict) and not item.get("plazo_descripcion")
    ]
    details = {
        "returned": len(items),
        "modelos": sorted(str(modelo) for modelo in modelos),
        "missing_plazo": missing_plazo[:20],
    }
    ok = len(items) >= 2 and "303" in modelos and "202" not in modelos and not missing_plazo
    return ok, details


def _validate_norma_eu_list(payload: Any) -> tuple[bool, dict[str, Any]]:
    items = payload if isinstance(payload, list) else []
    celex_values = {item.get("celex") for item in items if isinstance(item, dict)}
    missing_url = [
        item.get("codigo")
        for item in items
        if isinstance(item, dict) and not item.get("url_eurlex")
    ]
    details = {
        "returned": len(items),
        "celex": sorted(str(value) for value in celex_values if value),
        "missing_url_eurlex": missing_url[:20],
    }
    ok = (
        len(items) >= 10
        and not missing_url
    )
    return ok, details


def _validate_norma_eu_detail(expected_celex: str) -> Any:
    def validator(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        obligaciones = payload.get("obligaciones_referenciadas") or []
        details = {
            "codigo": payload.get("codigo"),
            "celex": payload.get("celex"),
            "tipo_norma": payload.get("tipo_norma"),
            "url_eurlex_present": bool(payload.get("url_eurlex")),
            "obligaciones_referenciadas": len(obligaciones),
        }
        ok = (
            payload.get("celex") == expected_celex
            and bool(payload.get("url_eurlex"))
            and payload.get("tipo_norma") is not None
        )
        if expected_celex == "32014R0600":
            ok = ok and len(obligaciones) >= 1
        return ok, details

    return validator


def _validate_eurlex_market_article(expected_celex: str) -> Any:
    def validator(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        text_value = payload.get("texto") or ""
        details = {
            "celex": payload.get("celex"),
            "numero": payload.get("numero"),
            "verified": payload.get("verified"),
            "completeness": payload.get("completeness"),
            "quality_signal": payload.get("quality_signal"),
            "text_length": len(text_value),
            "source_url_present": bool(payload.get("source_url")),
            "source_hash_present": bool(payload.get("source_hash")),
            "capture_date_present": bool(payload.get("capture_date")),
        }
        ok = (
            payload.get("celex") == expected_celex
            and payload.get("numero") == "1"
            and payload.get("verified") is True
            and payload.get("completeness") == "completa"
            and payload.get("quality_signal") == "official_eurlex_text"
            and len(text_value) > 100
            and "metadata_only" not in text_value.lower()
            and bool(payload.get("source_url"))
            and bool(payload.get("source_hash"))
            and bool(payload.get("capture_date"))
        )
        return ok, details

    return validator


def _validate_legislation_article(
    expected_norma: str,
    expected_numero: str,
    expected_boe_reference: str,
    *,
    required_text: str | None = None,
) -> Any:
    def validator(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        text_value = payload.get("texto") or ""
        source_url = payload.get("source_url") or ""
        details = {
            "norma": payload.get("norma"),
            "numero": payload.get("numero"),
            "boe_reference": payload.get("boe_reference"),
            "verified": payload.get("verified"),
            "completeness": payload.get("completeness"),
            "text_length": len(text_value),
            "source_url": source_url,
        }
        ok = (
            payload.get("norma") == expected_norma
            and payload.get("numero") == expected_numero
            and payload.get("boe_reference") == expected_boe_reference
            and payload.get("verified") is True
            and payload.get("completeness") == "completa"
            and len(text_value) > 50
            and source_url.startswith(f"https://www.boe.es/buscar/act.php?id={expected_boe_reference}")
        )
        if required_text is not None:
            ok = ok and required_text.lower() in text_value.lower()
        return ok, details

    return validator


def _validate_teac_search_result(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    resultados = payload.get("resultados") or []
    teac_results = [
        item
        for item in resultados
        if item.get("tipo_documento") == "resolucion_teac"
        or str(item.get("organismo_emisor") or "").upper() == "TEAC"
    ]
    details = {
        "returned": len(resultados),
        "teac_results": len(teac_results),
        "first_referencia": teac_results[0].get("referencia") if teac_results else None,
    }
    return len(teac_results) > 0, details


def _validate_sepblac_family_list(expected_tipo: str, minimum: int = 1) -> Any:
    def validator(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        documentos = payload.get("documentos") or []
        matching = [item for item in documentos if item.get("tipo_documento") == expected_tipo]
        details = {
            "returned": len(documentos),
            "matching": len(matching),
            "expected_tipo": expected_tipo,
        }
        return len(matching) >= minimum, details

    return validator


def _validate_esma_mifir_schema_contract(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    items = payload.get("items") or []
    details = {
        "total": payload.get("total"),
        "returned": len(items),
        "verified": payload.get("verified"),
        "completeness": payload.get("completeness"),
        "quality_signal": payload.get("quality_signal"),
        "sources_present": sum(1 for item in items if item.get("source_url") and item.get("source_hash")),
    }
    ok = (
        isinstance(items, list)
        and payload.get("total", 0) >= 1
        and payload.get("verified") is True
        and payload.get("completeness") == "completa"
        and payload.get("quality_signal") == "official_esma_schema"
        and all(item.get("source_url") and item.get("source_hash") for item in items)
    )
    return ok, details


def _validate_esma_mifir_fields_contract(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    items = payload.get("items") or []
    details = {
        "total": payload.get("total"),
        "returned": len(items),
        "verified": payload.get("verified"),
        "completeness": payload.get("completeness"),
        "quality_signal": payload.get("quality_signal"),
        "sources_present": sum(1 for item in items if item.get("source_url") and item.get("source_hash")),
        "descriptions_present": sum(1 for item in items if item.get("descripcion")),
    }
    ok = (
        isinstance(items, list)
        and payload.get("total", 0) > 0
        and 0 < len(items) <= payload.get("limit", 0)
        and payload.get("verified") is True
        and payload.get("completeness") == "completa"
        and payload.get("quality_signal") == "official_esma_xsd"
        and all(item.get("source_url") and item.get("source_hash") for item in items)
        and all(item.get("quality_signal") == "official_esma_xsd" for item in items)
    )
    return ok, details


def _validate_esma_firds_files_contract(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    items = payload.get("items") or []
    details = {
        "total": payload.get("total"),
        "returned": len(items),
        "verified": payload.get("verified"),
        "completeness": payload.get("completeness"),
        "quality_signal": payload.get("quality_signal"),
        "safe_to_answer": payload.get("safe_to_answer"),
        "sources_present": sum(1 for item in items if item.get("source_url") and item.get("source_hash")),
    }
    ok = (
        isinstance(items, list)
        and payload.get("total", 0) > 0
        and payload.get("verified") is False
        and payload.get("completeness") == "parcial"
        and payload.get("quality_signal") == "evidence_limited_firds_pilot"
        and payload.get("safe_to_answer") is True
        and all(item.get("source_url") and item.get("source_hash") for item in items)
    )
    return ok, details


def _validate_esma_firds_unknown_isin_contract(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    details = {
        "total": payload.get("total"),
        "returned": len(payload.get("items") or []),
        "verified": payload.get("verified"),
        "completeness": payload.get("completeness"),
        "quality_signal": payload.get("quality_signal"),
        "safe_to_answer": payload.get("safe_to_answer"),
        "evidence_notice": payload.get("evidence_notice"),
    }
    ok = (
        payload.get("total") == 0
        and payload.get("items") == []
        and payload.get("verified") is False
        and payload.get("completeness") == "parcial"
        and payload.get("quality_signal") == "evidence_limited_firds_pilot"
        and payload.get("safe_to_answer") is False
        and "absence is not authoritative" in (payload.get("evidence_notice") or "")
    )
    return ok, details


def _validate_esma_dlt_contract(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    items = payload.get("items") or []
    details = {
        "total": payload.get("total"),
        "returned": len(items),
        "verified": payload.get("verified"),
        "completeness": payload.get("completeness"),
        "quality_signal": payload.get("quality_signal"),
        "safe_to_answer": payload.get("safe_to_answer"),
    }
    if payload.get("total") == 0:
        ok = (
            items == []
            and payload.get("verified") is False
            and payload.get("quality_signal") == "configured_but_unavailable"
            and payload.get("safe_to_answer") is False
        )
    else:
        ok = (
            payload.get("verified") is True
            and payload.get("completeness") == "completa"
            and payload.get("quality_signal") == "official_esma_dlt_register"
            and payload.get("safe_to_answer") is True
            and all(item.get("source_url") and item.get("source_hash") for item in items)
        )
    return ok, details


def _validate_casp_contract(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    items = payload.get("items") or []
    details = {
        "total": payload.get("total"),
        "returned": len(items),
        "quality_signal": payload.get("quality_signal"),
        "availability_status": payload.get("availability_status"),
        "safe_to_answer": payload.get("safe_to_answer"),
        "source_url": payload.get("source_url"),
    }
    ok = (
        payload.get("total", 0) > 0
        and payload.get("quality_signal") == "official_esma_register"
        and payload.get("availability_status") == "populated"
        and payload.get("safe_to_answer") is True
        and bool(payload.get("source_url"))
    )
    return ok, details


def _validate_cnmv_coverage_contract(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    families = payload.get("source_families") or []
    family_by_id = {
        item.get("family_id"): item for item in families if isinstance(item, dict)
    }
    unavailable = [
        item.get("family_id")
        for item in families
        if item.get("coverage_status") == "configured_but_unavailable"
    ]
    details = {
        "total_cnmv_loaded": payload.get("total_cnmv_loaded"),
        "current_loaded": payload.get("current_loaded"),
        "derogado_loaded": payload.get("derogado_loaded"),
        "family_count": len(families),
        "unavailable": unavailable,
        "coverage_note": payload.get("coverage_note"),
    }
    ok = (
        isinstance(families, list)
        and payload.get("total_cnmv_loaded", 0) > 0
        and payload.get("current_loaded", 0) > 0
        and (family_by_id.get("circulares") or {}).get("coverage_status")
        == "partial_loaded"
        and (family_by_id.get("guias_tecnicas") or {}).get("coverage_status")
        == "partial_loaded"
        and (family_by_id.get("guias_tecnicas") or {}).get("loaded_count", 0) > 0
        and (family_by_id.get("documentos_consulta_cnmv") or {}).get(
            "coverage_status"
        )
        == "partial_loaded"
        and (family_by_id.get("documentos_consulta_cnmv") or {}).get("loaded_count", 0)
        > 0
        and "no cargado" in (payload.get("coverage_note") or "")
    )
    return ok, details


def _validate_cnmv_perfil_documents(payload: Any) -> tuple[bool, dict[str, Any]]:
    documents = payload if isinstance(payload, list) else []
    missing_fields = [
        item
        for item in documents
        if isinstance(item, dict)
        and not {"referencia", "titulo", "tipo_documento"} <= set(item)
    ]
    details = {
        "documents": len(documents),
        "missing_fields_count": len(missing_fields),
        "tipos": sorted(
            {
                str(item.get("tipo_documento"))
                for item in documents
                if isinstance(item, dict)
            }
        ),
    }
    ok = len(documents) >= 10 and not missing_fields
    return ok, details


def run_read_only_suite(base_url: str) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    checks: list[dict[str, Any]] = []
    with httpx.Client(base_url=base_url, timeout=60) as client:
        checks.append(_check_get(client, "/health"))
        checks.append(_check_get(client, "/status"))
        checks.append(_check_mcp_transport(client))
        checks.append(_check_stdio_tool_descriptions())
        checks.extend(_check_database_contracts())
        checks.append(_check_get(client, "/v1/legislacion/LIVA/articulos/90", "21 por ciento"))
        checks.append(
            _check_json_contract(
                client,
                "/v1/legislacion/TRLIRNR/articulos/14",
                {},
                _validate_legislation_article(
                    "TRLIRNR",
                    "14",
                    "BOE-A-2004-4527",
                    required_text="Rentas exentas",
                ),
                "trlirnr_article_14_official_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/legislacion/IRNR/articulos/14",
                {},
                _validate_legislation_article(
                    "TRLIRNR",
                    "14",
                    "BOE-A-2004-4527",
                    required_text="Rentas exentas",
                ),
                "irnr_alias_article_14_official_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/legislacion/LIVA/articulos/163%20sexvicies",
                {},
                _validate_legislation_article(
                    "LIVA",
                    "163 sexvicies",
                    "BOE-A-1992-28740",
                ),
                "liva_article_163_sexvicies_official_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/domain-availability",
                {"only_empty": "true"},
                _validate_domain_availability,
                "domain_availability_empty_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/consulta",
                {"q": "wallet custodian MiCA autorizados en España"},
                _validate_empty_domain_abstention,
                "consulta_empty_domain_fail_closed",
            )
        )
        for path, name in [
            ("/v1/mica/wallet-custodians", "direct_availability_mica_wallet_custodians"),
            ("/v1/aifmd/funds", "direct_availability_aifmd_funds"),
            ("/v1/ucits/funds", "direct_availability_ucits_funds"),
            ("/v1/crd/capital-positions", "direct_availability_crd_capital_positions"),
            ("/v1/emir/trade-reports", "direct_availability_emir_trade_reports"),
            ("/v1/consumer-credit/contracts", "direct_availability_consumer_credit_contracts"),
            ("/v1/insurance/distributors", "direct_availability_insurance_idd_distributors"),
            ("/v1/insurance/uci-products", "direct_availability_insurance_uci_products"),
            ("/v1/transparency/issuers", "direct_availability_transparency_issuers"),
            ("/v1/xbrl/facts", "direct_availability_xbrl_facts"),
        ]:
            checks.append(
                _check_json_contract(
                    client,
                    path,
                    {},
                    _validate_direct_empty_domain_envelope,
                    name,
                )
            )
        checks.append(
            _check_json_contract(
                client,
                "/v1/consulta",
                {"q": "modelo 100 irpf"},
                _validate_available_domain_not_blocked,
                "consulta_available_domain_not_blocked",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/legislacion",
                {"limit": 5, "offset": 0},
                _validate_list_pagination,
                "legislacion_list_pagination_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/modelos",
                {"limit": 5, "offset": 0},
                _validate_list_pagination,
                "modelos_list_pagination_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/modelos/por-supuesto",
                {
                    "tipo_entidad": "sociedad_valores",
                    "clientes_residentes": "true",
                    "clientes_no_residentes": "true",
                    "tipo_renta": "capital_mobiliario",
                },
                _validate_modelos_por_supuesto,
                "modelos_por_supuesto_sociedad_valores_fail_closed",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/modelos/100",
                {
                    "casillas_limit": 25,
                    "casillas_offset": 0,
                    "related_limit": 10,
                    "articulos_offset": 0,
                },
                _validate_modelo_detail_bounded,
                "modelo_100_detail_bounded_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/modelos/100/casillas",
                {"limit": 25, "offset": 0},
                _validate_modelo_casillas_pagination,
                "modelo_100_casillas_paginated_agent_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/modelos/aeat/290",
                {},
                _validate_modelo_290_fatca_contract,
                "modelo_290_fatca_rules_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/modelos/aeat/289",
                {},
                _validate_modelo_289_obligation_context,
                "modelo_289_obligation_context_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/modelos/catalogo",
                {"codigo": "123"},
                _validate_aeat_catalogo_layer,
                "aeat_catalogo_no_profile_evidence_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/modelos/catalogo",
                {"codigo": "289"},
                _validate_aeat_catalogo_289_crs,
                "aeat_catalogo_modelo_289_crs_counts",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/consulta",
                {"q": "FATCA passive NFFE modelo 290"},
                _validate_fatca_query_routes_to_290,
                "consulta_fatca_routes_to_modelo_290",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/modelos/aeat/198",
                {},
                _validate_completed_aeat_model("198"),
                "aeat_modelo_198_completed_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/obligaciones/aplicables",
                {"tipo_entidad": "sociedad_valores", "limite": 1, "offset": 0},
                _validate_obligaciones_aplicables_contract,
                "obligaciones_aplicables_profile_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/perfil",
                {},
                _validate_perfil_list,
                "perfil_list_profiles_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/perfil/sociedad_valores/obligaciones",
                {},
                _validate_perfil_obligaciones(minimum_total=15),
                "perfil_sociedad_valores_obligaciones_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/perfil/sociedad_valores/obligaciones",
                {"dominio": "FISCAL"},
                _validate_sociedad_valores_fiscal_routing,
                "perfil_sociedad_valores_fiscal_routing_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/perfil/sociedad_valores/obligaciones",
                {"dominio": "PBC_FT"},
                _validate_perfil_obligaciones(
                    minimum_total=4,
                    required_types={"COMUNICACION_INDICIO", "DILIGENCIA_DEBIDA"},
                ),
                "perfil_sociedad_valores_pbc_ft_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/perfil/sociedad_valores/obligaciones/calendario",
                {},
                _validate_perfil_calendar,
                "perfil_sociedad_valores_calendar_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/perfil/sociedad_valores/obligaciones/calendario/2026-Q3",
                {},
                _validate_calendar_q3_structured,
                "perfil_sociedad_valores_calendar_q3_contract",
            )
        )
        for perfil_codigo, minimum_total in (
            ("eaf", 15),
            ("entidad_credito", 22),
            ("empresa_servicios_pago", 10),
            ("sgiic", 20),
        ):
            checks.append(
                _check_json_contract(
                    client,
                    f"/v1/perfil/{perfil_codigo}/obligaciones",
                    {},
                    _validate_perfil_obligaciones(
                        minimum_total=minimum_total,
                        expected_perfil=perfil_codigo,
                    ),
                    f"perfil_{perfil_codigo}_obligaciones_contract",
                )
            )
        checks.append(
            _check_json_contract(
                client,
                "/v1/perfil/eaf/obligaciones",
                {"dominio": "CNMV"},
                _validate_perfil_obligaciones(
                    minimum_total=4,
                    expected_perfil="eaf",
                    required_text={"idoneidad"},
                    forbidden_text={"transaction reporting", "mejor ejecucion"},
                ),
                "perfil_eaf_cnmv_no_execution_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/perfil/agencia_valores/obligaciones",
                {},
                _validate_perfil_obligaciones(
                    minimum_total=18,
                    expected_perfil="agencia_valores",
                    forbidden_text={"custodia"},
                ),
                "perfil_agencia_valores_no_custody_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/perfil/entidad_credito/obligaciones",
                {"dominio": "CNMV"},
                _validate_perfil_obligaciones(
                    minimum_total=5,
                    expected_perfil="entidad_credito",
                    required_text={"corep", "finrep"},
                ),
                "perfil_entidad_credito_prudential_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/perfil/empresa_servicios_pago/obligaciones",
                {"dominio": "FISCAL"},
                _validate_perfil_obligaciones(
                    minimum_total=4,
                    expected_perfil="empresa_servicios_pago",
                    required_modelos={"303"},
                ),
                "perfil_empresa_servicios_pago_fiscal_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/perfil/sgiic/obligaciones",
                {"dominio": "CNMV"},
                _validate_perfil_obligaciones(
                    minimum_total=6,
                    expected_perfil="sgiic",
                    required_text={"annex iv"},
                ),
                "perfil_sgiic_aifmd_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/norma/eu",
                {},
                _validate_norma_eu_list,
                "norma_eu_list_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/norma/32014R0600",
                {},
                _validate_norma_eu_detail("32014R0600"),
                "norma_eu_mifir_detail_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/norma/32022R2554",
                {},
                _validate_norma_eu_detail("32022R2554"),
                "norma_eu_dora_detail_contract",
            )
        )
        for celex, name in [
            ("32014R0600", "eurlex_mifir_article_1_official_text"),
            ("32023R1114", "eurlex_mica_article_1_official_text"),
            ("32022R0858", "eurlex_dlt_pilot_article_1_official_text"),
        ]:
            checks.append(
                _check_json_contract(
                    client,
                    f"/v1/eurlex/market/{celex}/articulos/1",
                    {},
                    _validate_eurlex_market_article(celex),
                    name,
                )
            )
        checks.append(
            _check_json_contract(
                client,
                "/v1/esma/mifir/schemas",
                {},
                _validate_esma_mifir_schema_contract,
                "esma_mifir_schema_official_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/esma/mifir/transaction-reporting/fields",
                {"limit": 5, "offset": 0},
                _validate_esma_mifir_fields_contract,
                "esma_mifir_transaction_reporting_fields_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/esma/firds/files",
                {"limit": 5, "offset": 0},
                _validate_esma_firds_files_contract,
                "esma_firds_files_evidence_limited_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/esma/firds/instruments",
                {"isin": "ZZZZZZZZZZZZ", "limit": 5, "offset": 0},
                _validate_esma_firds_unknown_isin_contract,
                "esma_firds_unknown_isin_fail_closed_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/esma/dlt/infrastructures",
                {"limit": 10, "offset": 0},
                _validate_esma_dlt_contract,
                "esma_dlt_infrastructure_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/mica/casp/buscar",
                {"q": "crypto", "limit": 5, "offset": 0},
                _validate_casp_contract,
                "esma_casp_register_official_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/cnmv/coverage",
                {},
                _validate_cnmv_coverage_contract,
                "cnmv_coverage_partial_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/cnmv/perfil/sociedad_valores",
                {},
                _validate_cnmv_perfil_documents,
                "cnmv_perfil_sociedad_valores_documents",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/doctrina/buscar",
                {
                    "q": "retencion no residente",
                    "tipo": "resolucion_teac",
                    "organismo_emisor": "TEAC",
                },
                _validate_teac_search_result,
                "teac_resoluciones_search_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/sepblac",
                {"q": "obligaciones"},
                _validate_sepblac_family_list("obligacion_sepblac"),
                "sepblac_obligacion_family_contract",
            )
        )
        checks.append(
            _check_json_contract(
                client,
                "/v1/legislacion/RD_304_2014/articulos/4",
                {},
                _validate_legislation_article(
                    "RD_304_2014",
                    "4",
                    "BOE-A-2014-4742",
                    required_text="Identificación formal",
                ),
                "rd_304_2014_article_4_contract",
            )
        )

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "read_only": True,
        "checks": checks,
        "ok": all(check["ok"] for check in checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-only", action="store_true", required=True)
    parser.add_argument(
        "--base-url",
        default=os.getenv("ESDATA_API_URL", "http://localhost:8000"),
        help="Base API URL. Defaults to ESDATA_API_URL or http://localhost:8000.",
    )
    args = parser.parse_args()

    result = run_read_only_suite(args.base_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"ok={str(result['ok']).lower()}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
