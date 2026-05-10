#!/usr/bin/env python
"""Read-only MCP/API validation suite for scheduled maintenance checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

import httpx


def _headers() -> dict[str, str]:
    api_key = os.getenv("ESDATA_API_KEY", "")
    return {"X-API-Key": api_key} if api_key else {}


def _check_get(
    client: httpx.Client,
    path: str,
    required_text: str | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.get(path, params=params, headers=_headers())
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
    response = client.get(path, params=params, headers=_headers())
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
        and "casp" in table_names
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


def run_read_only_suite(base_url: str) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    checks: list[dict[str, Any]] = []
    with httpx.Client(base_url=base_url, timeout=20) as client:
        checks.append(_check_get(client, "/health"))
        checks.append(_check_get(client, "/status"))
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
                {"q": "lista CASP MiCA autorizados en España"},
                _validate_empty_domain_abstention,
                "consulta_empty_domain_fail_closed",
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
