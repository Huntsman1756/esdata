#!/usr/bin/env python3
"""Test seed_irs_dta_convention — Validacion de datos de convenios DTA."""

import json
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


class TestIrsDtaConventionStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'irs_dta_convention')"
        )
        assert cur.fetchone()[0] is True

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'irs_dta_convention' "
            "ORDER BY ordinal_position"
        )
        cols = [r[0] for r in cur.fetchall()]
        assert cols == [
            "id", "codigo", "pais_origen", "pais_destino", "titulo",
            "fecha_firma", "fecha_vigencia", "tipo_acuerdo", "boe_referencia",
            "articulos", "texto_completo", "estado", "creado_en", "actualizado_en",
        ]

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM irs_dta_convention")
        assert cur.fetchone()[0] == 10


class TestIrsDtaConventionIntegrity:
    def test_no_null_fields(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_dta_convention "
            "WHERE codigo IS NULL OR pais_origen IS NULL OR pais_destino IS NULL "
            "OR titulo IS NULL OR fecha_firma IS NULL OR fecha_vigencia IS NULL "
            "OR tipo_acuerdo IS NULL OR estado IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_all_codigos_unique(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT codigo, count(*) FROM irs_dta_convention "
            "GROUP BY codigo HAVING count(*) > 1"
        )
        assert cur.fetchone() is None

    def test_tipo_acuerdo_values(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT tipo_acuerdo FROM irs_dta_convention ORDER BY tipo_acuerdo"
        )
        tipos = [r[0] for r in cur.fetchall()]
        assert all(t in ("bilateral", "multilateral") for t in tipos)

    def test_estado_values(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT estado FROM irs_dta_convention ORDER BY estado"
        )
        estados = [r[0] for r in cur.fetchall()]
        assert all(e in ("vigente", "derogado", "en_proceso") for e in estados)

    def test_articulos_valid_json(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT articulos FROM irs_dta_convention WHERE articulos IS NOT NULL"
        )
        for row in cur.fetchall():
            if row[0] is not None:
                result = row[0]
                if isinstance(result, str):
                    result = json.loads(result)
                assert isinstance(result, dict)

    def test_fecha_firma_before_vigencia(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_dta_convention "
            "WHERE fecha_firma >= fecha_vigencia"
        )
        assert cur.fetchone()[0] == 0

    def test_titulo_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_dta_convention "
            "WHERE titulo IS NULL OR titulo = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_texto_completo_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_dta_convention "
            "WHERE texto_completo IS NULL OR texto_completo = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_all_countries_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT pais_origen FROM irs_dta_convention ORDER BY pais_origen"
        )
        paises = [r[0] for r in cur.fetchall()]
        assert len(paises) >= 5

    def test_all_vigentes(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_dta_convention WHERE estado = 'vigente'"
        )
        assert cur.fetchone()[0] == 10

    def test_boe_referencia_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_dta_convention "
            "WHERE boe_referencia IS NULL OR boe_referencia = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_countries_pair_unique(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT pais_origen, pais_destino, count(*) "
            "FROM irs_dta_convention GROUP BY pais_origen, pais_destino "
            "HAVING count(*) > 1"
        )
        assert cur.fetchone() is None
