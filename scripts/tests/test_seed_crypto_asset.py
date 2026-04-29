#!/usr/bin/env python3
"""Test crypto_asset seed — Activos cripto relevantes para DAC8/DAC9.

Uso:
    pytest scripts/tests/test_seed_crypto_asset.py -v
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_crypto_asset.py"
EXPECTED_COUNT = 10


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestCryptoAssetStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'crypto_asset')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'crypto_asset' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "asset_type", "reference_uid", "issuer_jurisdiction",
            "is_sha", "market_value_eur", "holders_count",
            "status", "created_at", "updated_at",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM crypto_asset")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestCryptoAssetIntegrity:
    def test_all_reference_uids_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM crypto_asset WHERE reference_uid IS NULL")
        assert cur.fetchone()[0] == 0

    def test_all_reference_uids_unique(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT reference_uid, count(*) FROM crypto_asset "
            "GROUP BY reference_uid HAVING count(*) > 1"
        )
        assert cur.fetchone() is None

    def test_asset_type_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT asset_type FROM crypto_asset")
        values = [r[0] for r in cur.fetchall()]
        valid_types = {"cryptocurrency", "stablecoin", "security_token", "defi_token"}
        assert all(v in valid_types for v in values)

    def test_status_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT status FROM crypto_asset")
        values = [r[0] for r in cur.fetchall()]
        assert all(v in ("active", "inactive", "delisted") for v in values)

    def test_is_sha_boolean(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT is_sha FROM crypto_asset")
        values = [r[0] for r in cur.fetchall()]
        assert all(v in (True, False) for v in values)

    def test_market_value_non_negative(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM crypto_asset "
            "WHERE market_value_eur IS NOT NULL AND market_value_eur < 0"
        )
        assert cur.fetchone()[0] == 0

    def test_holders_count_non_negative(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM crypto_asset "
            "WHERE holders_count IS NOT NULL AND holders_count < 0"
        )
        assert cur.fetchone()[0] == 0

    def test_major_assets_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT reference_uid FROM crypto_asset "
            "WHERE reference_uid IN ('BTC', 'ETH', 'USDT') "
            "ORDER BY reference_uid"
        )
        values = [r[0] for r in cur.fetchall()]
        assert values == ["BTC", "ETH", "USDT"]

    def test_stablecoins_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM crypto_asset WHERE asset_type = 'stablecoin'"
        )
        assert cur.fetchone()[0] > 0
