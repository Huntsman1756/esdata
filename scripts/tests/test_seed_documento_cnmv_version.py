#!/usr/bin/env python3
"""Test documento_cnmv_version seed — Versiones historicas de documentos CNMV.

Uso:
    pytest scripts/tests/test_seed_documento_cnmv_version.py -v
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_documento_cnmv_version.py"
EXPECTED_COUNT = 10


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestDocumentoCnmvVersionStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'documento_cnmv_version')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'documento_cnmv_version' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "documento_referencia", "version_numero",
            "estado_version", "fecha_version", "resumen_cambios",
            "fuente_version", "creado_en",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM documento_cnmv_version")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestDocumentoCnmvVersionIntegrity:
    def test_all_documentos_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM documento_cnmv_version WHERE documento_referencia IS NULL")
        assert cur.fetchone()[0] == 0

    def test_all_version_numeros_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM documento_cnmv_version WHERE version_numero IS NULL")
        assert cur.fetchone()[0] == 0

    def test_version_number_positive(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM documento_cnmv_version "
            "WHERE version_numero <= 0"
        )
        assert cur.fetchone()[0] == 0

    def test_estado_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT estado_version FROM documento_cnmv_version")
        values = [r[0] for r in cur.fetchall()]
        valid_states = {"draft", "published", "amended", "superseded"}
        assert all(v in valid_states for v in values)

    def test_fuente_version_consistent(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT fuente_version FROM documento_cnmv_version")
        values = [r[0] for r in cur.fetchall()]
        assert all(v and len(v) > 0 for v in values)

    def test_dates_not_future(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM documento_cnmv_version "
            "WHERE fecha_version > CURRENT_DATE"
        )
        assert cur.fetchone()[0] == 0

    def test_multi_version_documents(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT documento_referencia, count(*) FROM documento_cnmv_version "
            "GROUP BY documento_referencia HAVING count(*) > 1"
        )
        assert cur.fetchone() is not None
