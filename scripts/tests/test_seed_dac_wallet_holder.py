#!/usr/bin/env python3
"""Test dac_wallet_holder seed — Titulares de wallets DAC crypto.

Uso:
    pytest scripts/tests/test_seed_dac_wallet_holder.py -v
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_dac_wallet_holder.py"
EXPECTED_COUNT = 10


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestDacWalletHolderStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'dac_wallet_holder')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'dac_wallet_holder' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "report_id", "wallet_address", "holder_tin",
            "holder_member_state", "holder_type", "total_value_eur",
            "verification_status", "created_at",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM dac_wallet_holder")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestDacWalletHolderIntegrity:
    def test_all_wallet_addresses_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM dac_wallet_holder WHERE wallet_address IS NULL")
        assert cur.fetchone()[0] == 0

    def test_all_wallet_addresses_unique(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT wallet_address, count(*) FROM dac_wallet_holder "
            "GROUP BY wallet_address HAVING count(*) > 1"
        )
        assert cur.fetchone() is None

    def test_holder_type_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT holder_type FROM dac_wallet_holder")
        values = [r[0] for r in cur.fetchall()]
        valid_types = {"individual", "entity", "unknown"}
        assert all(v in valid_types for v in values)

    def test_verification_status_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT verification_status FROM dac_wallet_holder")
        values = [r[0] for r in cur.fetchall()]
        valid_statuses = {"verified", "pending", "rejected"}
        assert all(v in valid_statuses for v in values)

    def test_total_value_non_negative(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM dac_wallet_holder "
            "WHERE total_value_eur IS NOT NULL AND total_value_eur < 0"
        )
        assert cur.fetchone()[0] == 0

    def test_report_id_references(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM dac_wallet_holder w "
            "LEFT JOIN dac_crypto_report r ON w.report_id = r.id "
            "WHERE r.id IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_total_value_eur_numeric(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'dac_wallet_holder' AND column_name = 'total_value_eur'"
        )
        assert cur.fetchone()[0] == "numeric"

    def test_eu_holders_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM dac_wallet_holder "
            "WHERE holder_member_state IS NOT NULL AND holder_member_state != 'US'"
        )
        assert cur.fetchone()[0] > 0

    def test_non_eu_holders_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM dac_wallet_holder "
            "WHERE holder_member_state IS NOT NULL AND holder_member_state = 'US'"
        )
        assert cur.fetchone()[0] > 0
