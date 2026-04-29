"""Tests para seed_modelo_articulo.py — AEAT model ↔ article mappings."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_modelo_articulo import MAPPINGS


class TestModeloArticuloData:
    def test_mappings_not_empty(self):
        assert len(MAPPINGS) > 0

    def test_mappings_correct_count(self):
        assert len(MAPPINGS) == 100

    def test_mappings_have_five_fields(self):
        for row in MAPPINGS:
            assert len(row) == 5

    def test_mappings_have_required_fields(self):
        for row in MAPPINGS:
            assert row[0] in ("100", "200", "303", "347", "349", "390", "111", "114", "124", "216", "290", "394", "720", "878")

    def test_mappings_impuestos_valid(self):
        valid = {"IRPF", "IS", "IVA", "OP.347", "FACTA", "IVA.A", "IRPF.T", "IRNR", "DAC2", "SII", "BIEN.EX", "PROV.NR"}
        for row in MAPPINGS:
            assert row[1] in valid

    def test_mappings_casillas_non_empty(self):
        for row in MAPPINGS:
            assert len(row[2]) > 0

    def test_mappings_descriptions_non_empty(self):
        for row in MAPPINGS:
            assert len(row[3]) > 0

    def test_mappings_articulo_non_empty(self):
        for row in MAPPINGS:
            assert len(row[4]) > 0

    def test_mappings_modelo_codes_valid(self):
        valid_codes = {"100", "200", "303", "347", "349", "390", "111", "114", "124", "216", "290", "394", "720", "878"}
        for row in MAPPINGS:
            assert row[0] in valid_codes
