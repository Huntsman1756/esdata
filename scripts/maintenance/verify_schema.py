#!/usr/bin/env python3
"""Verify required database schema state for deploy gating."""

from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, inspect

REQUIRED_SCHEMA = {
    "modelo_campana_operativa": {
        "campana_id",
        "categoria_obligado",
        "frecuencia_presentacion",
        "ventana_presentacion",
        "canal_presentacion",
        "obligados_resumen",
        "plazo_resumen",
        "presentacion_resumen",
        "norma_base",
        "nota",
        "actualizado_at",
        "origen_metadato",
        "estado_metadato",
        "completeness_estado",
    },
    "query_audit_log": {
        "entry_id",
        "request_id",
        "path",
        "query_text",
        "retrieved_chunks",
        "response_summary",
        "tool_name",
        "sources",
        "confidence",
        "completeness",
        "verified",
        "grounding_status",
        "prompt_injection_detected",
        "grounding_summary",
        "response_payload",
        "created_at",
    },
    "dgt_queue": {
        "worker_name",
        "source_entity_id",
        "dgt_url",
        "status",
        "queued_at",
        "processed_at",
    },
    "documento_interpretativo": {
        "row_completeness",
        "row_provenance",
    },
}


def normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + db_url.removeprefix("postgresql://")
    return db_url


def find_schema_issues(db_inspector) -> list[str]:
    issues: list[str] = []
    tables = set(db_inspector.get_table_names())

    for table_name, required_columns in REQUIRED_SCHEMA.items():
        if table_name not in tables:
            issues.append(f"missing table: {table_name}")
            continue

        existing_columns = {
            column["name"] for column in db_inspector.get_columns(table_name)
        }
        missing_columns = sorted(required_columns - existing_columns)
        issues.extend(
            f"missing column: {table_name}.{column_name}"
            for column_name in missing_columns
        )

    return issues


def find_dgt_queue_uniqueness_issues(db_inspector) -> list[str]:
    tables = set(db_inspector.get_table_names())
    if "dgt_queue" not in tables:
        return []

    expected = {"worker_name", "source_entity_id"}
    for index in db_inspector.get_indexes("dgt_queue"):
        if index.get("unique") and set(index.get("column_names") or []) == expected:
            return []

    get_unique_constraints = getattr(db_inspector, "get_unique_constraints", None)
    if callable(get_unique_constraints):
        for constraint in get_unique_constraints("dgt_queue"):
            if set(constraint.get("column_names") or []) == expected:
                return []

    return ["missing unique key: dgt_queue(worker_name, source_entity_id)"]


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("SCHEMA VERIFICATION FAILED: DATABASE_URL is not set", file=sys.stderr)
        return 2

    engine = create_engine(normalize_db_url(database_url), future=True)
    try:
        db_inspector = inspect(engine)
        issues = find_schema_issues(db_inspector)
        issues.extend(find_dgt_queue_uniqueness_issues(db_inspector))
    finally:
        engine.dispose()

    if issues:
        print("SCHEMA VERIFICATION FAILED", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print(
        "Schema OK: modelo_campana_operativa, query_audit_log, dgt_queue, "
        "documento_interpretativo runtime columns present and dgt_queue "
        "uniqueness enforced"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
