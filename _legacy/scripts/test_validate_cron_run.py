import importlib.util
from pathlib import Path


def _load_module():
    module_path = Path(__file__).with_name("validate-cron-run.py")
    spec = importlib.util.spec_from_file_location("validate_cron_run", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_normalize_db_url_strips_sqlalchemy_driver_suffix():
    module = _load_module()

    url = "postgresql+psycopg://user:pass@host:5432/dbname"

    assert module.normalize_db_url(url) == "postgresql://user:pass@host:5432/dbname"


def test_get_db_url_normalizes_explicit_argument():
    module = _load_module()

    url = "postgresql+psycopg://user:pass@host:5432/dbname"

    assert module.get_db_url(url) == "postgresql://user:pass@host:5432/dbname"


def test_recent_documents_query_counts_rows_without_join_table_id():
    module = _load_module()

    assert (
        "COUNT(*) FILTER (WHERE da.documento_id IS NOT NULL) AS links"
        in module.RECENT_DOCUMENTS
    )
    assert "COUNT(da.id)" not in module.RECENT_DOCUMENTS
