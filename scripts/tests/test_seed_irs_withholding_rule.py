#!/usr/bin/env python3
"""Test irs_withholding_rule seed — Reglas de retencion fiscal por tipo de renta.

Uso:
    pytest scripts/tests/test_seed_irs_withholding_rule.py -v
"""

import re
import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_irs_withholding_rule.py"
EXPECTED_COUNT = 10


@pytest.fixture(scope="module")
def db():
    conn = psycopg.connect(DEFAULT_DB)
    yield conn
    conn.close()


class TestIrsWithholdingRuleStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'irs_withholding_rule')"
        )
        assert cur.fetchone()[0]

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'irs_withholding_rule' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        for col in [
            "id", "codigo", "tipo_renta", "tipo_renta_espanol",
            "tipo_retencion_default", "tipo_retencion_dta", "pais_aplicable",
            "descripcion", "norma_referencia", "articulo_referencia",
            "estado", "creado_en", "actualizado_en",
        ]:
            assert col in col_names, f"Missing column: {col}"

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM irs_withholding_rule")
        assert cur.fetchone()[0] == EXPECTED_COUNT


class TestIrsWithholdingRuleIntegrity:
    def test_no_null_codigos(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM irs_withholding_rule WHERE codigo IS NULL")
        assert cur.fetchone()[0] == 0

    def test_all_codigos_unique(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT codigo, count(*) FROM irs_withholding_rule "
            "GROUP BY codigo HAVING count(*) > 1"
        )
        assert cur.fetchone() is None

    def test_tipo_renta_values(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT tipo_renta FROM irs_withholding_rule "
            "ORDER BY tipo_renta"
        )
        values = [r[0] for r in cur.fetchall()]
        valid_types = {
            "dividend", "interest", "royalty", "capital_gain",
            "services", "construction", "pension", "lottery",
            "individual",
        }
        assert all(v in valid_types for v in values), f"Invalid tipo_renta: {values}"

    def test_tipo_retencion_range(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_withholding_rule "
            "WHERE tipo_retencion_default < 0 OR tipo_retencion_default > 100"
        )
        assert cur.fetchone()[0] == 0

    def test_estado_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT DISTINCT estado FROM irs_withholding_rule")
        values = [r[0] for r in cur.fetchall()]
        assert all(v in ("active", "inactive", "deprecated") for v in values)

    def test_norma_referencia_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_withholding_rule "
            "WHERE norma_referencia IS NULL OR norma_referencia = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_articulo_referencia_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_withholding_rule "
            "WHERE articulo_referencia IS NULL OR articulo_referencia = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_seeded_codigos_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT codigo FROM irs_withholding_rule ORDER BY codigo"
        )
        codigos = [r[0] for r in cur.fetchall()]
        expected = ["WTH_CAP_GAIN", "WTH_CONSTRUCTION", "WTH_DIVIDEND", "WTH_EU_PARENT",
                     "WTH_INDIVIDUAL", "WTH_INTEREST", "WTH_LOTTERY", "WTH_PENSION",
                     "WTH_ROYALTY", "WTH_SERVICES"]
        assert codigos == expected

    def test_eu_parent_zero_retention(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT tipo_retencion_default FROM irs_withholding_rule "
            "WHERE codigo = 'WTH_EU_PARENT'"
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == 0.0
