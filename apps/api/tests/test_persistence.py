import sys
from pathlib import Path


API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def test_governance_ddl_uses_postgres_primary_key_for_postgresql():
    from services import persistence

    statements = persistence._ddl_statements_for_dialect("postgresql")

    assert any("BIGSERIAL PRIMARY KEY" in statement for statement in statements)
    assert all("AUTOINCREMENT" not in statement for statement in statements)


def test_governance_ddl_keeps_sqlite_autoincrement_for_sqlite():
    from services import persistence

    statements = persistence._ddl_statements_for_dialect("sqlite")

    assert any("AUTOINCREMENT" in statement for statement in statements)
