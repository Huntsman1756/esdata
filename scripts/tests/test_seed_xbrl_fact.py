#!/usr/bin/env python3
"""Test xbrl_fact seed — Hechos XBRL extraidos de depositos.

Uso:
    pytest scripts/tests/test_seed_xbrl_fact.py -v
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_xbrl_fact.py"
EXPECTED_COUNT = 12


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestXbrlFactStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'xbrl_fact')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'xbrl_fact' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "filing_id", "concept", "value_raw", "value_numeric",
            "unit", "context_ref", "period_start", "period_end",
            "entity_identifier", "decimals", "created_at",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM xbrl_fact")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestXbrlFactIntegrity:
    def test_all_concepts_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM xbrl_fact WHERE concept IS NULL")
        assert cur.fetchone()[0] == 0

    def test_all_values_raw_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM xbrl_fact WHERE value_raw IS NULL")
        assert cur.fetchone()[0] == 0

    def test_all_entity_identifiers_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM xbrl_fact WHERE entity_identifier IS NULL")
        assert cur.fetchone()[0] == 0

    def test_filing_id_references(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM xbrl_fact f "
            "LEFT JOIN xbrl_filing x ON f.filing_id = x.id "
            "WHERE x.id IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_concepts_have_namespace(self, db):
        cur = db.cursor()
        cur.execute("SELECT concept FROM xbrl_fact")
        for row in cur.fetchall():
            assert ":" in row[0], f"Concept missing namespace: {row[0]}"

    def test_value_numeric_numeric(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'xbrl_fact' AND column_name = 'value_numeric'"
        )
        assert cur.fetchone()[0] == "numeric"

    def test_spanish_filings_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM xbrl_fact "
            "WHERE entity_identifier LIKE 'ES%'"
        )
        assert cur.fetchone()[0] > 0

    def test_us_filings_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM xbrl_fact "
            "WHERE entity_identifier NOT LIKE 'ES%'"
        )
        assert cur.fetchone()[0] > 0
