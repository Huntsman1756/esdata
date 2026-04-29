#!/usr/bin/env python3
"""Test crypto_transaction seed — Transacciones de criptoactivos DAC8/DAC9.

Uso:
    pytest scripts/tests/test_seed_crypto_transaction.py -v
"""

import re
import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_crypto_transaction.py"
EXPECTED_COUNT = 10


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestCryptoTransactionStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'crypto_transaction')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'crypto_transaction' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "sender_wallet", "receiver_wallet", "sender_jurisdiction",
            "receiver_jurisdiction", "asset_type", "amount", "value_eur",
            "timestamp", "reporting_period", "status",
            "created_at", "updated_at",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM crypto_transaction")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestCryptoTransactionIntegrity:
    def test_all_wallets_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM crypto_transaction "
            "WHERE sender_wallet IS NULL OR receiver_wallet IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_asset_type_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT asset_type FROM crypto_transaction")
        values = [r[0] for r in cur.fetchall()]
        valid_types = {"cryptocurrency", "stablecoin", "defi_token", "security_token"}
        assert all(v in valid_types for v in values)

    def test_amount_positive(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM crypto_transaction "
            "WHERE amount <= 0"
        )
        assert cur.fetchone()[0] == 0

    def test_status_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT status FROM crypto_transaction")
        values = [r[0] for r in cur.fetchall()]
        assert all(v in ("completed", "pending", "failed") for v in values)

    def test_reporting_period_format(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT reporting_period FROM crypto_transaction "
            "WHERE reporting_period IS NOT NULL"
        )
        for row in cur.fetchall():
            assert re.match(r"^\d{4}-Q[1-4]$", row[0]), f"Invalid period: {row[0]}"

    def test_jurisdiction_two_chars(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM crypto_transaction "
            "WHERE (sender_jurisdiction IS NOT NULL AND char_length(sender_jurisdiction) != 2) "
            "OR (receiver_jurisdiction IS NOT NULL AND char_length(receiver_jurisdiction) != 2)"
        )
        assert cur.fetchone()[0] == 0

    def test_eu_transactions_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM crypto_transaction "
            "WHERE sender_jurisdiction IN ('ES', 'FR', 'DE', 'IE', 'LU', 'NL', 'PT') "
            "AND receiver_jurisdiction IN ('ES', 'FR', 'DE', 'IE', 'LU', 'NL', 'PT')"
        )
        assert cur.fetchone()[0] > 0

    def test_cross_border_transactions_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM crypto_transaction "
            "WHERE sender_jurisdiction != receiver_jurisdiction "
            "AND sender_jurisdiction IS NOT NULL"
        )
        assert cur.fetchone()[0] > 0
