#!/usr/bin/env python3
"""Test dac_reporting_entity seed — Entidades de declaracion DAC8/DAC9.

Uso:
    pytest scripts/tests/test_seed_dac_reporting_entity.py -v
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_dac_reporting_entity.py"
EXPECTED_COUNT = 10


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestDacReportingEntityStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'dac_reporting_entity')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'dac_reporting_entity' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "tin", "entity_type", "member_state",
            "dac8_registered", "dac9_registered", "status", "created_at",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM dac_reporting_entity")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestDacReportingEntityIntegrity:
    def test_no_null_tin(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM dac_reporting_entity WHERE tin IS NULL")
        assert cur.fetchone()[0] == 0

    def test_all_tins_unique(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT tin, count(*) FROM dac_reporting_entity "
            "GROUP BY tin HAVING count(*) > 1"
        )
        assert cur.fetchone() is None

    def test_member_state_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT member_state FROM dac_reporting_entity")
        values = [r[0] for r in cur.fetchall()]
        assert all(len(v) == 2 for v in values)

    def test_entity_type_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT entity_type FROM dac_reporting_entity")
        values = [r[0] for r in cur.fetchall()]
        valid_types = {
            "reporting_fi", "custodian_broker", "payment_platform",
            "investment_fund", "foreign_platform",
        }
        assert all(v in valid_types for v in values)

    def test_status_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT status FROM dac_reporting_entity")
        values = [r[0] for r in cur.fetchall()]
        assert all(v in ("active", "pending", "inactive") for v in values)

    def test_dac8_registered_boolean(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT dac8_registered FROM dac_reporting_entity")
        values = [r[0] for r in cur.fetchall()]
        assert all(v in (True, False) for v in values)

    def test_dac9_registered_boolean(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT dac9_registered FROM dac_reporting_entity")
        values = [r[0] for r in cur.fetchall()]
        assert all(v in (True, False) for v in values)

    def test_spain_entities_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM dac_reporting_entity WHERE member_state = 'ES'"
        )
        assert cur.fetchone()[0] > 0

    def test_foreign_entities_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM dac_reporting_entity WHERE member_state != 'ES'"
        )
        assert cur.fetchone()[0] > 0
