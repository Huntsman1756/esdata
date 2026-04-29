#!/usr/bin/env python3
"""Test seed_data_lineage — Validacion de datos de lineage."""

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


class TestDataLineageStructure:
    def test_table_exists(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'data_lineage')"
        )
        assert cur.fetchone()[0] is True

    def test_columns_exist(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'data_lineage' "
            "ORDER BY ordinal_position"
        )
        cols = [r[0] for r in cur.fetchall()]
        assert "id" in cols
        assert "entry_id" in cols
        assert "tabla" in cols
        assert "campo" in cols
        assert "fuente_origen" in cols
        assert "transformacion" in cols
        assert "fecha_ingestion" in cols
        assert "worker_correspondiente" in cols
        assert "calidad_score" in cols
        assert "observaciones" in cols

    def test_count_matches_seed(self, db):
        cur = db.cursor()
        cur.execute("SELECT count(*) FROM data_lineage")
        assert cur.fetchone()[0] == 20


class TestDataLineageIntegrity:
    def test_no_null_fields(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM data_lineage "
            "WHERE entry_id IS NULL OR tabla IS NULL OR campo IS NULL "
            "OR fuente_origen IS NULL OR transformacion IS NULL "
            "OR fecha_ingestion IS NULL OR worker_correspondiente IS NULL "
            "OR calidad_score IS NULL"
        )
        assert cur.fetchone()[0] == 0

    def test_all_tablas_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT tabla FROM data_lineage ORDER BY tabla"
        )
        tablas = [r[0] for r in cur.fetchall()]
        expected = [
            "articulo", "csrd_esg_data_point", "documento_fragmento",
            "dora_tic_incident", "empresa", "mifid_client_category",
            "modelo_fiscal_calendar", "norma", "ownership_share",
            "pbc_internal_control", "pgc_cuenta", "psd2_aspsp",
            "screening_entries", "sfdr_product", "ubo_record",
        ]
        assert tablas == expected

    def test_all_workers_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT DISTINCT worker_correspondiente FROM data_lineage ORDER BY worker_correspondiente"
        )
        workers = [r[0] for r in cur.fetchall()]
        expected = [
            "aeat_ingestion", "boe_ingestion", "csrd_ingestion",
            "dora_ingestion", "mercantil_ingestion", "mifid_ingestion",
            "ownership_ingestion", "pbc_ingestion", "pgc_ingestion",
            "psd2_ingestion", "screening_ingestion", "sfdr_ingestion",
            "ubo_ingestion",
        ]
        assert workers == expected

    def test_quality_scores_valid(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM data_lineage "
            "WHERE calidad_score < 0 OR calidad_score > 1"
        )
        assert cur.fetchone()[0] == 0

    def test_quality_scores_positive(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM data_lineage WHERE calidad_score > 0"
        )
        assert cur.fetchone()[0] == 20

    def test_dates_not_future(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM data_lineage "
            "WHERE fecha_ingestion > '2026-12-31'"
        )
        assert cur.fetchone()[0] == 0

    def test_observaciones_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM data_lineage "
            "WHERE observaciones IS NULL OR observaciones = ''"
        )
        assert cur.fetchone()[0] == 0

    def test_transformations_not_empty(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT count(*) FROM data_lineage "
            "WHERE transformacion IS NULL OR transformacion = ''"
        )
        assert cur.fetchone()[0] == 0
