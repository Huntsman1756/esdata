#!/usr/bin/env python
"""Deep read-only MCP/API/database contract audit.

This gate is intentionally broader than the scheduled smoke suite:

- one live DB row-count/classification/RLS check per public table
- one orphan check per foreign-key relationship
- one API availability-envelope check per Ralph registry table
- MCP transport/tools-list contract checks
- GPT Actions/OpenAPI contract checks
- critical semantic fail-closed checks delegated to mcp_validation_suite

It does not mutate compliance data and does not try to prove every possible
legal answer. It verifies that the system exposes data and uncertainty through
deterministic, bounded, traceable contracts.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in (current.parent, *current.parents):
        if (parent / "apps" / "api").exists() and (parent / "scripts").exists():
            return parent
    return Path.cwd()


ROOT = _repo_root()
REGISTRY_PATH = ROOT / "scripts" / "ralph" / "table-remediation-registry.json"
MCP_CATALOG_PATH = ROOT / "apps" / "api" / "mcp_catalog.py"

EMPTY_STATUSES = {"workflow_empty", "allowed_empty", "configured_but_unavailable"}
VALID_AVAILABILITY_STATUSES = EMPTY_STATUSES | {"populated"}
BLOCKING_CLASSIFICATIONS = {"blocker", "derived_blocker", "unclassified"}


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: dict[str, Any]


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


def _quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _load_http_mcp_operations() -> list[str]:
    tree = ast.parse(MCP_CATALOG_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "HTTP_MCP_OPERATIONS":
                    value = ast.literal_eval(node.value)
                    return list(value)
    raise RuntimeError("HTTP_MCP_OPERATIONS not found")


def _connect(database_url: str) -> Engine:
    return create_engine(database_url, future=True)


def _public_tables(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
        ).scalars()
        return [str(row) for row in rows]


def _row_count(engine: Engine, table_name: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT COUNT(*) FROM {_quote_ident(table_name)}")).scalar() or 0)


def _rls_enabled(engine: Engine, table_name: str) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT c.relrowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = :table_name
                """
            ),
            {"table_name": table_name},
        ).scalar()
        return bool(row)


def audit_tables(engine: Engine, registry: dict[str, Any]) -> CheckResult:
    registry_tables = {item["table"]: item for item in registry.get("tables", [])}
    live_tables = _public_tables(engine)
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}

    for table_name in live_tables:
        registry_entry = registry_tables.get(table_name)
        count = _row_count(engine, table_name)
        rls = _rls_enabled(engine, table_name)
        if registry_entry is None:
            failures.append({"table": table_name, "reason": "missing_from_ralph_registry", "row_count": count})
            continue
        classification = registry_entry.get("classification")
        status_counts[classification] = status_counts.get(classification, 0) + 1
        if classification in BLOCKING_CLASSIFICATIONS:
            failures.append({"table": table_name, "reason": "blocking_registry_classification", "classification": classification})
        if count == 0 and classification == "populated":
            failures.append({"table": table_name, "reason": "registry_says_populated_but_live_empty"})
        if count > 0 and classification in EMPTY_STATUSES:
            failures.append(
                {
                    "table": table_name,
                    "reason": "registry_says_empty_but_live_populated",
                    "classification": classification,
                    "row_count": count,
                }
            )
        if not rls:
            failures.append({"table": table_name, "reason": "rls_disabled"})
        registry_rls = registry_entry.get("rls_enabled")
        if registry_rls is not None and bool(registry_rls) != rls:
            warnings.append(
                {
                    "table": table_name,
                    "reason": "registry_rls_drift",
                    "registry_rls_enabled": registry_rls,
                    "live_rls_enabled": rls,
                }
            )

    extra_registry = sorted(set(registry_tables) - set(live_tables))
    for table_name in extra_registry:
        failures.append({"table": table_name, "reason": "registry_table_missing_in_database"})

    return CheckResult(
        name="database_table_registry_contract",
        ok=not failures,
        details={
            "live_tables": len(live_tables),
            "registry_tables": len(registry_tables),
            "classification_counts": status_counts,
            "failures": failures,
            "warnings": warnings[:50],
            "warning_count": len(warnings),
        },
    )


def _foreign_keys(engine: Engine) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    con.conname AS constraint_name,
                    child.relname AS child_table,
                    parent.relname AS parent_table,
                    array_agg(child_col.attname ORDER BY ck.ord) AS child_columns,
                    array_agg(parent_col.attname ORDER BY ck.ord) AS parent_columns
                FROM pg_constraint con
                JOIN pg_class child ON child.oid = con.conrelid
                JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
                JOIN pg_class parent ON parent.oid = con.confrelid
                JOIN pg_namespace parent_ns ON parent_ns.oid = parent.relnamespace
                JOIN unnest(con.conkey) WITH ORDINALITY AS ck(attnum, ord) ON true
                JOIN unnest(con.confkey) WITH ORDINALITY AS pk(attnum, ord) ON pk.ord = ck.ord
                JOIN pg_attribute child_col ON child_col.attrelid = child.oid AND child_col.attnum = ck.attnum
                JOIN pg_attribute parent_col ON parent_col.attrelid = parent.oid AND parent_col.attnum = pk.attnum
                WHERE con.contype = 'f'
                  AND child_ns.nspname = 'public'
                  AND parent_ns.nspname = 'public'
                GROUP BY con.conname, child.relname, parent.relname
                ORDER BY child.relname, con.conname
                """
            )
        ).mappings()
        return [dict(row) for row in rows]


def audit_foreign_keys(engine: Engine) -> CheckResult:
    failures: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []
    for fk in _foreign_keys(engine):
        child_table = fk["child_table"]
        parent_table = fk["parent_table"]
        child_columns = list(fk["child_columns"])
        parent_columns = list(fk["parent_columns"])
        join_clause = " AND ".join(
            f"c.{_quote_ident(child_col)} = p.{_quote_ident(parent_col)}"
            for child_col, parent_col in zip(child_columns, parent_columns, strict=True)
        )
        non_null_clause = " AND ".join(f"c.{_quote_ident(child_col)} IS NOT NULL" for child_col in child_columns)
        first_parent_col = _quote_ident(parent_columns[0])
        sql = f"""
            SELECT COUNT(*)
            FROM {_quote_ident(child_table)} c
            LEFT JOIN {_quote_ident(parent_table)} p ON {join_clause}
            WHERE {non_null_clause}
              AND p.{first_parent_col} IS NULL
        """
        with engine.connect() as conn:
            orphan_count = int(conn.execute(text(sql)).scalar() or 0)
        record = {
            "constraint": fk["constraint_name"],
            "child_table": child_table,
            "parent_table": parent_table,
            "child_columns": child_columns,
            "parent_columns": parent_columns,
            "orphan_count": orphan_count,
        }
        checked.append(record)
        if orphan_count:
            failures.append(record)

    return CheckResult(
        name="database_foreign_key_orphan_contract",
        ok=not failures,
        details={
            "relationships_checked": len(checked),
            "orphan_failures": failures,
        },
    )


def _get_json(client: httpx.Client, path: str, params: dict[str, Any] | None = None) -> tuple[int, dict[str, Any] | None, str]:
    response = _request_with_retry(client, "GET", path, params=params, headers=_headers())
    try:
        payload = response.json()
    except ValueError:
        payload = None
    return response.status_code, payload, response.text[:500]


def audit_domain_availability(base_url: str, registry: dict[str, Any]) -> CheckResult:
    failures: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}
    registry_tables = [item["table"] for item in registry.get("tables", [])]
    with httpx.Client(base_url=base_url, timeout=30) as client:
        for table_name in registry_tables:
            status_code, payload, text_preview = _get_json(client, f"/v1/domain-availability/{table_name}")
            if status_code != 200 or not payload:
                failures.append({"table": table_name, "reason": "availability_endpoint_failed", "status_code": status_code, "response": text_preview})
                continue
            status = payload.get("availability_status")
            status_counts[status] = status_counts.get(status, 0) + 1
            if payload.get("table") != table_name:
                failures.append({"table": table_name, "reason": "availability_table_mismatch", "payload_table": payload.get("table")})
            if status not in VALID_AVAILABILITY_STATUSES:
                failures.append({"table": table_name, "reason": "invalid_availability_status", "availability_status": status})
            row_count = payload.get("row_count")
            if status == "populated" and not isinstance(row_count, int):
                failures.append({"table": table_name, "reason": "populated_without_integer_row_count", "row_count": row_count})
            if status == "populated" and row_count == 0:
                failures.append({"table": table_name, "reason": "populated_with_zero_row_count"})
            if status in EMPTY_STATUSES and payload.get("safe_to_answer") is not False:
                failures.append({"table": table_name, "reason": "empty_status_not_fail_closed", "status": status})

    return CheckResult(
        name="domain_availability_per_table_contract",
        ok=not failures,
        details={
            "tables_checked": len(registry_tables),
            "status_counts": status_counts,
            "failures": failures,
        },
    )


def _mcp_session(client: httpx.Client) -> tuple[str | None, dict[str, Any]]:
    # /mcp opens an SSE stream; read headers only and close immediately.
    with client.stream(
        "GET",
        "/mcp",
        headers={"Accept": "text/event-stream", **_mcp_headers()},
    ) as handshake:
        session_id = handshake.headers.get("mcp-session-id") or handshake.headers.get(
            "Mcp-Session-Id"
        )
        details = {
            "handshake_status_code": handshake.status_code,
            "has_session_id": bool(session_id),
        }
        return session_id, details


def audit_mcp_tools(base_url: str) -> CheckResult:
    expected_operations = set(_load_http_mcp_operations())
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    with httpx.Client(base_url=base_url, timeout=60) as client:
        session_id, details = _mcp_session(client)
        if not session_id:
            return CheckResult("mcp_tools_contract", False, {**details, "failures": [{"reason": "missing_session_id"}]})
        rpc_headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Session-ID": session_id,
            **_mcp_headers(),
        }
        init = _request_with_retry(
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
                    "clientInfo": {"name": "esdata-deep-audit", "version": "1.0"},
                },
            },
        )
        tools_response = _request_with_retry(
            client,
            "POST",
            "/mcp",
            headers=rpc_headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        details["initialize_status_code"] = init.status_code
        details["tools_status_code"] = tools_response.status_code
        if init.status_code != 200 or tools_response.status_code != 200:
            failures.append({"reason": "mcp_rpc_failed", "initialize": init.text[:300], "tools": tools_response.text[:300]})
            return CheckResult("mcp_tools_contract", False, {**details, "failures": failures})
        payload = tools_response.json()
        tools = payload.get("result", {}).get("tools", [])
        tool_names = {tool.get("name") for tool in tools}
        missing = sorted(expected_operations - tool_names)
        extra = sorted(tool_names - expected_operations)
        if missing:
            failures.append({"reason": "missing_http_mcp_operations", "tools": missing})
        if extra:
            warnings.append({"reason": "extra_tools_not_in_http_mcp_operations", "tools": extra})
        for tool in tools:
            name = tool.get("name")
            if not name or not isinstance(name, str):
                failures.append({"reason": "tool_missing_name", "tool": tool})
            if not tool.get("description"):
                failures.append({"tool": name, "reason": "tool_missing_description"})
            schema = tool.get("inputSchema") or tool.get("input_schema")
            if not isinstance(schema, dict) or schema.get("type") != "object":
                failures.append({"tool": name, "reason": "input_schema_not_object", "schema": schema})
            if "outputSchema" not in tool and "output_schema" not in tool:
                warnings.append({"tool": name, "reason": "missing_output_schema"})

    return CheckResult(
        name="mcp_tools_contract",
        ok=not failures,
        details={
            **details,
            "expected_operations": len(expected_operations),
            "tools_returned": len(tool_names),
            "failures": failures,
            "warnings": warnings[:50],
            "warning_count": len(warnings),
        },
    )


def audit_actions_openapi(base_url: str) -> CheckResult:
    failures: list[dict[str, Any]] = []
    with httpx.Client(base_url=base_url, timeout=30) as client:
        status_code, spec, text_preview = _get_json(client, "/gpt-actions/modelos/openapi.json")
    if status_code != 200 or not spec:
        return CheckResult(
            "gpt_actions_openapi_contract",
            False,
            {"status_code": status_code, "response": text_preview},
        )
    paths = spec.get("paths", {})
    security = spec.get("components", {}).get("securitySchemes", {})
    if "ApiKeyAuth" not in security:
        failures.append({"reason": "missing_api_key_security_scheme"})
    operations_in_spec = {
        op.get("operationId")
        for methods in paths.values()
        for op in methods.values()
        if isinstance(op, dict)
    }
    expected_operations = set(_load_http_mcp_operations())
    missing_operations = sorted(expected_operations - operations_in_spec)
    if missing_operations:
        failures.append(
            {
                "reason": "missing_http_mcp_operations",
                "operation_ids": missing_operations,
            }
        )
    modelo_params = {
        param.get("name")
        for param in paths.get("/v1/modelos/{codigo}", {}).get("get", {}).get("parameters", [])
    }
    for required in {"casillas_limit", "casillas_offset", "related_limit", "articulos_offset"}:
        if required not in modelo_params:
            failures.append({"reason": "missing_get_modelo_pagination_param", "param": required})

    return CheckResult(
        "gpt_actions_openapi_contract",
        not failures,
        {
            "openapi": spec.get("openapi"),
            "path_count": len(paths),
            "operation_count": len(operations_in_spec),
            "expected_operations": len(expected_operations),
            "security_schemes": sorted(security),
            "failures": failures,
        },
    )


def audit_eurlex_esma_market_contracts(base_url: str) -> CheckResult:
    failures: list[dict[str, Any]] = []
    details: dict[str, Any] = {
        "eurlex_articles_checked": [],
        "esma_checks": {},
    }
    with httpx.Client(base_url=base_url, timeout=60) as client:
        for celex in ("32014R0600", "32023R1114", "32022R0858"):
            status_code, payload, text_preview = _get_json(client, f"/v1/eurlex/market/{celex}/articulos/1")
            record = {
                "celex": celex,
                "status_code": status_code,
                "verified": payload.get("verified") if payload else None,
                "completeness": payload.get("completeness") if payload else None,
                "quality_signal": payload.get("quality_signal") if payload else None,
                "text_length": len((payload or {}).get("texto") or ""),
                "source_url": (payload or {}).get("source_url"),
            }
            details["eurlex_articles_checked"].append(record)
            source_url = record["source_url"] or ""
            if status_code != 200 or not payload:
                failures.append({"check": "eurlex_market_article", "celex": celex, "reason": "endpoint_failed", "response": text_preview})
                continue
            if payload.get("celex") != celex:
                failures.append({"check": "eurlex_market_article", "celex": celex, "reason": "celex_mismatch", "payload_celex": payload.get("celex")})
            if payload.get("verified") is not True or payload.get("completeness") != "completa":
                failures.append({"check": "eurlex_market_article", "celex": celex, "reason": "not_authoritative_complete", "record": record})
            if len(payload.get("texto") or "") < 100:
                failures.append({"check": "eurlex_market_article", "celex": celex, "reason": "missing_real_text", "record": record})
            official_eu_source = (
                "eur-lex.europa.eu" in source_url
                or "publications.europa.eu" in source_url
            )
            if not official_eu_source:
                failures.append({"check": "eurlex_market_article", "celex": celex, "reason": "not_official_eu_sourced", "source_url": source_url})
            if "boe.es" in source_url.lower():
                failures.append({"check": "eurlex_market_article", "celex": celex, "reason": "cross_domain_contamination", "source_url": source_url})

        market_checks = [
            (
                "esma_schema",
                "/v1/esma/mifir/schemas",
                {},
                lambda payload: (
                    payload.get("total", 0) >= 1
                    and payload.get("verified") is True
                    and payload.get("completeness") == "completa"
                    and payload.get("quality_signal") == "official_esma_schema"
                    and all(item.get("source_url") and item.get("source_hash") for item in payload.get("items") or [])
                ),
            ),
            (
                "esma_transaction_reporting_fields",
                "/v1/esma/mifir/transaction-reporting/fields",
                {"limit": 5, "offset": 0},
                lambda payload: (
                    payload.get("total", 0) > 0
                    and payload.get("verified") is True
                    and payload.get("completeness") == "completa"
                    and payload.get("quality_signal") == "official_esma_xsd"
                    and all(
                        item.get("source_url")
                        and item.get("source_hash")
                        and item.get("quality_signal") == "official_esma_xsd"
                        for item in payload.get("items") or []
                    )
                ),
            ),
            (
                "esma_firds_files_partial",
                "/v1/esma/firds/files",
                {"limit": 5, "offset": 0},
                lambda payload: (
                    payload.get("total", 0) > 0
                    and payload.get("verified") is False
                    and payload.get("completeness") == "parcial"
                    and payload.get("quality_signal") == "evidence_limited_firds_pilot"
                ),
            ),
            (
                "esma_firds_unknown_isin_fail_closed",
                "/v1/esma/firds/instruments",
                {"isin": "ZZZZZZZZZZZZ", "limit": 5, "offset": 0},
                lambda payload: (
                    payload.get("total") == 0
                    and payload.get("items") == []
                    and payload.get("verified") is False
                    and payload.get("safe_to_answer") is False
                    and "absence is not authoritative" in (payload.get("evidence_notice") or "")
                ),
            ),
            (
                "esma_dlt_register_or_empty",
                "/v1/esma/dlt/infrastructures",
                {"limit": 10, "offset": 0},
                lambda payload: (
                    (
                        payload.get("total", 0) > 0
                        and payload.get("verified") is True
                        and payload.get("completeness") == "completa"
                        and payload.get("quality_signal") == "official_esma_dlt_register"
                    )
                    or (
                        payload.get("total") == 0
                        and payload.get("quality_signal") == "configured_but_unavailable"
                        and payload.get("safe_to_answer") is False
                    )
                ),
            ),
            (
                "esma_casp_register",
                "/v1/mica/casp/buscar",
                {"q": "crypto", "limit": 5, "offset": 0},
                lambda payload: (
                    payload.get("total", 0) > 0
                    and payload.get("quality_signal") == "official_esma_register"
                    and payload.get("availability_status") == "populated"
                    and payload.get("safe_to_answer") is True
                ),
            ),
        ]
        for name, path, params, predicate in market_checks:
            status_code, payload, text_preview = _get_json(client, path, params)
            details["esma_checks"][name] = {
                "path": path,
                "params": params,
                "status_code": status_code,
                "total": payload.get("total") if payload else None,
                "verified": payload.get("verified") if payload else None,
                "completeness": payload.get("completeness") if payload else None,
                "quality_signal": payload.get("quality_signal") if payload else None,
                "safe_to_answer": payload.get("safe_to_answer") if payload else None,
            }
            if status_code != 200 or not payload:
                failures.append({"check": name, "reason": "endpoint_failed", "response": text_preview})
            elif not predicate(payload):
                failures.append({"check": name, "reason": "contract_failed", "details": details["esma_checks"][name]})

    return CheckResult(
        "eurlex_esma_market_contracts",
        not failures,
        {
            **details,
            "failures": failures,
        },
    )


def audit_boe_core_legislation_contracts(base_url: str) -> CheckResult:
    failures: list[dict[str, Any]] = []
    details: dict[str, Any] = {"articles_checked": []}
    article_checks = [
        {
            "name": "trlirnr_article_14",
            "path": "/v1/legislacion/TRLIRNR/articulos/14",
            "expected_norma": "TRLIRNR",
            "expected_numero": "14",
            "expected_boe": "BOE-A-2004-4527",
            "required_text": "Rentas exentas",
        },
        {
            "name": "irnr_alias_article_14",
            "path": "/v1/legislacion/IRNR/articulos/14",
            "expected_norma": "TRLIRNR",
            "expected_numero": "14",
            "expected_boe": "BOE-A-2004-4527",
            "required_text": "Rentas exentas",
        },
        {
            "name": "liva_article_163_sexvicies",
            "path": "/v1/legislacion/LIVA/articulos/163%20sexvicies",
            "expected_norma": "LIVA",
            "expected_numero": "163 sexvicies",
            "expected_boe": "BOE-A-1992-28740",
            "required_text": None,
        },
    ]
    with httpx.Client(base_url=base_url, timeout=60) as client:
        for check in article_checks:
            status_code, payload, text_preview = _get_json(client, check["path"])
            text_value = (payload or {}).get("texto") or ""
            source_url = (payload or {}).get("source_url") or ""
            record = {
                "name": check["name"],
                "path": check["path"],
                "status_code": status_code,
                "norma": (payload or {}).get("norma"),
                "numero": (payload or {}).get("numero"),
                "boe_reference": (payload or {}).get("boe_reference"),
                "verified": (payload or {}).get("verified"),
                "completeness": (payload or {}).get("completeness"),
                "text_length": len(text_value),
                "source_url": source_url,
            }
            details["articles_checked"].append(record)
            if status_code != 200 or not payload:
                failures.append({"check": check["name"], "reason": "endpoint_failed", "response": text_preview})
                continue
            if payload.get("norma") != check["expected_norma"] or payload.get("numero") != check["expected_numero"]:
                failures.append({"check": check["name"], "reason": "article_identity_mismatch", "record": record})
            if payload.get("boe_reference") != check["expected_boe"]:
                failures.append({"check": check["name"], "reason": "boe_reference_mismatch", "record": record})
            if payload.get("verified") is not True or payload.get("completeness") != "completa":
                failures.append({"check": check["name"], "reason": "not_verified_complete", "record": record})
            if len(text_value) < 50:
                failures.append({"check": check["name"], "reason": "missing_real_text", "record": record})
            required_text = check.get("required_text")
            if required_text and required_text.lower() not in text_value.lower():
                failures.append({"check": check["name"], "reason": "required_text_missing", "required_text": required_text, "record": record})
            if not source_url.startswith(f"https://www.boe.es/buscar/act.php?id={check['expected_boe']}"):
                failures.append({"check": check["name"], "reason": "not_official_boe_sourced", "record": record})

    return CheckResult(
        "boe_core_legislation_contracts",
        not failures,
        {
            **details,
            "failures": failures,
        },
    )


def audit_aeat_instruction_key_contracts(base_url: str) -> CheckResult:
    failures: list[dict[str, Any]] = []
    details: dict[str, Any] = {
        "modelo_290": {},
        "fatca_query": {},
        "completed_models": [],
    }
    with httpx.Client(base_url=base_url, timeout=60) as client:
        status_code, payload, text_preview = _get_json(client, "/v1/modelos/aeat/290")
        if status_code != 200 or not payload:
            failures.append({"check": "modelo_290_detail", "reason": "endpoint_failed", "response": text_preview})
        else:
            reglas = payload.get("reglas_inclusion") or []
            detalles_reglas = [
                {
                    "supuesto": regla.get("supuesto"),
                    "decision": regla.get("decision"),
                    "source_url": regla.get("source_url"),
                }
                for regla in reglas
            ]
            details["modelo_290"] = {
                "verified": payload.get("verified"),
                "completeness": payload.get("completeness"),
                "claves": len(payload.get("claves") or []),
                "instrucciones": len(payload.get("instrucciones") or []),
                "reglas": len(reglas),
                "reglas_inclusion": detalles_reglas,
            }
            if payload.get("verified") is not True or payload.get("completeness") != "completa":
                failures.append({"check": "modelo_290_detail", "reason": "not_verified_complete", "details": details["modelo_290"]})
            if not payload.get("claves") or not payload.get("instrucciones") or not reglas:
                failures.append({"check": "modelo_290_detail", "reason": "missing_keys_instructions_or_rules", "details": details["modelo_290"]})

            def _find_rule(term: str, decision: str) -> dict[str, Any] | None:
                for regla in reglas:
                    if term in (regla.get("supuesto") or "").lower() and regla.get("decision") == decision:
                        return regla
                return None

            passive_include = _find_rule("pasiva con", "INCLUIR")
            passive_exclude = _find_rule("pasiva sin", "EXCLUIR")
            active_exclude = _find_rule("activa", "EXCLUIR")
            if not passive_include:
                failures.append({"check": "modelo_290_rules", "reason": "missing_passive_include_rule"})
            if not passive_exclude:
                failures.append({"check": "modelo_290_rules", "reason": "missing_passive_exclude_rule"})
            if not active_exclude:
                failures.append({"check": "modelo_290_rules", "reason": "missing_active_exclude_rule"})
            for name, rule in {
                "passive_include": passive_include,
                "passive_exclude": passive_exclude,
                "active_exclude": active_exclude,
            }.items():
                if rule and not rule.get("source_url"):
                    failures.append({"check": "modelo_290_rules", "reason": "missing_rule_source_url", "rule": name})

        status_code, consulta, text_preview = _get_json(
            client,
            "/v1/consulta",
            {"q": "FATCA passive NFFE modelo 290"},
        )
        if status_code != 200 or not consulta:
            failures.append({"check": "consulta_fatca_routing", "reason": "endpoint_failed", "response": text_preview})
        else:
            codigos = [item.get("codigo") for item in consulta.get("modelos") or []]
            details["fatca_query"] = {
                "status": consulta.get("status"),
                "safe_to_answer": consulta.get("safe_to_answer"),
                "codigos": codigos,
            }
            if "290" not in codigos:
                failures.append({"check": "consulta_fatca_routing", "reason": "modelo_290_missing", "details": details["fatca_query"]})
            if {"216", "296"} & set(codigos):
                failures.append({"check": "consulta_fatca_routing", "reason": "irnr_contamination", "details": details["fatca_query"]})

        status_code, modelo_198, text_preview = _get_json(client, "/v1/modelos/aeat/198")
        if status_code != 200 or not modelo_198:
            failures.append({"check": "aeat_completed_models", "reason": "endpoint_failed", "response": text_preview})
        else:
            completed = []
            if modelo_198.get("verified") is True and modelo_198.get("completeness") == "completa":
                completed.append(modelo_198.get("codigo"))
            details["completed_models"] = completed
            if not completed:
                failures.append({"check": "aeat_completed_models", "reason": "no_completed_verified_models"})

    return CheckResult(
        "aeat_instruction_key_contracts",
        not failures,
        {
            **details,
            "failures": failures,
        },
    )


def audit_teac_sepblac_contracts(base_url: str, engine: Engine) -> CheckResult:
    failures: list[dict[str, Any]] = []
    details: dict[str, Any] = {}

    with engine.connect() as conn:
        teac_count = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM documento_interpretativo
                    WHERE tipo_documento='resolucion_teac'
                    """
                )
            ).scalar()
            or 0
        )
        teac_url_count = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM documento_interpretativo
                    WHERE tipo_documento='resolucion_teac'
                      AND url_fuente IS NOT NULL
                    """
                )
            ).scalar()
            or 0
        )
        sepblac_obligacion_count = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM documento_interpretativo
                    WHERE tipo_documento='obligacion_sepblac'
                    """
                )
            ).scalar()
            or 0
        )
        sepblac_sociedad_valores_count = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM documento_interpretativo
                    WHERE tipo_documento='obligacion_sepblac'
                      AND (
                        metadata->>'sujeto_obligado' IN ('sociedad_valores', 'all')
                        OR LOWER(COALESCE(texto, '')) LIKE '%sociedad%valores%'
                        OR LOWER(COALESCE(titulo, '')) LIKE '%sociedad%valores%'
                      )
                    """
                )
            ).scalar()
            or 0
        )
        rd_304_articles = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM articulo a
                    JOIN norma n ON n.id=a.norma_id
                    WHERE n.codigo='RD_304_2014'
                    """
                )
            ).scalar()
            or 0
        )

    details["db"] = {
        "teac_count": teac_count,
        "teac_url_count": teac_url_count,
        "teac_url_percent": round((teac_url_count / teac_count) * 100, 2)
        if teac_count
        else 0,
        "sepblac_obligacion_count": sepblac_obligacion_count,
        "sepblac_sociedad_valores_applicable_count": sepblac_sociedad_valores_count,
        "sociedad_valores_basis": "obligacion_sepblac rows explicitly tagged sociedad_valores or all, or matching text/title",
        "rd_304_2014_articles": rd_304_articles,
    }
    if teac_count < 500:
        failures.append({"check": "teac_count", "reason": "count_below_500", "value": teac_count})
    if teac_count and (teac_url_count / teac_count) < 0.9:
        failures.append(
            {
                "check": "teac_url_coverage",
                "reason": "url_oficial_below_90_percent",
                "value": teac_url_count,
                "total": teac_count,
            }
        )
    if sepblac_obligacion_count < 5:
        failures.append(
            {
                "check": "sepblac_obligacion_count",
                "reason": "count_below_5",
                "value": sepblac_obligacion_count,
            }
        )
    if sepblac_sociedad_valores_count < 1:
        failures.append(
            {
                "check": "sepblac_sociedad_valores_applicability",
                "reason": "no_obligacion_sepblac_row_applicable_to_sociedad_valores",
            }
        )
    if rd_304_articles < 10:
        failures.append(
            {
                "check": "rd_304_2014_articles",
                "reason": "article_count_below_10",
                "value": rd_304_articles,
            }
        )

    with httpx.Client(base_url=base_url, timeout=60) as client:
        status_code, payload, text_preview = _get_json(
            client,
            "/v1/doctrina/buscar",
            {
                "q": "retencion no residente",
                "tipo": "resolucion_teac",
                "organismo_emisor": "TEAC",
            },
        )
        resultados = (payload or {}).get("resultados") or []
        teac_results = [
            item
            for item in resultados
            if item.get("tipo_documento") == "resolucion_teac"
            or str(item.get("organismo_emisor") or "").upper() == "TEAC"
        ]
        details["teac_query"] = {
            "status_code": status_code,
            "returned": len(resultados),
            "teac_results": len(teac_results),
        }
        if status_code != 200 or not teac_results:
            failures.append(
                {
                    "check": "teac_retencion_no_residente_query",
                    "reason": "no_resolucion_teac_result",
                    "response": text_preview,
                }
            )

        status_code, payload, text_preview = _get_json(
            client,
            "/v1/sepblac",
            {"q": "sujetos"},
        )
        documentos = (payload or {}).get("documentos") or []
        sepblac_obligaciones = [
            item for item in documentos if item.get("tipo_documento") == "obligacion_sepblac"
        ]
        details["sepblac_sociedad_valores_query"] = {
            "status_code": status_code,
            "returned": len(documentos),
            "obligacion_sepblac_results": len(sepblac_obligaciones),
            "query": "sujetos",
        }
        if status_code != 200 or not sepblac_obligaciones:
            failures.append(
                {
                    "check": "sepblac_sociedad_valores_obligacion_query",
                    "reason": "no_obligacion_sepblac_result",
                    "response": text_preview,
                }
            )

        status_code, payload, text_preview = _get_json(
            client,
            "/v1/legislacion/RD_304_2014/articulos/4",
        )
        text_value = (payload or {}).get("texto") or ""
        details["rd_304_article_4"] = {
            "status_code": status_code,
            "norma": (payload or {}).get("norma"),
            "numero": (payload or {}).get("numero"),
            "boe_reference": (payload or {}).get("boe_reference"),
            "text_length": len(text_value),
        }
        if (
            status_code != 200
            or not payload
            or payload.get("norma") != "RD_304_2014"
            or payload.get("numero") != "4"
            or payload.get("boe_reference") != "BOE-A-2014-4742"
            or "identificación formal" not in text_value.lower()
        ):
            failures.append(
                {
                    "check": "rd_304_2014_article_4",
                    "reason": "article_contract_failed",
                    "response": text_preview,
                }
            )

    return CheckResult(
        "teac_sepblac_sprint_a_contracts",
        not failures,
        {
            **details,
            "failures": failures,
        },
    )


def audit_profile_applicability_contracts(base_url: str) -> CheckResult:
    failures: list[dict[str, Any]] = []
    details: dict[str, Any] = {}

    with httpx.Client(base_url=base_url, timeout=60) as client:
        fiscal_status, fiscal_payload, fiscal_preview = _get_json(
            client,
            "/v1/perfil/sociedad_valores/obligaciones",
            params={"dominio": "FISCAL"},
        )
        pbc_status, pbc_payload, pbc_preview = _get_json(
            client,
            "/v1/perfil/sociedad_valores/obligaciones",
            params={"dominio": "PBC_FT"},
        )

    fiscal_obligaciones = fiscal_payload.get("obligaciones") if isinstance(fiscal_payload, dict) else []
    pbc_obligaciones = pbc_payload.get("obligaciones") if isinstance(pbc_payload, dict) else []
    fiscal_modelos = {
        item.get("modelo_aeat")
        for item in (fiscal_obligaciones or [])
        if isinstance(item, dict) and item.get("modelo_aeat")
    }
    pbc_tipos = {
        item.get("obligacion_tipo")
        for item in (pbc_obligaciones or [])
        if isinstance(item, dict)
    }
    missing_source = [
        item.get("descripcion")
        for item in [*(fiscal_obligaciones or []), *(pbc_obligaciones or [])]
        if isinstance(item, dict) and not item.get("source_url")
    ]

    details.update(
        {
            "fiscal_status": fiscal_status,
            "pbc_status": pbc_status,
            "fiscal_total": fiscal_payload.get("total") if isinstance(fiscal_payload, dict) else None,
            "pbc_total": pbc_payload.get("total") if isinstance(pbc_payload, dict) else None,
            "fiscal_modelos": sorted(str(modelo) for modelo in fiscal_modelos),
            "pbc_tipos": sorted(str(tipo) for tipo in pbc_tipos),
            "missing_source_url": missing_source[:20],
            "fiscal_safe_to_answer_present": isinstance(fiscal_payload, dict)
            and "safe_to_answer" in fiscal_payload,
            "pbc_safe_to_answer_present": isinstance(pbc_payload, dict)
            and "safe_to_answer" in pbc_payload,
            "fiscal_evidence_notice_present": isinstance(fiscal_payload, dict)
            and bool(fiscal_payload.get("evidence_notice")),
            "pbc_evidence_notice_present": isinstance(pbc_payload, dict)
            and bool(pbc_payload.get("evidence_notice")),
        }
    )

    if fiscal_status != 200 or not isinstance(fiscal_payload, dict):
        failures.append({"check": "fiscal_endpoint", "status": fiscal_status, "response": fiscal_preview})
    if pbc_status != 200 or not isinstance(pbc_payload, dict):
        failures.append({"check": "pbc_endpoint", "status": pbc_status, "response": pbc_preview})
    if not {"200", "303", "193", "198"} <= fiscal_modelos:
        failures.append(
            {
                "check": "fiscal_modelos",
                "missing": sorted({"200", "303", "193", "198"} - fiscal_modelos),
            }
        )
    if not {"COMUNICACION_INDICIO", "DILIGENCIA_DEBIDA"} <= pbc_tipos:
        failures.append(
            {
                "check": "pbc_obligation_types",
                "missing": sorted({"COMUNICACION_INDICIO", "DILIGENCIA_DEBIDA"} - pbc_tipos),
            }
        )
    if missing_source:
        failures.append({"check": "source_url_required", "missing": missing_source[:20]})
    for name, payload in (("fiscal", fiscal_payload), ("pbc", pbc_payload)):
        if not isinstance(payload, dict) or not payload.get("evidence_notice"):
            failures.append({"check": f"{name}_evidence_notice"})
        if not isinstance(payload, dict) or "safe_to_answer" not in payload:
            failures.append({"check": f"{name}_safe_to_answer"})

    with httpx.Client(base_url=base_url, timeout=60) as client:
        profile_checks = {
            "sociedad_valores_fiscal": (
                "/v1/perfil/sociedad_valores/obligaciones",
                {"dominio": "FISCAL"},
            ),
            "eaf_cnmv": ("/v1/perfil/eaf/obligaciones", {"dominio": "CNMV"}),
            "entidad_credito_cnmv": (
                "/v1/perfil/entidad_credito/obligaciones",
                {"dominio": "CNMV"},
            ),
            "empresa_servicios_pago_fiscal": (
                "/v1/perfil/empresa_servicios_pago/obligaciones",
                {"dominio": "FISCAL"},
            ),
            "sgiic_cnmv": ("/v1/perfil/sgiic/obligaciones", {"dominio": "CNMV"}),
            "all_profiles": ("/v1/perfil", {}),
        }
        extra_payloads: dict[str, Any] = {}
        for check_name, (path, params) in profile_checks.items():
            status, payload, preview = _get_json(client, path, params=params)
            details[f"{check_name}_status"] = status
            if status != 200:
                failures.append({"check": check_name, "status": status, "response": preview})
            extra_payloads[check_name] = payload
        calendar_q3_status, calendar_q3_payload, calendar_q3_preview = _get_json(
            client,
            "/v1/perfil/sociedad_valores/obligaciones/calendario/2026-Q3",
        )
        catalog_123_status, catalog_123_payload, catalog_123_preview = _get_json(
            client,
            "/v1/modelos/catalogo",
            params={"codigo": "123"},
        )
        catalog_289_status, catalog_289_payload, catalog_289_preview = _get_json(
            client,
            "/v1/modelos/catalogo",
            params={"codigo": "289"},
        )
        modelo_289_status, modelo_289_payload, modelo_289_preview = _get_json(
            client,
            "/v1/modelos/aeat/289",
        )
        dora_rts_1774_status, dora_rts_1774_payload, dora_rts_1774_preview = _get_json(
            client,
            "/v1/norma/eu",
            params={"termino": "32024R1774"},
        )
        details["calendar_q3_status"] = calendar_q3_status
        details["catalog_123_status"] = catalog_123_status
        details["catalog_289_status"] = catalog_289_status
        details["modelo_289_status"] = modelo_289_status
        details["dora_rts_1774_status"] = dora_rts_1774_status

    sociedad_fiscal_items = extra_payloads.get("sociedad_valores_fiscal", {}).get(
        "obligaciones", []
    )
    eaf_items = extra_payloads.get("eaf_cnmv", {}).get("obligaciones", [])
    entidad_items = extra_payloads.get("entidad_credito_cnmv", {}).get("obligaciones", [])
    esp_items = extra_payloads.get("empresa_servicios_pago_fiscal", {}).get("obligaciones", [])
    sgiic_items = extra_payloads.get("sgiic_cnmv", {}).get("obligaciones", [])
    calendar_q3_items = calendar_q3_payload if isinstance(calendar_q3_payload, list) else []
    catalog_123_items = catalog_123_payload if isinstance(catalog_123_payload, list) else []
    catalog_289_items = catalog_289_payload if isinstance(catalog_289_payload, list) else []
    dora_rts_1774_items = dora_rts_1774_payload if isinstance(dora_rts_1774_payload, list) else []
    modelo_289_context = (
        modelo_289_payload.get("obligation_context")
        if isinstance(modelo_289_payload, dict)
        else []
    )
    all_profile_items: list[dict[str, Any]] = []
    with httpx.Client(base_url=base_url, timeout=60) as client:
        profile_obligaciones: dict[str, list[dict[str, Any]]] = {}
        for profile in (
            "sociedad_valores",
            "agencia_valores",
            "sgiic",
            "eaf",
            "entidad_credito",
            "empresa_servicios_pago",
        ):
            status, payload, _preview = _get_json(
                client,
                f"/v1/perfil/{profile}/obligaciones",
                params={},
            )
            if status == 200 and isinstance(payload, dict):
                items = [item for item in (payload.get("obligaciones") or []) if isinstance(item, dict)]
                profile_obligaciones[profile] = items
                all_profile_items.extend(items)

    details["eaf_cnmv_descriptions"] = [item.get("descripcion") for item in eaf_items if isinstance(item, dict)]
    details["entidad_credito_cnmv_descriptions"] = [
        item.get("descripcion") for item in entidad_items if isinstance(item, dict)
    ]
    details["empresa_servicios_pago_fiscal_modelos"] = [
        item.get("modelo_aeat") for item in esp_items if isinstance(item, dict)
    ]
    details["sgiic_cnmv_descriptions"] = [item.get("descripcion") for item in sgiic_items if isinstance(item, dict)]
    sociedad_items = profile_obligaciones.get("sociedad_valores", [])
    sociedad_ifr_obligations = [
        item
        for item in sociedad_items
        if item.get("norma_codigo") == "32019R2033"
        and (
            "prudencial" in str(item.get("descripcion", "")).lower()
            or "recursos propios" in str(item.get("descripcion", "")).lower()
        )
    ]
    sgiic_annex_iv_count = sum(
        1
        for item in sgiic_items
        if isinstance(item, dict) and "annex iv" in str(item.get("descripcion", "")).lower()
    )
    verified_partial_bad_notice = [
        item.get("descripcion")
        for item in all_profile_items
        if isinstance(item, dict)
        and item.get("verified") is True
        and item.get("completeness") == "parcial"
        and (
            "condicional" not in str(item.get("evidence_notice", "")).lower()
            or "evidence_limited" in str(item.get("evidence_notice", "")).lower()
        )
    ]
    details["sociedad_valores_ifr_obligations"] = [
        item.get("descripcion") for item in sociedad_ifr_obligations
    ]
    details["sgiic_annex_iv_count"] = sgiic_annex_iv_count
    details["verified_partial_bad_notice"] = verified_partial_bad_notice[:20]
    q3_modelos = {
        item.get("modelo_aeat")
        for item in calendar_q3_items
        if isinstance(item, dict) and item.get("modelo_aeat")
    }
    catalog_first = catalog_123_items[0] if catalog_123_items and isinstance(catalog_123_items[0], dict) else {}
    catalog_289_first = catalog_289_items[0] if catalog_289_items and isinstance(catalog_289_items[0], dict) else {}
    modelo_289_sociedad_context = [
        item
        for item in (modelo_289_context or [])
        if isinstance(item, dict) and item.get("perfil_codigo") == "sociedad_valores"
    ]
    modelo_289_profile_items = [
        item
        for item in sociedad_items
        if isinstance(item, dict) and item.get("modelo_aeat") == "289"
    ]
    details["calendar_q3_modelos"] = sorted(str(modelo) for modelo in q3_modelos)
    details["sociedad_valores_fiscal_modelos"] = sorted(
        str(item.get("modelo_aeat"))
        for item in sociedad_fiscal_items
        if isinstance(item, dict) and item.get("modelo_aeat")
    )
    details["catalog_123_keys"] = sorted(catalog_first.keys()) if isinstance(catalog_first, dict) else []
    details["catalog_289_counts"] = {
        "codigo": catalog_289_first.get("codigo") if isinstance(catalog_289_first, dict) else None,
        "instrucciones_count": (
            catalog_289_first.get("instrucciones_count")
            if isinstance(catalog_289_first, dict)
            else None
        ),
        "reglas_inclusion_count": (
            catalog_289_first.get("reglas_inclusion_count")
            if isinstance(catalog_289_first, dict)
            else None
        ),
        "has_obligation_context": (
            "obligation_context" in catalog_289_first
            if isinstance(catalog_289_first, dict)
            else None
        ),
    }
    details["modelo_289_sociedad_context"] = modelo_289_sociedad_context[:1]
    details["modelo_289_profile_evidence_notice"] = [
        item.get("evidence_notice") for item in modelo_289_profile_items
    ]
    sociedad_rts_items = [
        item
        for item in sociedad_items
        if isinstance(item, dict) and item.get("norma_codigo") in {"32017R0587", "32017R0583"}
    ]
    sociedad_rts1_items = [
        item for item in sociedad_rts_items if item.get("norma_codigo") == "32017R0587"
    ]
    eaf_rts_items = [
        item
        for item in profile_obligaciones.get("eaf", [])
        if isinstance(item, dict) and item.get("norma_codigo") in {"32017R0587", "32017R0583"}
    ]
    agencia_dora_control_items = [
        item
        for item in profile_obligaciones.get("agencia_valores", [])
        if isinstance(item, dict)
        and item.get("norma_codigo") == "32022R2554"
        and item.get("obligacion_tipo") == "CONTROL_INTERNO"
    ]
    eaf_dora_items = [
        item
        for item in profile_obligaciones.get("eaf", [])
        if isinstance(item, dict) and item.get("norma_codigo") == "32022R2554"
    ]
    dora_rts_1774_match = [
        item
        for item in dora_rts_1774_items
        if isinstance(item, dict)
        and item.get("celex") == "32024R1774"
        and item.get("tipo_norma") == "reglamento_delegado_ue"
    ]
    details["sociedad_valores_rts1_rts2_count"] = len(sociedad_rts_items)
    details["sociedad_valores_rts1_descriptions"] = [
        item.get("descripcion") for item in sociedad_rts1_items
    ]
    details["eaf_rts1_rts2_count"] = len(eaf_rts_items)
    details["agencia_valores_dora_control_count"] = len(agencia_dora_control_items)
    details["eaf_dora_count"] = len(eaf_dora_items)
    details["eaf_dora_completeness"] = [
        item.get("completeness") for item in eaf_dora_items
    ]
    details["dora_rts_1774_match"] = dora_rts_1774_match[:1]

    if not any("idoneidad" in str(item.get("descripcion", "")).lower() for item in eaf_items if isinstance(item, dict)):
        failures.append({"check": "eaf_cnmv_idoneidad"})
    if any(
        needle in str(item.get("descripcion", "")).lower()
        for item in eaf_items
        if isinstance(item, dict)
        for needle in ("transaction reporting", "mejor ejecucion")
    ):
        failures.append({"check": "eaf_forbidden_execution_obligations"})
    if not any(
        needle in str(item.get("descripcion", "")).lower()
        for item in entidad_items
        if isinstance(item, dict)
        for needle in ("corep", "finrep")
    ):
        failures.append({"check": "entidad_credito_corep_finrep"})
    if not any(
        item.get("modelo_aeat") == "303" and item.get("completeness") == "completa"
        for item in esp_items
        if isinstance(item, dict)
    ):
        failures.append({"check": "empresa_servicios_pago_modelo_303_completa"})
    if not any("annex iv" in str(item.get("descripcion", "")).lower() for item in sgiic_items if isinstance(item, dict)):
        failures.append({"check": "sgiic_aifmd_annex_iv"})
    if not sociedad_ifr_obligations:
        failures.append({"check": "sociedad_valores_ifr_prudential_obligation"})
    if sgiic_annex_iv_count != 1:
        failures.append({"check": "sgiic_aifmd_annex_iv_exactly_one", "count": sgiic_annex_iv_count})
    if verified_partial_bad_notice:
        failures.append(
            {
                "check": "verified_partial_notice_conditional",
                "items": verified_partial_bad_notice[:20],
            }
        )
    if (
        calendar_q3_status != 200
        or "303" not in q3_modelos
        or "202" in q3_modelos
        or any(
            not item.get("plazo_descripcion")
            for item in calendar_q3_items
            if isinstance(item, dict)
        )
    ):
        failures.append(
            {
                "check": "calendar_q3_structured",
                "status": calendar_q3_status,
                "modelos": sorted(str(modelo) for modelo in q3_modelos),
                "response": calendar_q3_preview,
            }
        )
    sociedad_fiscal_modelos = {
        item.get("modelo_aeat")
        for item in sociedad_fiscal_items
        if isinstance(item, dict) and item.get("modelo_aeat")
    }
    if {"123", "124"} & sociedad_fiscal_modelos:
        failures.append(
            {
                "check": "sociedad_valores_fiscal_no_123_124",
                "modelos": sorted(str(modelo) for modelo in sociedad_fiscal_modelos),
            }
        )
    if (
        catalog_123_status != 200
        or not catalog_first
        or "verified" in catalog_first
        or "evidence_notice" in catalog_first
    ):
        failures.append(
            {
                "check": "catalog_tool_has_no_profile_evidence",
                "status": catalog_123_status,
                "response": catalog_123_preview,
            }
        )
    if (
        catalog_289_status != 200
        or not catalog_289_first
        or catalog_289_first.get("codigo") != "289"
        or int(catalog_289_first.get("instrucciones_count") or 0) < 5
        or int(catalog_289_first.get("reglas_inclusion_count") or 0) < 6
        or "obligation_context" in catalog_289_first
    ):
        failures.append(
            {
                "check": "catalog_289_crs_counts_no_obligation_context",
                "status": catalog_289_status,
                "response": catalog_289_preview,
                "counts": details["catalog_289_counts"],
            }
        )
    if (
        modelo_289_status != 200
        or not modelo_289_sociedad_context
        or modelo_289_sociedad_context[0].get("verified") is not True
    ):
        failures.append(
            {
                "check": "modelo_289_obligation_context_verified",
                "status": modelo_289_status,
                "response": modelo_289_preview,
            }
        )
    if not any(
        "Verificado" in str(item.get("evidence_notice") or "")
        and "evidence_limited" not in str(item.get("evidence_notice") or "")
        for item in modelo_289_profile_items
        if isinstance(item, dict)
    ):
        failures.append({"check": "modelo_289_profile_evidence_notice_verified"})
    if not sociedad_rts1_items:
        failures.append({"check": "sociedad_valores_rts1_obligation_present"})
    if not any(
        "Verificado" in str(item.get("evidence_notice") or "")
        for item in sociedad_rts1_items
    ):
        failures.append({"check": "sociedad_valores_rts1_evidence_notice_verified"})
    if not all(item.get("completeness") == "parcial" for item in sociedad_rts_items):
        failures.append({"check": "sociedad_valores_rts_completeness_parcial"})
    sociedad_rts_pre_trade_items = [
        item
        for item in sociedad_rts_items
        if "pre-negociacion" in str(item.get("descripcion", "")).lower()
    ]
    if not all(
        item.get("notas")
        and (
            "Internalizador Sistematico" in str(item.get("notas"))
            or "estatus SI" in str(item.get("notas"))
            or "registrada como SI" in str(item.get("notas"))
        )
        for item in sociedad_rts_pre_trade_items
    ):
        failures.append({"check": "sociedad_valores_rts_notas_si_conditionality"})
    if eaf_rts_items:
        failures.append({"check": "eaf_has_zero_rts1_rts2_obligations", "items": eaf_rts_items[:5]})
    if not agencia_dora_control_items:
        failures.append({"check": "agencia_valores_dora_control_interno_present"})
    if not eaf_dora_items or not all(item.get("completeness") == "parcial" for item in eaf_dora_items):
        failures.append(
            {
                "check": "eaf_dora_all_parcial",
                "items": [
                    {
                        "descripcion": item.get("descripcion"),
                        "completeness": item.get("completeness"),
                    }
                    for item in eaf_dora_items
                ],
            }
        )
    if not eaf_dora_items or not all(
        "microempresa" in str(item.get("notas") or "").lower()
        for item in eaf_dora_items
    ):
        failures.append(
            {
                "check": "eaf_dora_notas_microempresa",
                "items": [
                    {
                        "descripcion": item.get("descripcion"),
                        "notas": item.get("notas"),
                    }
                    for item in eaf_dora_items
                ],
            }
        )
    if dora_rts_1774_status != 200 or not dora_rts_1774_match:
        failures.append(
            {
                "check": "buscar_norma_eu_32024R1774_reglamento_delegado",
                "status": dora_rts_1774_status,
                "response": dora_rts_1774_preview,
            }
        )
    missing_profile_source = [
        item.get("descripcion")
        for item in all_profile_items
        if isinstance(item, dict) and not item.get("source_url")
    ]
    details["all_profiles_source_url_missing"] = missing_profile_source[:20]
    if missing_profile_source:
        failures.append({"check": "all_profiles_source_url_required", "missing": missing_profile_source[:20]})

    try:
        with httpx.Client(base_url=base_url, timeout=60) as client:
            session_id, session_details = _mcp_session(client)
            details["mcp_session"] = session_details
            if not session_id:
                failures.append({"check": "mcp_tool_registry", "reason": "missing_session_id"})
            else:
                rpc_headers = {
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "MCP-Session-ID": session_id,
                    **_mcp_headers(),
                }
                _request_with_retry(
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
                            "clientInfo": {"name": "esdata-profile-audit", "version": "1.0"},
                        },
                    },
                )
                tools_response = _request_with_retry(
                    client,
                    "POST",
                    "/mcp",
                    headers=rpc_headers,
                    json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                )
                tools_payload = tools_response.json()
                tools = {
                    tool.get("name"): tool
                    for tool in ((tools_payload.get("result") or {}).get("tools") or [])
                    if isinstance(tool, dict)
                }
                tool = tools.get("obtener_obligaciones_perfil") or {}
                description = tool.get("description") or ""
                details["obtener_obligaciones_perfil_description_length"] = len(description)
                try:
                    api_path = ROOT / "apps" / "api"
                    if str(api_path) not in sys.path:
                        sys.path.insert(0, str(api_path))
                    from mcp_catalog import MCP_TOOL_ROUTING_POLICY  # type: ignore

                    details["routing_policy_length"] = len(MCP_TOOL_ROUTING_POLICY)
                    if "calendario_obligaciones_perfil" not in MCP_TOOL_ROUTING_POLICY:
                        failures.append({"check": "mcp_tool_routing_policy_importable"})
                except Exception as exc:
                    failures.append({"check": "mcp_tool_routing_policy_importable", "error": str(exc)})
                expected_core_tools = {
                    "listar_perfiles_entidad",
                    "obtener_obligaciones_perfil",
                    "calendario_obligaciones_perfil",
                    "buscar_norma_eu",
                    "buscar_modelos_aeat_catalogo",
                }
                present_core_tools = sorted(name for name in expected_core_tools if name in tools)
                details["profile_mcp_tools_present"] = present_core_tools
                details["profile_mcp_core_tool_count"] = len(present_core_tools)
                if len(description) <= 50:
                    failures.append({"check": "tool_description_length", "tool": "obtener_obligaciones_perfil"})
                if "NO" not in description or "calendario_obligaciones_perfil" not in description:
                    failures.append(
                        {
                            "check": "obtener_obligaciones_routing_description",
                            "description": description[:300],
                        }
                    )
                missing_core_tools = sorted(expected_core_tools - set(present_core_tools))
                if missing_core_tools:
                    failures.append(
                        {
                            "check": "core_mcp_tool_registry",
                            "missing": missing_core_tools,
                        }
                    )
                calendar_description = (
                    tools.get("calendario_obligaciones_perfil", {}).get("description") or ""
                )
                catalog_description = (
                    tools.get("buscar_modelos_aeat_catalogo", {}).get("description") or ""
                )
                if "quarter" not in calendar_description or "este trimestre" not in calendar_description:
                    failures.append(
                        {
                            "check": "calendar_tool_quarter_description",
                            "description": calendar_description[:200],
                        }
                    )
                if "NO indica" not in catalog_description:
                    failures.append(
                        {
                            "check": "catalog_tool_layer_description",
                            "description": catalog_description[:200],
                        }
                    )
    except Exception as exc:
        failures.append({"check": "mcp_tool_registry", "error": str(exc)})

    return CheckResult(
        "profile_applicability_contracts",
        not failures,
        {
            **details,
            "failures": failures,
        },
    )


def audit_eu_norm_contracts(base_url: str, engine: Engine) -> CheckResult:
    failures: list[dict[str, Any]] = []
    details: dict[str, Any] = {}

    with engine.connect() as conn:
        eu_count = int(
            conn.execute(
                text("SELECT COUNT(*) FROM norma WHERE celex IS NOT NULL AND tipo_norma IS NOT NULL")
            ).scalar()
            or 0
        )
        sociedad_verified = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM obligacion_perfil
                    WHERE perfil_codigo='sociedad_valores'
                      AND verified=true
                    """
                )
            ).scalar()
            or 0
        )
    details["eu_norms_with_celex"] = eu_count
    details["sociedad_valores_verified_count"] = sociedad_verified
    if eu_count < 10:
        failures.append({"check": "eu_norms_with_celex", "value": eu_count, "minimum": 10})
    if sociedad_verified < 20:
        failures.append({"check": "sociedad_valores_verified_count", "value": sociedad_verified, "minimum": 20})

    with httpx.Client(base_url=base_url, timeout=60) as client:
        list_status, list_payload, list_preview = _get_json(client, "/v1/norma/eu")
        mifir_status, mifir_payload, mifir_preview = _get_json(client, "/v1/norma/eu", params={"termino": "MiFIR"})
        dora_status, dora_payload, dora_preview = _get_json(client, "/v1/norma/eu", params={"termino": "DORA"})
        cnmv_status, cnmv_payload, cnmv_preview = _get_json(
            client,
            "/v1/perfil/sociedad_valores/obligaciones",
            params={"dominio": "CNMV"},
        )

    list_items = list_payload if isinstance(list_payload, list) else []
    mifir_items = mifir_payload if isinstance(mifir_payload, list) else []
    dora_items = dora_payload if isinstance(dora_payload, list) else []
    cnmv_obligaciones = cnmv_payload.get("obligaciones") if isinstance(cnmv_payload, dict) else []
    cnmv_normas = {
        item.get("norma_codigo")
        for item in (cnmv_obligaciones or [])
        if isinstance(item, dict) and item.get("norma_codigo")
    }
    missing_url = [
        item.get("codigo")
        for item in list_items
        if isinstance(item, dict) and not item.get("url_eurlex")
    ]
    details.update(
        {
            "norma_eu_status": list_status,
            "norma_eu_returned": len(list_items),
            "norma_eu_missing_url": missing_url[:20],
            "mifir_status": mifir_status,
            "mifir_celex": [item.get("celex") for item in mifir_items if isinstance(item, dict)],
            "dora_status": dora_status,
            "dora_celex": [item.get("celex") for item in dora_items if isinstance(item, dict)],
            "cnmv_status": cnmv_status,
            "cnmv_normas": sorted(str(value) for value in cnmv_normas),
        }
    )
    if list_status != 200 or len(list_items) < 10 or missing_url:
        failures.append({"check": "norma_eu_endpoint", "status": list_status, "preview": list_preview})
    if mifir_status != 200 or "32014R0600" not in {item.get("celex") for item in mifir_items if isinstance(item, dict)}:
        failures.append({"check": "buscar_norma_eu_mifir", "status": mifir_status, "preview": mifir_preview})
    if dora_status != 200 or "32022R2554" not in {item.get("celex") for item in dora_items if isinstance(item, dict)}:
        failures.append({"check": "buscar_norma_eu_dora", "status": dora_status, "preview": dora_preview})
    if "32014R0600" not in cnmv_normas:
        failures.append({"check": "perfil_cnmv_mifir_obligation", "status": cnmv_status, "preview": cnmv_preview})

    try:
        with httpx.Client(base_url=base_url, timeout=60) as client:
            session_id, session_details = _mcp_session(client)
            details["eu_mcp_session"] = session_details
            if session_id:
                rpc_headers = {
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "MCP-Session-ID": session_id,
                    **_mcp_headers(),
                }
                _request_with_retry(
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
                            "clientInfo": {"name": "esdata-eu-audit", "version": "1.0"},
                        },
                    },
                )
                tools_response = _request_with_retry(
                    client,
                    "POST",
                    "/mcp",
                    headers=rpc_headers,
                    json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                )
                tools_payload = tools_response.json()
                tools = {
                    tool.get("name"): tool
                    for tool in ((tools_payload.get("result") or {}).get("tools") or [])
                    if isinstance(tool, dict)
                }
                tool = tools.get("buscar_norma_eu") or {}
                description = tool.get("description") or ""
                details["buscar_norma_eu_description_length"] = len(description)
                if len(description) <= 50:
                    failures.append({"check": "tool_description_length", "tool": "buscar_norma_eu"})
            else:
                failures.append({"check": "eu_mcp_tool_registry", "reason": "missing_session_id"})
    except Exception as exc:
        failures.append({"check": "eu_mcp_tool_registry", "error": str(exc)})

    return CheckResult(
        "eu_norm_contracts",
        not failures,
        {
            **details,
            "failures": failures,
        },
    )


def audit_semantic_suite(base_url: str) -> CheckResult:
    sys.path.insert(0, str(ROOT / "scripts" / "maintenance"))
    from mcp_validation_suite import run_read_only_suite  # type: ignore

    result = run_read_only_suite(base_url)
    failures = [check for check in result.get("checks", []) if not check.get("ok")]
    return CheckResult(
        "semantic_fail_closed_and_pagination_suite",
        bool(result.get("ok")),
        {
            "checks": len(result.get("checks", [])),
            "failures": failures,
        },
    )


def run_audit(base_url: str, database_url: str) -> dict[str, Any]:
    registry = _load_registry()
    engine = _connect(database_url)
    checks = [
        audit_tables(engine, registry),
        audit_foreign_keys(engine),
        audit_domain_availability(base_url, registry),
        audit_mcp_tools(base_url),
        audit_actions_openapi(base_url),
        audit_boe_core_legislation_contracts(base_url),
        audit_aeat_instruction_key_contracts(base_url),
        audit_teac_sepblac_contracts(base_url, engine),
        audit_profile_applicability_contracts(base_url),
        audit_eu_norm_contracts(base_url, engine),
        audit_eurlex_esma_market_contracts(base_url),
        audit_semantic_suite(base_url),
    ]
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "database_url_present": bool(database_url),
        "read_only": True,
        "checks": [
            {"name": check.name, "ok": check.ok, "details": check.details}
            for check in checks
        ],
        "ok": all(check.ok for check in checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("ESDATA_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--output", default=None, help="Optional JSON output path.")
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL is required for deep table/relationship audit")

    result = run_audit(args.base_url.rstrip("/"), args.database_url)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    print(f"ok={str(result['ok']).lower()}")
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
