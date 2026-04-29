#!/usr/bin/env python3
"""Test seed_cnmv_regulation_link — Validacion de datos de regulaciones CNMV."""

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


class TestCnmvRegulationLinkStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'cnmv_regulation_link')"
        )
        assert cur.fetchone()[0] is True

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'cnmv_regulation_link' "
            "ORDER BY ordinal_position"
        )
        cols = [r[0] for r in cur.fetchall()]
        assert cols == ["id", "documento_referencia", "regulacion_id", "relacion_tipo", "nota"]

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM cnmv_regulation_link")
        assert cur.fetchone()[0] == 16


class TestCnmvRegulationLinkIntegrity:
    def test_no_null_fields(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM cnmv_regulation_link "
            "WHERE documento_referencia IS NULL OR regulacion_id IS NULL "
            "OR relacion_tipo IS NULL OR nota IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_all_documento_referencias_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM cnmv_regulation_link rl "
            "JOIN documento_interpretativo di ON rl.documento_referencia = di.referencia"
        )
        total = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM cnmv_regulation_link")
        assert total == cur.fetchone()[0]

    def test_relacion_tipo_values(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT relacion_tipo FROM cnmv_regulation_link ORDER BY relacion_tipo"
        )
        tipos = [r[0] for r in cur.fetchall()]
        assert all(t in ("aplica", "deriva_de") for t in tipos)

    def test_nota_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM cnmv_regulation_link "
            "WHERE nota IS NULL OR nota = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_all_regulaciones_used(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(DISTINCT regulacion_id) FROM cnmv_regulation_link"
        )
        count = cur.fetchone()[0]
        assert count >= 3

    def test_no_duplicate_documento_regulacion(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT documento_referencia, regulacion_id, count(*) "
            "FROM cnmv_regulation_link GROUP BY documento_referencia, regulacion_id "
            "HAVING count(*) > 1"
        )
        assert cur.fetchone() is None
