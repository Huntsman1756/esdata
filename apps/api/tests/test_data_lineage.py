"""Tests for data lineage and quality (Fase 26.9)."""

import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from services.data_lineage import (
    DataLineageService,
    get_data_lineage_service,
    reset_data_lineage_service,
)


@pytest.fixture(autouse=True)
def clean_service():
    reset_data_lineage_service()
    yield
    reset_data_lineage_service()


# ---------------------------------------------------------------------------
# Lineage recording
# ---------------------------------------------------------------------------


class TestRecordLineage:
    def test_record_basic_lineage(self):
        service = get_data_lineage_service()
        entry = service.record_lineage(
            tabla="articulos",
            campo="texto",
            fuente_origen="legalize-es-worker",
        )
        assert entry.entry_id.startswith("ln-")
        assert entry.tabla == "articulos"
        assert entry.campo == "texto"
        assert entry.fuente_origen == "legalize-es-worker"
        assert entry.calidad_score == 100.0

    def test_record_with_quality_score(self):
        service = get_data_lineage_service()
        entry = service.record_lineage(
            tabla="articulos",
            campo="titulo",
            fuente_origen="worker-a",
            calidad_score=85.0,
            observaciones="Falta contenido en 2 registros",
        )
        assert entry.calidad_score == 85.0
        assert entry.observaciones == "Falta contenido en 2 registros"

    def test_record_with_transformation(self):
        service = get_data_lineage_service()
        entry = service.record_lineage(
            tabla="articulos",
            campo="texto",
            fuente_origen="legalize-es",
            transformacion="extraccion de articulos desde markdown",
            worker_correspondiente="ingestion-worker",
        )
        assert entry.transformacion == "extraccion de articulos desde markdown"
        assert entry.worker_correspondiente == "ingestion-worker"

    def test_multiple_lineage_entries(self):
        service = get_data_lineage_service()
        service.record_lineage(tabla="articulos", campo="texto", fuente_origen="w1")
        service.record_lineage(tabla="articulos", campo="titulo", fuente_origen="w2")
        service.record_lineage(tabla="leyes", campo="texto", fuente_origen="w3")
        assert service.total_records == 3

    def test_unique_entry_ids(self):
        service = get_data_lineage_service()
        e1 = service.record_lineage(tabla="t", campo="c", fuente_origen="w")
        e2 = service.record_lineage(tabla="t", campo="c", fuente_origen="w")
        assert e1.entry_id != e2.entry_id


# ---------------------------------------------------------------------------
# Lineage queries
# ---------------------------------------------------------------------------


class TestLineageQueries:
    def test_get_lineage_by_table(self):
        service = get_data_lineage_service()
        service.record_lineage(tabla="articulos", campo="texto", fuente_origen="w1")
        service.record_lineage(tabla="articulos", campo="titulo", fuente_origen="w2")

        results = service.get_lineage("articulos")
        assert len(results) == 2

    def test_get_lineage_by_table_and_field(self):
        service = get_data_lineage_service()
        service.record_lineage(tabla="articulos", campo="texto", fuente_origen="w1")
        service.record_lineage(tabla="articulos", campo="titulo", fuente_origen="w2")
        service.record_lineage(tabla="articulos", campo="texto", fuente_origen="w3")

        results = service.get_lineage("articulos", campo="texto")
        assert len(results) == 2

    def test_get_lineage_empty_table(self):
        service = get_data_lineage_service()
        results = service.get_lineage("noexiste")
        assert len(results) == 0

    def test_get_lineage_empty_field(self):
        service = get_data_lineage_service()
        service.record_lineage(tabla="articulos", campo="texto", fuente_origen="w1")
        results = service.get_lineage("articulos", campo="noexiste")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Quality scores
# ---------------------------------------------------------------------------


class TestQualityScores:
    def test_quality_single_table(self):
        service = get_data_lineage_service()
        service.record_lineage(tabla="articulos", campo="texto", fuente_origen="w1", calidad_score=90)
        service.record_lineage(tabla="articulos", campo="texto", fuente_origen="w2", calidad_score=80)

        quality = service.get_data_quality("articulos")
        assert quality["tabla"] == "articulos"
        assert quality["avg_score"] == 85.0
        assert quality["min_score"] == 80.0
        assert quality["max_score"] == 90.0
        assert quality["total_records"] == 2

    def test_quality_empty_table(self):
        service = get_data_lineage_service()
        quality = service.get_data_quality("noexiste")
        assert quality["avg_score"] == 0.0
        assert quality["total_records"] == 0

    def test_quality_multiple_tables(self):
        service = get_data_lineage_service()
        service.record_lineage(tabla="articulos", campo="texto", fuente_origen="w1", calidad_score=90)
        service.record_lineage(tabla="leyes", campo="texto", fuente_origen="w2", calidad_score=70)

        all_quality = service.get_all_quality_scores()
        assert len(all_quality) == 2
        # Sorted by avg_score ascending
        assert all_quality[0]["avg_score"] == 70.0
        assert all_quality[1]["avg_score"] == 90.0

    def test_quality_100_score(self):
        service = get_data_lineage_service()
        service.record_lineage(tabla="t", campo="c", fuente_origen="w", calidad_score=100)
        quality = service.get_data_quality("t")
        assert quality["avg_score"] == 100.0

    def test_quality_zero_score(self):
        service = get_data_lineage_service()
        service.record_lineage(tabla="t", campo="c", fuente_origen="w", calidad_score=0)
        quality = service.get_data_quality("t")
        assert quality["avg_score"] == 0.0


# ---------------------------------------------------------------------------
# Data catalog
# ---------------------------------------------------------------------------


class TestDataCatalog:
    def test_get_full_catalog(self):
        service = get_data_lineage_service()
        service.record_lineage(tabla="articulos", campo="texto", fuente_origen="w1")
        service.record_lineage(tabla="leyes", campo="texto", fuente_origen="w2")

        catalog = service.get_data_catalog()
        assert len(catalog) == 2

    def test_catalog_entry_fields(self):
        service = get_data_lineage_service()
        service.record_lineage(tabla="articulos", campo="texto", fuente_origen="legalize-es")
        service.record_lineage(tabla="articulos", campo="titulo", fuente_origen="legalize-es")

        catalog = service.get_data_catalog()
        entry = [e for e in catalog if e["tabla"] == "articulos"][0]
        assert entry["total_campos"] == 2
        assert "texto" in entry["campos"]
        assert "titulo" in entry["campos"]
        assert "legalize-es" in entry["source_tables"]

    def test_catalog_entry_single_table(self):
        service = get_data_lineage_service()
        service.record_lineage(tabla="articulos", campo="texto", fuente_origen="w1")

        entry = service.get_catalog_entry("articulos")
        assert entry is not None
        assert entry["tabla"] == "articulos"
        assert entry["total_lineage_records"] == 1

    def test_catalog_nonexistent_table(self):
        service = get_data_lineage_service()
        assert service.get_catalog_entry("noexiste") is None

    def test_catalog_tracks_workers(self):
        service = get_data_lineage_service()
        service.record_lineage(
            tabla="articulos",
            campo="texto",
            fuente_origen="w1",
            worker_correspondiente="embedder",
        )
        entry = service.get_catalog_entry("articulos")
        assert "embedder" in entry["workers"]


# ---------------------------------------------------------------------------
# Service properties
# ---------------------------------------------------------------------------


class TestServiceProperties:
    def test_total_records(self):
        service = get_data_lineage_service()
        assert service.total_records == 0
        service.record_lineage(tabla="t", campo="c", fuente_origen="w")
        service.record_lineage(tabla="t", campo="c", fuente_origen="w")
        assert service.total_records == 2

    def test_table_count(self):
        service = get_data_lineage_service()
        assert service.table_count == 0
        service.record_lineage(tabla="t1", campo="c", fuente_origen="w")
        service.record_lineage(tabla="t2", campo="c", fuente_origen="w")
        assert service.table_count == 2


class TestDurablePersistence:
    def test_lineage_survives_new_service_instance(self):
        service = DataLineageService()
        service.record_lineage(
            tabla="articulos",
            campo="texto",
            fuente_origen="worker-a",
            calidad_score=88.0,
        )

        new_service = DataLineageService()
        results = new_service.get_lineage("articulos", campo="texto")

        assert len(results) == 1
        assert results[0].calidad_score == 88.0
