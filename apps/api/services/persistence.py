"""Shared SQL persistence helpers for lightweight services."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from db import engine
from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import Iterable


DDL_TEMPLATE = [
    """
    CREATE TABLE IF NOT EXISTS ai_audit_log (
        id {id_column},
        request_id TEXT NOT NULL DEFAULT '',
        timestamp TEXT NOT NULL,
        componente TEXT NOT NULL,
        accion TEXT NOT NULL,
        configuracion TEXT NOT NULL DEFAULT '{{}}',
        resultado_resumen TEXT NOT NULL DEFAULT '',
        latencia_ms REAL,
        error TEXT,
        user_id TEXT,
        ip_address TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ai_audit_request ON ai_audit_log(request_id)",
    "CREATE INDEX IF NOT EXISTS idx_ai_audit_component ON ai_audit_log(componente)",
    "CREATE INDEX IF NOT EXISTS idx_ai_audit_timestamp ON ai_audit_log(timestamp)",
    """
    CREATE TABLE IF NOT EXISTS data_lineage (
        id {id_column},
        entry_id TEXT NOT NULL UNIQUE,
        tabla TEXT NOT NULL,
        campo TEXT NOT NULL,
        fuente_origen TEXT NOT NULL,
        transformacion TEXT NOT NULL DEFAULT '',
        fecha_ingestion TEXT NOT NULL,
        worker_correspondiente TEXT NOT NULL DEFAULT 'unknown',
        calidad_score REAL NOT NULL DEFAULT 100,
        observaciones TEXT NOT NULL DEFAULT ''
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_data_lineage_table ON data_lineage(tabla)",
    "CREATE INDEX IF NOT EXISTS idx_data_lineage_table_field ON data_lineage(tabla, campo)",
    """
    CREATE TABLE IF NOT EXISTS human_review (
        id {id_column},
        review_id TEXT NOT NULL UNIQUE,
        request_id TEXT NOT NULL,
        decision_type TEXT NOT NULL,
        ai_response_id TEXT,
        status TEXT NOT NULL,
        reviewer_id TEXT,
        action TEXT,
        notes TEXT,
        confidence_threshold REAL NOT NULL DEFAULT 0,
        ai_confidence REAL NOT NULL DEFAULT 0,
        required_for TEXT,
        created_at TEXT NOT NULL,
        reviewed_at TEXT,
        metadata TEXT NOT NULL DEFAULT '{{}}'
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_human_review_request ON human_review(request_id)",
    "CREATE INDEX IF NOT EXISTS idx_human_review_status ON human_review(status)",
    """
    CREATE TABLE IF NOT EXISTS ai_model_registry (
        id {id_column},
        model_id TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        version TEXT NOT NULL,
        tipo TEXT NOT NULL,
        proveedor TEXT NOT NULL,
        hash_modelo TEXT NOT NULL,
        descripcion TEXT NOT NULL DEFAULT '',
        fecha_despliegue TEXT NOT NULL,
        activo INTEGER NOT NULL DEFAULT 0,
        configuracion TEXT NOT NULL DEFAULT '{{}}'
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ai_model_tipo ON ai_model_registry(tipo)",
    "CREATE INDEX IF NOT EXISTS idx_ai_model_activo ON ai_model_registry(activo)",
    """
    CREATE TABLE IF NOT EXISTS ai_config_version (
        id {id_column},
        version_id TEXT NOT NULL UNIQUE,
        hybrid_weight REAL NOT NULL,
        rrf_k REAL NOT NULL,
        limit_default INTEGER NOT NULL,
        modo_review TEXT NOT NULL,
        fecha_cambio TEXT NOT NULL,
        cambiado_por TEXT NOT NULL,
        configuracion_completa TEXT NOT NULL DEFAULT '{{}}'
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ai_config_fecha ON ai_config_version(fecha_cambio)",
    """
    CREATE TABLE IF NOT EXISTS query_audit_log (
        id {id_column},
        entry_id TEXT NOT NULL UNIQUE,
        request_id TEXT NOT NULL,
        user_id TEXT,
        path TEXT NOT NULL,
        query_text TEXT NOT NULL,
        retrieved_chunks TEXT NOT NULL DEFAULT '[]',
        response_summary TEXT NOT NULL DEFAULT '',
        model_version TEXT,
        config_version TEXT,
        created_at TEXT NOT NULL,
        grounding_status TEXT DEFAULT '',
        prompt_injection_detected INTEGER NOT NULL DEFAULT 0,
        grounding_summary TEXT NOT NULL DEFAULT '{{}}'
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_query_audit_request ON query_audit_log(request_id)",
    "CREATE INDEX IF NOT EXISTS idx_query_audit_path ON query_audit_log(path)",
    "CREATE INDEX IF NOT EXISTS idx_query_audit_created ON query_audit_log(created_at)",
    """
    CREATE TABLE IF NOT EXISTS source_freshness_snapshot (
        id {id_column},
        snapshot_id TEXT NOT NULL UNIQUE,
        source_id TEXT NOT NULL,
        snapshot_version TEXT NOT NULL,
        snapshot_at TEXT NOT NULL,
        last_success_at TEXT,
        last_status TEXT NOT NULL,
        stale INTEGER NOT NULL DEFAULT 1,
        cadencia TEXT NOT NULL,
        modo_deteccion_cambios TEXT NOT NULL,
        manifest_hash TEXT NOT NULL DEFAULT '',
        payload TEXT NOT NULL DEFAULT '{{}}'
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_source_snapshot_source ON source_freshness_snapshot(source_id, snapshot_at)",
    "CREATE INDEX IF NOT EXISTS idx_source_snapshot_version ON source_freshness_snapshot(snapshot_version)",
    """
    CREATE TABLE IF NOT EXISTS data_freshness_alerts (
        id {id_column},
        alert_id TEXT NOT NULL UNIQUE,
        source_id TEXT NOT NULL,
        alert_level TEXT NOT NULL,
        stale_since TEXT,
        expected_interval TEXT NOT NULL,
        message TEXT NOT NULL DEFAULT '',
        acknowledged INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        resolved_at TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_freshness_alerts_source ON data_freshness_alerts(source_id, stale_since DESC)",
    "CREATE INDEX IF NOT EXISTS idx_freshness_alerts_level ON data_freshness_alerts(alert_level, acknowledged)",
]

GOVERNANCE_TABLE_COLUMNS = {
    "ai_audit_log": {
        "id",
        "request_id",
        "timestamp",
        "componente",
        "accion",
        "configuracion",
        "resultado_resumen",
        "latencia_ms",
        "error",
        "user_id",
        "ip_address",
    },
    "data_lineage": {
        "id",
        "entry_id",
        "tabla",
        "campo",
        "fuente_origen",
        "transformacion",
        "fecha_ingestion",
        "worker_correspondiente",
        "calidad_score",
        "observaciones",
    },
    "human_review": {
        "id",
        "review_id",
        "request_id",
        "decision_type",
        "ai_response_id",
        "status",
        "reviewer_id",
        "action",
        "notes",
        "confidence_threshold",
        "ai_confidence",
        "required_for",
        "created_at",
        "reviewed_at",
        "metadata",
    },
    "ai_model_registry": {
        "id",
        "model_id",
        "nombre",
        "version",
        "tipo",
        "proveedor",
        "hash_modelo",
        "descripcion",
        "fecha_despliegue",
        "activo",
        "configuracion",
    },
    "ai_config_version": {
        "id",
        "version_id",
        "hybrid_weight",
        "rrf_k",
        "limit_default",
        "modo_review",
        "fecha_cambio",
        "cambiado_por",
        "configuracion_completa",
    },
    "query_audit_log": {
        "id",
        "entry_id",
        "request_id",
        "user_id",
        "path",
        "query_text",
        "retrieved_chunks",
        "response_summary",
        "model_version",
        "config_version",
        "created_at",
        "tool_name",
        "sources",
        "confidence",
        "completeness",
        "verified",
        "response_payload",
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
        "last_success_at",
        "last_status",
        "stale",
        "cadencia",
        "modo_deteccion_cambios",
        "manifest_hash",
        "payload",
    },
    "data_freshness_alerts": {
        "id",
        "alert_id",
        "source_id",
        "alert_level",
        "stale_since",
        "expected_interval",
        "message",
        "acknowledged",
        "created_at",
        "resolved_at",
    },
}


def _ddl_statements_for_dialect(dialect: str) -> list[str]:
    id_column = "INTEGER PRIMARY KEY AUTOINCREMENT" if dialect == "sqlite" else "BIGSERIAL PRIMARY KEY"
    return [statement.format(id_column=id_column) for statement in DDL_TEMPLATE]


def _ensure_query_audit_log_columns(conn) -> None:
    dialect = conn.engine.dialect.name
    if dialect == "sqlite":
        rows = conn.execute(text("PRAGMA table_info(query_audit_log)"))
        existing = {row[1] for row in rows}
    else:
        rows = conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'query_audit_log'
                """
            )
        )
        existing = {row[0] for row in rows}

    # Columns added by migration 0055 (query_audit_response_payload)
    for col, ddl in [
        ("tool_name", "ALTER TABLE query_audit_log ADD COLUMN tool_name TEXT NOT NULL DEFAULT ''"),
        ("sources", "ALTER TABLE query_audit_log ADD COLUMN sources TEXT NOT NULL DEFAULT '[]'"),
        ("confidence", "ALTER TABLE query_audit_log ADD COLUMN confidence TEXT NOT NULL DEFAULT '{}'"),
        ("completeness", "ALTER TABLE query_audit_log ADD COLUMN completeness TEXT NOT NULL DEFAULT 'parcial'"),
        ("verified", "ALTER TABLE query_audit_log ADD COLUMN verified INTEGER NOT NULL DEFAULT 0"),
        ("response_payload", "ALTER TABLE query_audit_log ADD COLUMN response_payload TEXT NOT NULL DEFAULT '{}'"),
        # Columns added by migration 0037a (grounding)
        ("grounding_status", "ALTER TABLE query_audit_log ADD COLUMN grounding_status TEXT DEFAULT ''"),
        ("prompt_injection_detected", "ALTER TABLE query_audit_log ADD COLUMN prompt_injection_detected INTEGER NOT NULL DEFAULT 0"),
        ("grounding_summary", "ALTER TABLE query_audit_log ADD COLUMN grounding_summary TEXT NOT NULL DEFAULT '{}'"),
    ]:
        if col not in existing:
            try:
                conn.execute(text(ddl))
            except Exception:
                pass  # column may already exist from Alembic migration


def _value(row, key: str, index: int):
    if hasattr(row, "_mapping"):
        return row._mapping[key]
    return row[index]


def _verify_postgres_governance_schema(conn) -> None:
    table_literals = ", ".join(f"'{name}'" for name in sorted(GOVERNANCE_TABLE_COLUMNS))
    rows = conn.execute(
        text(
            f"""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN ({table_literals})
            """
        )
    )
    existing: dict[str, set[str]] = {}
    for row in rows:
        existing.setdefault(_value(row, "table_name", 0), set()).add(_value(row, "column_name", 1))

    errors: list[str] = []
    for table_name, required_columns in sorted(GOVERNANCE_TABLE_COLUMNS.items()):
        if table_name not in existing:
            errors.append(f"missing table: {table_name}")
            continue
        for column_name in sorted(required_columns - existing[table_name]):
            errors.append(f"missing column: {table_name}.{column_name}")

    if errors:
        raise RuntimeError(
            "Governance schema is incomplete; run Alembic migrations before starting the API: "
            + "; ".join(errors)
        )


def ensure_governance_tables() -> None:
    with engine.begin() as conn:
        if conn.engine.dialect.name == "postgresql":
            _verify_postgres_governance_schema(conn)
            return
        for statement in _ddl_statements_for_dialect(conn.engine.dialect.name):
            conn.execute(text(statement))
        _ensure_query_audit_log_columns(conn)


def dumps_json(value) -> str:
    return json.dumps(value or {}, ensure_ascii=True, sort_keys=True, default=_json_default)


def dumps_json_list(value) -> str:
    return json.dumps(value or [], ensure_ascii=True, sort_keys=True, default=_json_default)


def _json_default(obj):
    from datetime import date, datetime
    from decimal import Decimal

    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')


def loads_json(value, default):
    """Parse JSON string, or pass through if already parsed.

    Postgres `json`/`jsonb` columns are returned by psycopg as native Python
    lists/dicts; Postgres `text` columns come as strings. This helper handles
    both uniformly so callers can mix storage types without TypeError.
    """
    if value is None or value == "":
        return default
    if isinstance(value, (list, dict)):
        return value
    return json.loads(value)


def rows_to_dicts(rows: Iterable) -> list[dict]:
    return [dict(row._mapping) for row in rows]
