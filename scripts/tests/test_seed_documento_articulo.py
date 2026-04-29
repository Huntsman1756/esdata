#!/usr/bin/env python3
"""Test documento_articulo seed — Vinculos documentos y articulos legales.

Uso:
    pytest scripts/tests/test_seed_documento_articulo.py -v
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_documento_articulo.py"
EXPECTED_COUNT = 15


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestDocumentoArticuloStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'documento_articulo')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'documento_articulo' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "documento_id", "articulo_id", "metodo_enlace",
            "confianza_enlace", "nota",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM documento_articulo")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestDocumentoArticuloIntegrity:
    def test_all_metodo_enlace_present(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM documento_articulo WHERE metodo_enlace IS NULL")
        assert cur.fetchone()[0] == 0

    def test_metodo_enlace_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT metodo_enlace FROM documento_articulo")
        values = [r[0] for r in cur.fetchall()]
        valid_methods = {"exact_match", "semantic_match", "partial_match"}
        assert all(v in valid_methods for v in values)

    def test_confianza_range(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM documento_articulo "
            "WHERE confianza_enlace < 0 OR confianza_enlace > 1"
        )
        assert cur.fetchone()[0] == 0

    def test_documento_id_references(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM documento_articulo d "
            "LEFT JOIN documento_interpretativo doc ON d.documento_id = doc.id "
            "WHERE doc.id IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_articulo_id_references(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM documento_articulo d "
            "LEFT JOIN articulo a ON d.articulo_id = a.id "
            "WHERE a.id IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_high_confidence_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM documento_articulo "
            "WHERE confianza_enlace >= 0.9"
        )
        assert cur.fetchone()[0] > 0

    def test_low_confidence_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM documento_articulo "
            "WHERE confianza_enlace < 0.75"
        )
        assert cur.fetchone()[0] > 0
