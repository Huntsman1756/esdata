"""Tests para seed_pgc_marco.py — PGC conceptual framework records."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_pgc_marco import MARCO_RECORDS


class TestPgcMarcoData:
    def test_records_not_empty(self):
        assert len(MARCO_RECORDS) > 0

    def test_records_correct_count(self):
        assert len(MARCO_RECORDS) == 20

    def test_records_have_seven_fields(self):
        for row in MARCO_RECORDS:
            assert len(row) == 7

    def test_records_have_required_keys(self):
        required = {"codigo", "titulo", "tipo", "anio", "texto", "url_boe", "vigente"}
        for row in MARCO_RECORDS:
            assert required.issubset(row.keys())

    def test_records_codigos_unique(self):
        codigos = [r["codigo"] for r in MARCO_RECORDS]
        assert len(codigos) == len(set(codigos))

    def test_records_codigos_format(self):
        for row in MARCO_RECORDS:
            assert row["codigo"].startswith("mc-nv-")

    def test_records_anio_2007(self):
        for row in MARCO_RECORDS:
            assert row["anio"] == 2007

    def test_records_tipo_valoracion(self):
        for row in MARCO_RECORDS:
            assert row["tipo"] == "norma_valoracion"

    def test_records_boe_urls_valid(self):
        for row in MARCO_RECORDS:
            assert row["url_boe"] is not None
            assert "boe.es" in row["url_boe"]
            assert "BOE-A-2007" in row["url_boe"]

    def test_records_vigente_true(self):
        for row in MARCO_RECORDS:
            assert row["vigente"] is True

    def test_records_text_non_empty(self):
        for row in MARCO_RECORDS:
            assert len(row["texto"]) > 10

    def test_records_titulo_non_empty(self):
        for row in MARCO_RECORDS:
            assert len(row["titulo"]) > 10
