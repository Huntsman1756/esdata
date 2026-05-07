from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

MODULE_PATH = Path(__file__).resolve().parents[1] / "maintenance" / "verify_schema.py"
QUERY_AUDIT_REQUIRED_COLUMNS = {
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
}
DGT_QUEUE_REQUIRED_COLUMNS = {
    "worker_name",
    "source_entity_id",
    "dgt_url",
    "status",
    "queued_at",
    "processed_at",
}
DOCUMENTO_INTERPRETATIVO_REQUIRED_COLUMNS = {
    "row_completeness",
    "row_provenance",
}


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_schema", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_runtime_schema(engine) -> None:
    ddl = [
        """
        CREATE TABLE modelo_campana_operativa (
            campana_id INTEGER PRIMARY KEY,
            categoria_obligado TEXT,
            frecuencia_presentacion TEXT,
            ventana_presentacion TEXT,
            canal_presentacion TEXT,
            obligados_resumen TEXT,
            plazo_resumen TEXT,
            presentacion_resumen TEXT,
            norma_base TEXT,
            nota TEXT,
            actualizado_at TEXT,
            origen_metadato TEXT,
            estado_metadato TEXT
        )
        """,
        """
        CREATE TABLE query_audit_log (
            id INTEGER PRIMARY KEY,
            entry_id TEXT,
            request_id TEXT,
            path TEXT,
            query_text TEXT,
            retrieved_chunks TEXT,
            response_summary TEXT,
            tool_name TEXT,
            sources TEXT,
            confidence TEXT,
            completeness TEXT,
            verified INTEGER,
            grounding_status TEXT,
            prompt_injection_detected INTEGER,
            grounding_summary TEXT,
            response_payload TEXT,
            created_at TEXT
        )
        """,
        """
        CREATE TABLE dgt_queue (
            id INTEGER PRIMARY KEY,
            worker_name TEXT,
            source_entity_id TEXT,
            dgt_url TEXT,
            status TEXT,
            queued_at TEXT,
            processed_at TEXT
        )
        """,
        "CREATE UNIQUE INDEX uq_dgt_queue_worker_source ON dgt_queue(worker_name, source_entity_id)",
        """
        CREATE TABLE documento_interpretativo (
            id INTEGER PRIMARY KEY,
            row_completeness TEXT,
            row_provenance TEXT
        )
        """,
    ]
    with engine.begin() as conn:
        for statement in ddl:
            conn.execute(text(statement))


def test_normalize_db_url_adds_psycopg_driver_for_plain_postgresql_scheme():
    module = _load_module()

    url = "postgresql://user:pass@host:5432/dbname"

    assert module.normalize_db_url(url) == "postgresql+psycopg://user:pass@host:5432/dbname"


def test_normalize_db_url_keeps_existing_psycopg_driver_scheme():
    module = _load_module()

    url = "postgresql+psycopg://user:pass@host:5432/dbname"

    assert module.normalize_db_url(url) == url


def test_find_schema_issues_returns_empty_for_expanded_runtime_contract():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)

    inspector = inspect(engine)
    issues = module.find_schema_issues(inspector)
    issues.extend(module.find_dgt_queue_uniqueness_issues(inspector))

    assert issues == []


def test_find_schema_issues_reports_missing_modelo_campana_operativa_columns():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE modelo_campana_operativa"))
        conn.execute(
            text(
                """
                CREATE TABLE modelo_campana_operativa (
                    campana_id INTEGER PRIMARY KEY,
                    categoria_obligado TEXT,
                    frecuencia_presentacion TEXT,
                    ventana_presentacion TEXT,
                    canal_presentacion TEXT,
                    obligados_resumen TEXT,
                    plazo_resumen TEXT,
                    presentacion_resumen TEXT,
                    norma_base TEXT,
                    nota TEXT,
                    actualizado_at TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert set(issues) == {
        "missing column: modelo_campana_operativa.estado_metadato",
        "missing column: modelo_campana_operativa.origen_metadato",
    }


def test_find_schema_issues_reports_missing_query_audit_log_response_payload():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE query_audit_log"))
        conn.execute(
            text(
                """
                CREATE TABLE query_audit_log (
                    id INTEGER PRIMARY KEY,
                    entry_id TEXT,
                    request_id TEXT,
                    path TEXT,
                    query_text TEXT,
                    retrieved_chunks TEXT,
                    response_summary TEXT,
                    tool_name TEXT,
                    sources TEXT,
                    confidence TEXT,
                    completeness TEXT,
                    verified INTEGER,
                    grounding_status TEXT,
                    prompt_injection_detected INTEGER,
                    grounding_summary TEXT,
                    created_at TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert issues == ["missing column: query_audit_log.response_payload"]


def test_find_schema_issues_reports_missing_query_audit_log_entry_id():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE query_audit_log"))
        conn.execute(
            text(
                """
                CREATE TABLE query_audit_log (
                    id INTEGER PRIMARY KEY,
                    request_id TEXT,
                    path TEXT,
                    query_text TEXT,
                    retrieved_chunks TEXT,
                    response_summary TEXT,
                    tool_name TEXT,
                    sources TEXT,
                    confidence TEXT,
                    completeness TEXT,
                    verified INTEGER,
                    grounding_status TEXT,
                    prompt_injection_detected INTEGER,
                    grounding_summary TEXT,
                    response_payload TEXT,
                    created_at TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert issues == ["missing column: query_audit_log.entry_id"]


def test_find_schema_issues_reports_missing_query_audit_log_created_at():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE query_audit_log"))
        conn.execute(
            text(
                """
                CREATE TABLE query_audit_log (
                    id INTEGER PRIMARY KEY,
                    entry_id TEXT,
                    request_id TEXT,
                    path TEXT,
                    query_text TEXT,
                    retrieved_chunks TEXT,
                    response_summary TEXT,
                    tool_name TEXT,
                    sources TEXT,
                    confidence TEXT,
                    completeness TEXT,
                    verified INTEGER,
                    grounding_status TEXT,
                    prompt_injection_detected INTEGER,
                    grounding_summary TEXT,
                    response_payload TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert issues == ["missing column: query_audit_log.created_at"]


def test_find_schema_issues_reports_full_missing_query_audit_runtime_columns():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE query_audit_log"))
        conn.execute(
            text(
                """
                CREATE TABLE query_audit_log (
                    id INTEGER PRIMARY KEY,
                    request_id TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert set(issues) == {
        f"missing column: query_audit_log.{column_name}"
        for column_name in sorted(QUERY_AUDIT_REQUIRED_COLUMNS - {"request_id"})
    }


def test_find_schema_issues_reports_missing_dgt_queue_status():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE dgt_queue"))
        conn.execute(
            text(
                """
                CREATE TABLE dgt_queue (
                    id INTEGER PRIMARY KEY,
                    worker_name TEXT,
                    source_entity_id TEXT,
                    dgt_url TEXT,
                    queued_at TEXT,
                    processed_at TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert issues == ["missing column: dgt_queue.status"]


def test_find_dgt_queue_uniqueness_issues_reports_missing_unique_key():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP INDEX uq_dgt_queue_worker_source"))

    issues = module.find_dgt_queue_uniqueness_issues(inspect(engine))

    assert issues == [
        "missing unique key: dgt_queue(worker_name, source_entity_id)"
    ]


def test_find_dgt_queue_uniqueness_issues_accepts_table_level_unique_constraint():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE dgt_queue (
                    id INTEGER PRIMARY KEY,
                    worker_name TEXT,
                    source_entity_id TEXT,
                    dgt_url TEXT,
                    status TEXT,
                    queued_at TEXT,
                    processed_at TEXT,
                    UNIQUE(worker_name, source_entity_id)
                )
                """
            )
        )

    issues = module.find_dgt_queue_uniqueness_issues(inspect(engine))

    assert issues == []


def test_find_schema_issues_reports_full_missing_dgt_queue_runtime_columns():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE dgt_queue"))
        conn.execute(
            text(
                """
                CREATE TABLE dgt_queue (
                    id INTEGER PRIMARY KEY,
                    worker_name TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert set(issues) == {
        f"missing column: dgt_queue.{column_name}"
        for column_name in sorted(DGT_QUEUE_REQUIRED_COLUMNS - {"worker_name"})
    }


def test_find_schema_issues_reports_missing_documento_interpretativo_row_provenance():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE documento_interpretativo"))
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY,
                    row_completeness TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert issues == ["missing column: documento_interpretativo.row_provenance"]


def test_find_schema_issues_reports_full_missing_documento_interpretativo_runtime_columns():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE documento_interpretativo"))
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert set(issues) == {
        f"missing column: documento_interpretativo.{column_name}"
        for column_name in sorted(DOCUMENTO_INTERPRETATIVO_REQUIRED_COLUMNS)
    }


def test_find_schema_issues_reports_missing_runtime_tables():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE modelo_campana_operativa (
                    campana_id INTEGER PRIMARY KEY,
                    categoria_obligado TEXT,
                    frecuencia_presentacion TEXT,
                    ventana_presentacion TEXT,
                    canal_presentacion TEXT,
                    obligados_resumen TEXT,
                    plazo_resumen TEXT,
                    presentacion_resumen TEXT,
                    norma_base TEXT,
                    nota TEXT,
                    actualizado_at TEXT,
                    origen_metadato TEXT,
                    estado_metadato TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert set(issues) == {
        "missing table: query_audit_log",
        "missing table: dgt_queue",
        "missing table: documento_interpretativo",
    }
