#!/usr/bin/env python3
"""Test seed_articulo_materia — Validacion de datos semilla articulo↔materia."""

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


class TestArticuloMateriaStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'articulo_materia')"
        )
        assert cur.fetchone()[0] is True

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'articulo_materia' "
            "ORDER BY ordinal_position"
        )
        cols = [r[0] for r in cur.fetchall()]
        assert "articulo_id" in cols
        assert "materia_id" in cols
        assert "relevancia" in cols

    def test_all_not_null(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'articulo_materia'"
        )
        nulls = [r[0] for r in cur.fetchall()]
        assert all(n == "NO" for n in nulls)

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM articulo_materia")
        count = cur.fetchone()[0]
        assert count == 97


class TestArticuloMateriaIntegrity:
    def test_all_articulo_ids_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM articulo_materia am "
            "JOIN articulo a ON am.articulo_id = a.id"
        )
        total = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM articulo_materia")
        assert total == cur.fetchone()[0]

    def test_all_materia_ids_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM articulo_materia am "
            "JOIN materia m ON am.materia_id = m.id"
        )
        total = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM articulo_materia")
        assert total == cur.fetchone()[0]

    def test_relevancia_values_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT relevancia FROM articulo_materia "
            "ORDER BY relevancia"
        )
        vals = [r[0] for r in cur.fetchall()]
        assert all(v in (1, 2) for v in vals)

    def test_at_least_one_mapping_per_materia(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(DISTINCT materia_id) FROM articulo_materia"
        )
        count = cur.fetchone()[0]
        assert count >= 5

    def test_no_null_fields(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM articulo_materia "
            "WHERE articulo_id IS NULL OR materia_id IS NULL OR relevancia IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_all_articles_unique_materia(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT articulo_id, count(*) as cnt "
            "FROM articulo_materia GROUP BY articulo_id "
            "HAVING count(*) > 1"
        )
        rows = cur.fetchall()
        assert len(rows) == 0

    def test_materia_facta_has_mappings(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM articulo_materia am "
            "JOIN materia m ON am.materia_id = m.id "
            "WHERE m.slug = 'facta'"
        )
        assert cur.fetchone()[0] > 0

    def test_materia_retenciones_has_mappings(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM articulo_materia am "
            "JOIN materia m ON am.materia_id = m.id "
            "WHERE m.slug = 'retenciones-irpf'"
        )
        assert cur.fetchone()[0] > 0
