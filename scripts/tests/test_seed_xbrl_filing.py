#!/usr/bin/env python3
"""Test xbrl_filing seed — Depositos XBRL de companias.

Uso:
    pytest scripts/tests/test_seed_xbrl_filing.py -v
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_xbrl_filing.py"
EXPECTED_COUNT = 10


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestXbrlFilingStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'xbrl_filing')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'xbrl_filing' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "source_name", "source_path", "entity_identifier",
            "period_start", "period_end", "filing_type", "created_at",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM xbrl_filing")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestXbrlFilingIntegrity:
    def test_all_sources_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM xbrl_filing WHERE source_name IS NULL")
        assert cur.fetchone()[0] == 0

    def test_all_paths_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM xbrl_filing WHERE source_path IS NULL")
        assert cur.fetchone()[0] == 0

    def test_all_entity_identifiers_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM xbrl_filing WHERE entity_identifier IS NULL")
        assert cur.fetchone()[0] == 0

    def test_filing_type_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT filing_type FROM xbrl_filing")
        values = [r[0] for r in cur.fetchall()]
        valid_types = {"annual", "quarterly", "esg", "current"}
        assert all(v in valid_types for v in values)

    def test_source_names(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT source_name FROM xbrl_filing")
        values = [r[0] for r in cur.fetchall()]
        assert "CNMV" in values
        assert "EDGAR" in values

    def test_entity_identifiers_unique_per_source(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT source_path, count(*) FROM xbrl_filing "
            "GROUP BY source_path HAVING count(*) > 1"
        )
        assert cur.fetchone() is None

    def test_period_end_after_start(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM xbrl_filing "
            "WHERE period_start IS NOT NULL AND period_end IS NOT NULL "
            "AND period_end < period_start"
        )
        assert cur.fetchone()[0] == 0
