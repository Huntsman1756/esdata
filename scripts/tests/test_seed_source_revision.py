#!/usr/bin/env python3
"""Test seed_source_revision — Validacion de datos de revision de fuentes."""

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


class TestSourceRevisionStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'source_revision')"
        )
        assert cur.fetchone()[0] is True

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'source_revision' "
            "ORDER BY ordinal_position"
        )
        cols = [r[0] for r in cur.fetchall()]
        assert "id" in cols
        assert "worker_name" in cols
        assert "source_entity_tipo" in cols
        assert "source_entity_id" in cols
        assert "content_hash_sha256" in cols
        assert "etag" in cols
        assert "last_modified" in cols
        assert "content_length" in cols
        assert "fetched_at" in cols

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM source_revision")
        assert cur.fetchone()[0] == 15


class TestSourceRevisionIntegrity:
    def test_hash_length(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM source_revision "
            "WHERE char_length(content_hash_sha256) = 64"
        )
        assert cur.fetchone()[0] == 15

    def test_hash_is_lowercase(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM source_revision "
            "WHERE content_hash_sha256 != lower(content_hash_sha256)"
        )
        assert cur.fetchone()[0] == 0

    def test_content_length_positive(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM source_revision "
            "WHERE content_length IS NOT NULL AND content_length <= 0"
        )
        assert cur.fetchone()[0] == 0

    def test_content_length_not_negative(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM source_revision "
            "WHERE content_length IS NOT NULL AND content_length < 0"
        )
        assert cur.fetchone()[0] == 0

    def test_all_workers_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT worker_name FROM source_revision ORDER BY worker_name"
        )
        workers = [r[0] for r in cur.fetchall()]
        expected = [
            "aeat_ingestion", "boe_ingestion", "csrd_ingestion",
            "dora_ingestion", "mercantil_ingestion", "pbc_ingestion",
            "pgc_ingestion", "psd2_ingestion", "screening_ingestion",
            "sfdr_ingestion",
        ]
        assert workers == expected

    def test_all_entity_tipos_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT source_entity_tipo FROM source_revision "
            "ORDER BY source_entity_tipo"
        )
        tipos = [r[0] for r in cur.fetchall()]
        expected = [
            "aeat_calendario", "boe_norma", "boe_noticia", "directiva_ue",
            "eu_sanctions", "guia_pgc", "ley_es", "ofac_sdn",
            "rd_pgс", "registro_mercantil", "reglamento_ue",
        ]
        assert tipos == expected

    def test_entity_ids_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM source_revision "
            "WHERE source_entity_id IS NULL OR source_entity_id = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_fetched_at_not_null(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM source_revision WHERE fetched_at IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_unique_entity_per_worker(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT worker_name, source_entity_id, count(*) "
            "FROM source_revision GROUP BY worker_name, source_entity_id "
            "HAVING count(*) > 1"
        )
        assert cur.fetchone() is None

    def test_dates_not_future(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM source_revision "
            "WHERE fetched_at > '2026-12-31'"
        )
        assert cur.fetchone()[0] == 0
