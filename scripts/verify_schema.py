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
    }
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


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("SCHEMA VERIFICATION FAILED: DATABASE_URL is not set", file=sys.stderr)
        return 2

    engine = create_engine(normalize_db_url(database_url), future=True)
    try:
        issues = find_schema_issues(inspect(engine))
    finally:
        engine.dispose()

    if issues:
        print("SCHEMA VERIFICATION FAILED", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print("Schema OK: modelo_campana_operativa with provenance columns present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
