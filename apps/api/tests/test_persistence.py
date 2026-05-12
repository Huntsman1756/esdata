import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def test_ensure_governance_tables_verifies_postgres_without_runtime_ddl(monkeypatch):
    from services import persistence

    statements = []

    class FakeDialect:
        name = "postgresql"

    class FakeConn:
        engine = type("EngineRef", (), {"dialect": FakeDialect()})()

        def execute(self, statement):
            sql = str(statement)
            statements.append(sql)
            assert "information_schema.columns" in sql
            return [
                (table_name, column_name)
                for table_name, columns in persistence.GOVERNANCE_TABLE_COLUMNS.items()
                for column_name in columns
            ]

    class FakeBegin:
        def __enter__(self):
            return FakeConn()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

    monkeypatch.setattr(persistence, "engine", FakeEngine())

    persistence.ensure_governance_tables()

    assert len(statements) == 1
    assert "CREATE TABLE" not in statements[0]
    assert "ALTER TABLE" not in statements[0]


def test_governance_ddl_keeps_sqlite_autoincrement_for_sqlite():
    from services import persistence

    statements = persistence._ddl_statements_for_dialect("sqlite")

    assert any("AUTOINCREMENT" in statement for statement in statements)
