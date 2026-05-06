import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
API_DIR = ROOT / "apps/api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

MISSING_TABLES_MESSAGE = "run Alembic migrations instead of creating API runtime tables"


def _assert_no_runtime_ddl(statements):
    assert not any("CREATE TABLE" in statement for statement in statements)
    assert not any("ALTER TABLE" in statement for statement in statements)


class FakeColumnResult:
    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeDialect:
    name = "postgresql"


class FakeConnection:
    def __init__(self, *, columns_by_table=None, rls_missing=False):
        self.engine = type("FakeConnectionEngine", (), {"dialect": FakeDialect()})()
        self.statements = []
        self.columns_by_table = columns_by_table or {}
        self.rls_missing = rls_missing

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append(sql)
        if "information_schema.columns" in sql:
            rows = [
                (table_name, column)
                for table_name, columns in self.columns_by_table.items()
                for column in columns
            ]
            return FakeColumnResult(rows)
        if "relrowsecurity" in sql:
            return FakeColumnResult([("source_freshness_snapshot",)] if self.rls_missing else [])
        return FakeColumnResult([])


class FakeBegin:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeEngine:
    def __init__(self, conn):
        self.conn = conn

    def begin(self):
        return FakeBegin(self.conn)


def test_api_persistence_does_not_run_postgres_create_table_runtime():
    source = (ROOT / "apps/api/services/persistence.py").read_text(encoding="utf-8")

    assert "source_freshness_snapshot" in source
    assert "information_schema.columns" in source
    assert MISSING_TABLES_MESSAGE in source
    assert "CREATE TABLE" not in source


def test_webhook_idempotency_does_not_create_runtime_table():
    source = (ROOT / "apps/api/services/webhook_verification.py").read_text(encoding="utf-8")

    assert "CREATE TABLE" not in source
    assert "run Alembic migrations before webhook processing" in source


def test_forbidden_runtime_create_table_patterns_are_limited_to_sqlite_bootstrap():
    forbidden = "CREATE TABLE IF" + " NOT EXISTS"
    allowed_files = {
        ROOT / "apps/api/services/persistence.py",
        ROOT / "apps/api/tests/conftest.py",
        ROOT / "apps/api/tests/test_alembic_integrity.py",
    }
    offenders = []

    for path in (ROOT / "apps/api").rglob("*.py"):
        if path in allowed_files:
            continue
        text = path.read_text(encoding="utf-8")
        if forbidden in text:
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def test_deprecated_deploy_workflow_has_no_active_railway_deploy_or_main_push():
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")

    assert "railway up" not in workflow
    assert "branches: [main]" not in workflow


def test_api_persistence_postgres_missing_governance_table_raises_without_runtime_ddl(monkeypatch):
    from services import persistence

    columns_by_table = {
        table_name: columns
        for table_name, columns in persistence.REQUIRED_GOVERNANCE_COLUMNS.items()
        if table_name != "source_freshness_snapshot"
    }
    fake_engine = FakeEngine(FakeConnection(columns_by_table=columns_by_table))
    monkeypatch.setattr(persistence, "engine", fake_engine)

    with pytest.raises(RuntimeError, match=MISSING_TABLES_MESSAGE):
        persistence.ensure_governance_tables()

    _assert_no_runtime_ddl(fake_engine.conn.statements)


def test_api_persistence_postgres_missing_columns_raise_without_runtime_ddl(monkeypatch):
    from services import persistence

    columns_by_table = {
        table_name: set(columns)
        for table_name, columns in persistence.REQUIRED_GOVERNANCE_COLUMNS.items()
    }
    columns_by_table["source_freshness_snapshot"].remove("payload")
    fake_engine = FakeEngine(FakeConnection(columns_by_table=columns_by_table))
    monkeypatch.setattr(persistence, "engine", fake_engine)

    with pytest.raises(RuntimeError, match=MISSING_TABLES_MESSAGE):
        persistence.ensure_governance_tables()

    _assert_no_runtime_ddl(fake_engine.conn.statements)


def test_api_persistence_postgres_missing_rls_raises_without_runtime_ddl(monkeypatch):
    from services import persistence

    fake_engine = FakeEngine(
        FakeConnection(
            columns_by_table=persistence.REQUIRED_GOVERNANCE_COLUMNS,
            rls_missing=True,
        )
    )
    monkeypatch.setattr(persistence, "engine", fake_engine)

    with pytest.raises(RuntimeError, match=MISSING_TABLES_MESSAGE):
        persistence.ensure_governance_tables()

    _assert_no_runtime_ddl(fake_engine.conn.statements)


def test_latest_p0_rls_migration_absorbs_drift_and_applies_rls_policies():
    migration = ROOT / "alembic/versions/20260506_0001_p0_rls_current_tables.py"

    assert migration.exists()
    text = migration.read_text(encoding="utf-8")
    drift_safe_create = "CREATE TABLE IF" + " NOT EXISTS"
    assert "modelo_recurso" in text
    assert "source_freshness_snapshot" in text
    assert f"{drift_safe_create} webhook_events" in text
    assert f"{drift_safe_create} source_freshness_snapshot" in text
    assert "CREATE INDEX IF NOT EXISTS idx_source_snapshot_source" in text
    assert "CREATE INDEX IF NOT EXISTS idx_source_snapshot_version" in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "service_role_all" in text
    assert "esdata_all" in text
    assert "roles && ARRAY['public', 'anon', 'authenticated']::name[]" in text
