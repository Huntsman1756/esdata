#!/usr/bin/env python
"""Read-only MCP/API validation suite for scheduled maintenance checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any

import httpx


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
        handshake = _request_with_retry(client, "GET", "/mcp", headers=headers)
    except httpx.HTTPError as exc:
        check["error"] = f"handshake_failed: {exc}"
        return check

    session_id = handshake.headers.get("mcp-session-id") or handshake.headers.get("Mcp-Session-Id")
    check["handshake_status_code"] = handshake.status_code
    check["has_session_id"] = bool(session_id)
    if not session_id:
        check["error"] = handshake.text[:500] if handshake.status_code != 200 else "missing_mcp_session_id"
        return check
    if handshake.status_code not in {200, 400}:
        check["error"] = handshake.text[:500]
        return check
    if handshake.status_code == 400 and "Missing session ID" not in handshake.text:
        check["error"] = handshake.text[:500]
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


def run_read_only_suite(base_url: str) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    checks: list[dict[str, Any]] = []
    with httpx.Client(base_url=base_url, timeout=60) as client:
        checks.append(_check_get(client, "/health"))
        checks.append(_check_get(client, "/status"))
        checks.append(_check_mcp_transport(client))
        checks.append(_check_get(client, "/v1/legislacion/LIVA/articulos/90", "21 por ciento"))
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
                "/v1/obligaciones/aplicables",
                {"tipo_entidad": "sociedad_valores", "limite": 1, "offset": 0},
                _validate_obligaciones_aplicables_contract,
                "obligaciones_aplicables_profile_contract",
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
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
