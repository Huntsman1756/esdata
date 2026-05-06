"""Shared SQL persistence helpers for lightweight services."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from db import engine
from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import Iterable


MISSING_GOVERNANCE_TABLES_MESSAGE = (
    "Governance tables are missing; run Alembic migrations instead of creating API runtime tables."
)
REQUIRED_GOVERNANCE_COLUMNS = {
    "ai_audit_log": {"id", "request_id", "timestamp", "componente", "accion", "configuracion"},
    "data_lineage": {"id", "entry_id", "tabla", "campo", "fuente_origen", "fecha_ingestion"},
    "human_review": {"id", "review_id", "request_id", "decision_type", "status", "created_at"},
    "ai_model_registry": {"id", "model_id", "nombre", "version", "tipo", "proveedor"},
    "ai_config_version": {"id", "version_id", "hybrid_weight", "rrf_k", "limit_default", "modo_review"},
    "query_audit_log": {
        "id",
        "entry_id",
        "request_id",
        "path",
        "query_text",
        "retrieved_chunks",
        "grounding_status",
        "prompt_injection_detected",
        "grounding_summary",
    },
    "source_freshness_snapshot": {
        "id",
        "snapshot_id",
        "source_id",
        "snapshot_version",
        "snapshot_at",
        "last_status",
        "stale",
        "cadencia",
        "modo_deteccion_cambios",
        "manifest_hash",
        "payload",
    },
}
GOVERNANCE_TABLES = set(REQUIRED_GOVERNANCE_COLUMNS)


def _ensure_query_audit_log_columns(conn) -> None:
    rows = conn.execute(text("PRAGMA table_info(query_audit_log)"))
    existing = {row[1] for row in rows}

    missing = []
    if "grounding_status" not in existing:
        missing.append("ALTER TABLE query_audit_log ADD COLUMN grounding_status TEXT DEFAULT ''")
    if "prompt_injection_detected" not in existing:
        missing.append("ALTER TABLE query_audit_log ADD COLUMN prompt_injection_detected INTEGER NOT NULL DEFAULT 0")
    if "grounding_summary" not in existing:
        missing.append("ALTER TABLE query_audit_log ADD COLUMN grounding_summary TEXT NOT NULL DEFAULT '{}' ")

    for statement in missing:
        conn.execute(text(statement))


def _sqlite_governance_tables_exist(conn) -> bool:
    rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))
    existing = {row[0] for row in rows}
    return GOVERNANCE_TABLES.issubset(existing)


def _validate_postgres_governance_schema(conn) -> None:
    rows = conn.execute(
        text(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ANY(:table_names)
            """
        ),
        {"table_names": sorted(GOVERNANCE_TABLES)},
    )
    existing: dict[str, set[str]] = {table_name: set() for table_name in GOVERNANCE_TABLES}
    for table_name, column_name in rows:
        existing.setdefault(table_name, set()).add(column_name)

    for table_name, required_columns in REQUIRED_GOVERNANCE_COLUMNS.items():
        if not required_columns.issubset(existing.get(table_name, set())):
            raise RuntimeError(MISSING_GOVERNANCE_TABLES_MESSAGE)


def _validate_postgres_governance_rls(conn) -> None:
    missing_rls = conn.execute(
        text(
            """
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relname = ANY(:table_names)
              AND c.relkind = 'r'
              AND NOT c.relrowsecurity
            LIMIT 1
            """
        ),
        {"table_names": sorted(GOVERNANCE_TABLES)},
    ).fetchone()
    if missing_rls:
        raise RuntimeError(MISSING_GOVERNANCE_TABLES_MESSAGE)


def ensure_governance_tables() -> None:
    with engine.begin() as conn:
        dialect = conn.engine.dialect.name
        if dialect == "sqlite":
            if not _sqlite_governance_tables_exist(conn):
                if os.environ.get("APP_ENV", "").lower() == "test":
                    raise RuntimeError(
                        "SQLite governance tables are missing; call "
                        "tests.governance_bootstrap.bootstrap_governance_tables."
                    )
                raise RuntimeError(MISSING_GOVERNANCE_TABLES_MESSAGE)
            _ensure_query_audit_log_columns(conn)
            return

        _validate_postgres_governance_schema(conn)
        _validate_postgres_governance_rls(conn)


def dumps_json(value) -> str:
    return json.dumps(value or {}, ensure_ascii=True, sort_keys=True)


def dumps_json_list(value) -> str:
    return json.dumps(value or [], ensure_ascii=True, sort_keys=True)


def loads_json(value: str | None, default):
    if not value:
        return default
    return json.loads(value)


def rows_to_dicts(rows: Iterable) -> list[dict]:
    return [dict(row._mapping) for row in rows]
