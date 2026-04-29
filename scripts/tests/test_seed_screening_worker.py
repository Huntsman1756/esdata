#!/usr/bin/env python3
"""Test seed_screening_worker — Validacion de datos de screening."""

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


class TestScreeningLists:
    def test_lists_exist(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM screening_lists")
        assert cur.fetchone()[0] >= 5

    def test_lists_tipo_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT tipo FROM screening_lists ORDER BY tipo"
        )
        tipos = [r[0] for r in cur.fetchall()]
        assert all(t in ("sanctions", "pep", "watchlist") for t in tipos)

    def test_lists_pais_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT pais FROM screening_lists ORDER BY pais"
        )
        paises = [r[0] for r in cur.fetchall()]
        assert all(p in ("US", "EU", "UN", "ES") for p in paises)

    def test_lists_all_active(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM screening_lists WHERE activo = true"
        )
        total = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM screening_lists")
        assert total == cur.fetchone()[0]

    def test_list_ofac_sdn_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM screening_lists WHERE codigo = 'OFAC_SDN'"
        )
        assert cur.fetchone()[0] == 1

    def test_list_eu_sanctions_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM screening_lists WHERE codigo = 'EU_SANCTIONS'"
        )
        assert cur.fetchone()[0] == 1

    def test_list_sepblac_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM screening_lists WHERE codigo = 'SEPBLAC'"
        )
        assert cur.fetchone()[0] == 1

    def test_list_es_peps_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM screening_lists WHERE codigo = 'ES_PEPS'"
        )
        assert cur.fetchone()[0] == 1


class TestScreeningEntries:
    def test_entries_not_empty(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM screening_entries")
        assert cur.fetchone()[0] > 0

    def test_entries_correct_count(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM screening_entries")
        count = cur.fetchone()[0]
        assert count == 14

    def test_entries_have_expected_fields(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'screening_entries' "
            "ORDER BY ordinal_position"
        )
        cols = [r[0] for r in cur.fetchall()]
        expected = [
            "id", "list_id", "entidad_id", "nombre", "nombre_normalizado",
            "tipo_entidad", "pais", "nif", "fecha_nacimiento",
            "aliases", "categorias", "descripcion", "fecha_sancion",
            "fecha_alta", "fecha_baja", "activo", "metadata_json",
            "created_at", "embedding_384", "embedding_model_name",
            "content_hash"
        ]
        assert cols == expected

    def test_entries_have_unique_entidad_ids(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT list_id, entidad_id, count(*) FROM screening_entries "
            "GROUP BY list_id, entidad_id HAVING count(*) > 1"
        )
        assert cur.fetchone() is None

    def test_entries_all_have_list_ids(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM screening_entries e "
            "JOIN screening_lists l ON e.list_id = l.id"
        )
        total = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM screening_entries")
        assert total == cur.fetchone()[0]

    def test_entries_names_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM screening_entries "
            "WHERE nombre IS NULL OR nombre = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_entries_types_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT tipo_entidad FROM screening_entries ORDER BY tipo_entidad"
        )
        tipos = [r[0] for r in cur.fetchall()]
        assert all(t in ("person", "entity") for t in tipos)

    def test_entries_all_active(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM screening_entries WHERE activo = true"
        )
        total = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM screening_entries")
        assert total == cur.fetchone()[0]

    def test_entries_have_aliases(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM screening_entries "
            "WHERE aliases IS NOT NULL AND array_length(aliases, 1) > 0"
        )
        assert cur.fetchone()[0] > 0

    def test_entries_have_categories(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM screening_entries "
            "WHERE categorias IS NOT NULL AND array_length(categorias, 1) > 0"
        )
        assert cur.fetchone()[0] > 0

    def test_entries_have_metadata_json(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM screening_entries "
            "WHERE metadata_json IS NOT NULL"
        )
        assert cur.fetchone()[0] > 0
