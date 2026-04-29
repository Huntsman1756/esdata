"""Tests para seed_pgc_norma_valoracion.py — PGC valuation norms."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_pgc_norma_valoracion import NORMAS


class TestPgcNormaValoracionData:
    def test_records_not_empty(self):
        assert len(NORMAS) > 0

    def test_records_correct_count(self):
        assert len(NORMAS) == 20

    def test_records_have_four_fields(self):
        for row in NORMAS:
            assert len(row) == 4

    def test_records_codigos_unique(self):
        codigos = [r[0] for r in NORMAS]
        assert len(codigos) == len(set(codigos))

    def test_records_codigos_format(self):
        for row in NORMAS:
            assert row[0].startswith("NV")

    def test_records_tipo_valoracion(self):
        for row in NORMAS:
            assert row[2] == "norma_valoracion"

    def test_records_text_non_empty(self):
        for row in NORMAS:
            assert len(row[3]) > 10

    def test_records_titulo_non_empty(self):
        for row in NORMAS:
            assert len(row[1]) > 10

    def test_records_codigos_sequential(self):
        codigos = [r[0] for r in NORMAS]
        for i, c in enumerate(codigos, 1):
            assert c == f"NV{i}"

    def test_records_descriptions_spanish(self):
        for row in NORMAS:
            assert any(w in row[3] for w in ["valorarán", "valorará", "reconocerán", "reconocerá", "calculará", "imputarán", "aplicarán", "produc"])
