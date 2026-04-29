#!/usr/bin/env python3
"""Test fraud_incident seed — Incidentes de fraude para compliance PBC.

Uso:
    pytest scripts/tests/test_seed_fraud_incident.py -v
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_fraud_incident.py"
EXPECTED_COUNT = 10


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestFraudIncidentStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'fraud_incident')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'fraud_incident' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "entity_id", "incident_date", "description",
            "amount_eur", "status", "resolution_date",
            "regulatory_notification", "created_at",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM fraud_incident")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestFraudIncidentIntegrity:
    def test_all_descriptions_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM fraud_incident WHERE description IS NULL")
        assert cur.fetchone()[0] == 0

    def test_amount_non_negative(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM fraud_incident "
            "WHERE amount_eur IS NOT NULL AND amount_eur < 0"
        )
        assert cur.fetchone()[0] == 0

    def test_status_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT status FROM fraud_incident")
        values = [r[0] for r in cur.fetchall()]
        valid_statuses = {"open", "under_investigation", "resolved", "closed"}
        assert all(v in valid_statuses for v in values)

    def test_regulatory_notification_boolean(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT regulatory_notification FROM fraud_incident")
        values = [r[0] for r in cur.fetchall()]
        assert all(v in (True, False) for v in values)

    def test_resolution_date_logic(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM fraud_incident "
            "WHERE status IN ('resolved', 'closed') AND resolution_date IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_entity_id_references(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM fraud_incident f "
            "LEFT JOIN empresa e ON f.entity_id = e.id "
            "WHERE e.id IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_various_statuses_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT status FROM fraud_incident")
        values = [r[0] for r in cur.fetchall()]
        assert len(values) >= 3
