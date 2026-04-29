#!/usr/bin/env python3
"""Test dac_crypto_report seed — Reportes de criptoactivos DAC8.

Uso:
    pytest scripts/tests/test_seed_dac_crypto_report.py -v
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_dac_crypto_report.py"
EXPECTED_COUNT = 10


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestDacCryptoReportStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'dac_crypto_report')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'dac_crypto_report' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "entity_id", "reporting_period", "submitted_at",
            "status", "crypto_transactions_count", "wallet_holders_count",
            "created_at",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM dac_crypto_report")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestDacCryptoReportIntegrity:
    def test_reporting_period_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM dac_crypto_report "
            "WHERE reporting_period IS NULL OR reporting_period = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_status_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT status FROM dac_crypto_report")
        values = [r[0] for r in cur.fetchall()]
        valid_statuses = {"submitted", "draft", "pending_review", "not_started"}
        assert all(v in valid_statuses for v in values)

    def test_crypto_transactions_non_negative(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM dac_crypto_report "
            "WHERE crypto_transactions_count IS NOT NULL AND crypto_transactions_count < 0"
        )
        assert cur.fetchone()[0] == 0

    def test_wallet_holders_non_negative(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM dac_crypto_report "
            "WHERE wallet_holders_count IS NOT NULL AND wallet_holders_count < 0"
        )
        assert cur.fetchone()[0] == 0

    def test_submitted_at_for_submitted(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM dac_crypto_report "
            "WHERE status = 'submitted' AND submitted_at IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_period_format(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT reporting_period FROM dac_crypto_report "
            "WHERE reporting_period IS NOT NULL"
        )
        import re
        for row in cur.fetchall():
            assert re.match(r"^\d{4}-Q[1-4]$", row[0]), f"Invalid period: {row[0]}"

    def test_entity_id_references(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM dac_crypto_report r "
            "LEFT JOIN dac_reporting_entity e ON r.entity_id = e.id "
            "WHERE e.id IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_quarters_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT reporting_period FROM dac_crypto_report "
            "ORDER BY reporting_period"
        )
        periods = [r[0] for r in cur.fetchall()]
        assert "2025-Q1" in periods
        assert "2025-Q2" in periods

    def test_various_statuses_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT status FROM dac_crypto_report")
        values = [r[0] for r in cur.fetchall()]
        assert len(values) >= 3
