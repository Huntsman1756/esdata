import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


def _load_module():
    module_path = Path(__file__).with_name("verify_schema.py")
    spec = importlib.util.spec_from_file_location("verify_schema", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_find_schema_issues_returns_empty_when_required_table_and_columns_exist():
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

    assert issues == []


def test_find_schema_issues_reports_missing_columns():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE modelo_campana_operativa (
                    campana_id INTEGER PRIMARY KEY,
                    categoria_obligado TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert any("origen_metadato" in issue for issue in issues)
    assert any("estado_metadato" in issue for issue in issues)
