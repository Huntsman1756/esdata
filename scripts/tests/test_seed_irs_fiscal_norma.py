#!/usr/bin/env python3
"""Test seed_irs_fiscal_norma — Validacion de datos de normas fiscales IRS."""

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


class TestIrsFiscalNormaStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'irs_fiscal_norma')"
        )
        assert cur.fetchone()[0] is True

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'irs_fiscal_norma' "
            "ORDER BY ordinal_position"
        )
        cols = [r[0] for r in cur.fetchall()]
        assert cols == [
            "id", "codigo", "titulo", "tipo", "anio_vigencia",
            "texto", "url_fuente", "estado", "creado_en", "actualizado_en",
        ]

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM irs_fiscal_norma")
        assert cur.fetchone()[0] == 10


class TestIrsFiscalNormaIntegrity:
    def test_no_null_fields(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_fiscal_norma "
            "WHERE codigo IS NULL OR titulo IS NULL OR tipo IS NULL "
            "OR anio_vigencia IS NULL OR texto IS NULL OR estado IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_all_codigos_unique(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT codigo, count(*) FROM irs_fiscal_norma "
            "GROUP BY codigo HAVING count(*) > 1"
        )
        assert cur.fetchone() is None

    def test_tipo_values_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT tipo FROM irs_fiscal_norma ORDER BY tipo"
        )
        tipos = [r[0] for r in cur.fetchall()]
        assert all(t in ("ley", "reglamento", "publicacion") for t in tipos)

    def test_estado_values_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT estado FROM irs_fiscal_norma ORDER BY estado"
        )
        estados = [r[0] for r in cur.fetchall()]
        assert all(e in ("activo", "derogado", "modificado") for e in estados)

    def test_anios_valid_range(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_fiscal_norma "
            "WHERE anio_vigencia < 1900 OR anio_vigencia > 2030"
        )
        assert cur.fetchone()[0] == 0

    def test_titulo_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_fiscal_norma "
            "WHERE titulo IS NULL OR titulo = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_texto_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_fiscal_norma "
            "WHERE texto IS NULL OR texto = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_ley_type_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_fiscal_norma WHERE tipo = 'ley'"
        )
        assert cur.fetchone()[0] > 0

    def test_reglamento_type_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_fiscal_norma WHERE tipo = 'reglamento'"
        )
        assert cur.fetchone()[0] > 0

    def test_publicacion_type_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_fiscal_norma WHERE tipo = 'publicacion'"
        )
        assert cur.fetchone()[0] > 0

    def test_active_normas(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_fiscal_norma WHERE estado = 'activo'"
        )
        active = cur.fetchone()[0]
        assert active == 10

    def test_url_fuente_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_fiscal_norma "
            "WHERE url_fuente IS NULL OR url_fuente = ''"
        )
        assert cur.fetchone()[0] == 0
