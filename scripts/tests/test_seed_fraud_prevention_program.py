#!/usr/bin/env python3
"""Test fraud_prevention_program seed — Programas de prevencion de fraude.

Uso:
    pytest scripts/tests/test_seed_fraud_prevention_program.py -v
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_fraud_prevention_program.py"
EXPECTED_COUNT = 5


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestFraudPreventionProgramStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'fraud_prevention_program')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'fraud_prevention_program' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "entity_id", "code_of_conduct",
            "internal_reporting_system", "training_schedule",
            "audit_frequency", "compliance_officer_name",
            "status", "created_at",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM fraud_prevention_program")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestFraudPreventionProgramIntegrity:
    def test_code_of_conduct_boolean(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT code_of_conduct FROM fraud_prevention_program")
        values = [r[0] for r in cur.fetchall()]
        assert all(v in (True, False) for v in values)

    def test_internal_reporting_boolean(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT internal_reporting_system FROM fraud_prevention_program")
        values = [r[0] for r in cur.fetchall()]
        assert all(v in (True, False) for v in values)

    def test_status_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT status FROM fraud_prevention_program")
        values = [r[0] for r in cur.fetchall()]
        assert all(v in ("active", "pending", "inactive") for v in values)

    def test_entity_id_references(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM fraud_prevention_program f "
            "LEFT JOIN empresa e ON f.entity_id = e.id "
            "WHERE e.id IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_active_programs_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM fraud_prevention_program WHERE status = 'active'")
        assert cur.fetchone()[0] > 0

    def test_pending_programs_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM fraud_prevention_program WHERE status = 'pending'")
        assert cur.fetchone()[0] > 0
