"""Tests para seed_aeat_models.py — AEAT tax model reference data."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_aeat_models import MODELOS


class TestAeatModelsData:
    """Validaciones basicas de los datos."""

    def test_modeles_not_empty(self):
        assert len(MODELOS) > 0

    def test_modeles_correct_count(self):
        assert len(MODELOS) == 23

    def test_modeles_have_five_fields(self):
        for row in MODELOS:
            assert len(row) == 5, f"Row has {len(row)} fields: {row}"

    def test_modeles_modelo_is_int_or_str(self):
        for row in MODELOS:
            assert isinstance(row[0], (int, str))

    def test_modeles_periodo_valid(self):
        valid = {"mensual", "trimestral", "anual", "variable", "Unica"}
        for row in MODELOS:
            assert row[2] in valid, f"Invalid periodo: {row[2]}"

    def test_modeles_impuesto_valid(self):
        valid = {"IRPF", "IRNR", "IVA", "IS", "ITPAJD", "tasa", "impuesto_real", "estadistico", "informacion"}
        for row in MODELOS:
            assert row[3] in valid, f"Invalid impuesto: {row[3]}"

    def test_modeles_urls_valid(self):
        for row in MODELOS:
            assert row[4] is not None
            assert "agenciatributaria.gob.es" in row[4]

    def test_modeles_unique_codigos(self):
        codigos = [row[0] for row in MODELOS]
        assert len(codigos) == len(set(codigos))
