#!/usr/bin/env python3
"""Test fraud_risk_assessment seed — Evaluaciones de riesgo de fraude.

Uso:
    pytest scripts/tests/test_seed_fraud_risk_assessment.py -v
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_fraud_risk_assessment.py"
EXPECTED_COUNT = 5


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestFraudRiskAssessmentStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'fraud_risk_assessment')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'fraud_risk_assessment' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "entity_id", "assessment_date",
            "risk_areas", "mitigation_measures",
            "next_review_date", "created_at",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM fraud_risk_assessment")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestFraudRiskAssessmentIntegrity:
    def test_all_risk_areas_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM fraud_risk_assessment WHERE risk_areas IS NULL")
        assert cur.fetchone()[0] == 0

    def test_all_mitigation_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM fraud_risk_assessment WHERE mitigation_measures IS NULL")
        assert cur.fetchone()[0] == 0

    def test_entity_id_references(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM fraud_risk_assessment f "
            "LEFT JOIN empresa e ON f.entity_id = e.id "
            "WHERE e.id IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_assessment_dates_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM fraud_risk_assessment WHERE assessment_date IS NULL")
        assert cur.fetchone()[0] == 0

    def test_next_review_after_assessment(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM fraud_risk_assessment "
            "WHERE next_review_date IS NOT NULL AND assessment_date IS NOT NULL "
            "AND next_review_date <= assessment_date"
        )
        assert cur.fetchone()[0] == 0
