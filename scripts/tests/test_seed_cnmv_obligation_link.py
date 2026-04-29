#!/usr/bin/env python3
"""Test seed_cnmv_obligation_link — Validacion de datos de obligaciones CNMV."""

import os
import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://esdata:esdata_dev@localhost:5432/esdata",
)


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DB_URL)
    yield conn
    conn.close()


class TestCnmvObligationLinkStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'cnmv_obligation_link')"
        )
        assert cur.fetchone()[0] is True

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'cnmv_obligation_link' "
            "ORDER BY ordinal_position"
        )
        cols = [r[0] for r in cur.fetchall()]
        assert cols == ["id", "documento_referencia", "tipo_obligacion", "nota"]

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM cnmv_obligation_link")
        assert cur.fetchone()[0] == 16


class TestCnmvObligationLinkIntegrity:
    def test_no_null_fields(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM cnmv_obligation_link "
            "WHERE documento_referencia IS NULL OR tipo_obligacion IS NULL OR nota IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_all_documento_referencias_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM cnmv_obligation_link ol "
            "JOIN documento_interpretativo di ON ol.documento_referencia = di.referencia"
        )
        total = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM cnmv_obligation_link")
        assert total == cur.fetchone()[0]

    def test_tipo_obligacion_values(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT tipo_obligacion FROM cnmv_obligation_link ORDER BY tipo_obligacion"
        )
        tipos = [r[0] for r in cur.fetchall()]
        expected = [
            "compliance", "conflictos_interes", "gobierno_corporativo",
            "informe_anual", "informe_operaciones", "informe_trimestral",
            "transparencia",
        ]
        assert tipos == expected

    def test_nota_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM cnmv_obligation_link "
            "WHERE nota IS NULL OR nota = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_all_tipo_obligaciones_used(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(DISTINCT tipo_obligacion) FROM cnmv_obligation_link"
        )
        assert cur.fetchone()[0] == 7

    def test_no_duplicate_documento_tipo(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT documento_referencia, tipo_obligacion, count(*) "
            "FROM cnmv_obligation_link GROUP BY documento_referencia, tipo_obligacion "
            "HAVING count(*) > 1"
        )
        assert cur.fetchone() is None
