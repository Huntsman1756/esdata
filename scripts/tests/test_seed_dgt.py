"""Tests para seed_dgt.py — DGT consultaciones vinculantes."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_dgt import DATA


class TestDgtData:
    """Validaciones basicas de los datos DGT."""

    def test_data_not_empty(self):
        assert len(DATA) > 0

    def test_data_correct_count(self):
        assert len(DATA) == 10

    def test_data_have_ten_fields(self):
        for row in DATA:
            assert len(row) == 10, f"Row has {len(row)} fields: {row}"

    def test_data_tipo_documento_consulta_vinculante(self):
        for row in DATA:
            assert row[0] == "consulta_vinculante"

    def test_data_organismo_dgt(self):
        for row in DATA:
            assert row[1] == "DGT"

    def test_data_jurisdiccion_es(self):
        for row in DATA:
            assert row[2] == "es"

    def test_data_referencia_format(self):
        for row in DATA:
            assert row[5].startswith("V"), f"Referencia should start with V: {row[5]}"

    def test_data_titulo_not_empty(self):
        for row in DATA:
            assert len(row[7]) > 0

    def test_data_texto_not_empty(self):
        for row in DATA:
            assert len(row[8]) > 0

    def test_data_url_valid(self):
        for row in DATA:
            assert row[9] is not None
            assert "petete.tributos.hacienda.gob.es" in row[9]

    def test_data_unique_referencias(self):
        refs = [row[5] for row in DATA]
        assert len(refs) == len(set(refs)), "Referencias should be unique"
