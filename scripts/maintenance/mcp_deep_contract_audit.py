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

ROOT = Path(__file__).resolve().parents[2]
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
    handshake = _request_with_retry(
        client,
        "GET",
        "/mcp",
        headers={"Accept": "text/event-stream", **_mcp_headers()},
    )
    session_id = handshake.headers.get("mcp-session-id") or handshake.headers.get("Mcp-Session-Id")
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
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
