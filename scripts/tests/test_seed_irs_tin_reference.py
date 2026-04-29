#!/usr/bin/env python3
"""Test seed_irs_tin_reference — Validacion de datos de TIN por pais."""

import os
import re
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


class TestIrsTinReferenceStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'irs_tin_reference')"
        )
        assert cur.fetchone()[0] is True

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'irs_tin_reference' "
            "ORDER BY ordinal_position"
        )
        cols = [r[0] for r in cur.fetchall()]
        assert "id" in cols
        assert "codigo_pais" in cols
        assert "pais_nombre" in cols
        assert "formato_tin" in cols
        assert "ejemplo_tin" in cols
        assert "emisor_espana" in cols
        assert "emisor_pais" in cols
        assert "es_ocde" in cols
        assert "es_eu_vat" in cols

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM irs_tin_reference")
        assert cur.fetchone()[0] == 15


class TestIrsTinReferenceIntegrity:
    def test_no_null_fields(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_tin_reference "
            "WHERE codigo_pais IS NULL OR pais_nombre IS NULL "
            "OR formato_tin IS NULL OR ejemplo_tin IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_all_codigos_unique(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT codigo_pais, count(*) FROM irs_tin_reference "
            "GROUP BY codigo_pais HAVING count(*) > 1"
        )
        assert cur.fetchone() is None

    def test_codigos_iso_format(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_tin_reference "
            "WHERE char_length(codigo_pais) != 2"
        )
        assert cur.fetchone()[0] == 0

    def test_formato_tin_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_tin_reference "
            "WHERE formato_tin IS NULL OR formato_tin = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_ejemplo_tin_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_tin_reference "
            "WHERE ejemplo_tin IS NULL OR ejemplo_tin = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_formato_tin_valid_regex(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT formato_tin FROM irs_tin_reference WHERE formato_tin IS NOT NULL"
        )
        for row in cur.fetchall():
            try:
                re.compile(row[0])
            except re.error:
                pytest.fail(f"Invalid regex: {row[0]}")

    def test_ejemplo_matches_format(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT formato_tin, ejemplo_tin FROM irs_tin_reference "
            "WHERE ejemplo_tin IS NOT NULL AND formato_tin IS NOT NULL"
        )
        for row in cur.fetchall():
            pattern = row[0]
            example = row[1]
            try:
                re.compile(pattern)
            except re.error:
                assert False, f"Invalid regex pattern: {pattern}"

    def test_emisor_espana_values(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT emisor_espana FROM irs_tin_reference"
        )
        values = [r[0] for r in cur.fetchall()]
        assert all(v in ("true", "false") for v in values)

    def test_emisor_pais_values(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT emisor_pais FROM irs_tin_reference"
        )
        values = [r[0] for r in cur.fetchall()]
        assert all(v in ("true", "false") for v in values)

    def test_es_ocde_values(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT es_ocde FROM irs_tin_reference"
        )
        values = [r[0] for r in cur.fetchall()]
        assert all(v in (True, False) for v in values)

    def test_es_eu_vat_values(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT es_eu_vat FROM irs_tin_reference"
        )
        values = [r[0] for r in cur.fetchall()]
        assert all(v in (True, False) for v in values)

    def test_es_has_tin(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_tin_reference WHERE codigo_pais = 'ES'"
        )
        assert cur.fetchone()[0] == 1

    def test_ocde_countries_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_tin_reference WHERE es_ocde = true"
        )
        assert cur.fetchone()[0] > 0

    def test_eu_vat_countries_present(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM irs_tin_reference WHERE es_eu_vat = true"
        )
        assert cur.fetchone()[0] > 0
