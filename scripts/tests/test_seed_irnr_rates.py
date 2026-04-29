"""Tests para seed_irnr_rates.py — IRNR withholding rates and instructions."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_irnr_rates import WITHHOLDING_RATES, INSTRUCCIONES


class TestIrnrWithholdingRatesData:
    def test_rates_not_empty(self):
        assert len(WITHHOLDING_RATES) > 0

    def test_rates_correct_count(self):
        assert len(WITHHOLDING_RATES) == 17

    def test_rates_have_six_fields(self):
        for row in WITHHOLDING_RATES:
            assert len(row) == 6

    def test_rates_modelo_codes_valid(self):
        valid = {"124", "212", "116", "123", "216", "296", "878"}
        for row in WITHHOLDING_RATES:
            assert row[0] in valid

    def test_rates_tipo_retencion_range(self):
        for row in WITHHOLDING_RATES:
            assert 0 < row[2] <= 50

    def test_rates_articulo_non_empty(self):
        for row in WITHHOLDING_RATES:
            assert len(row[3]) > 0

    def test_rates_fuente_non_empty(self):
        for row in WITHHOLDING_RATES:
            assert len(row[4]) > 0

    def test_rates_activo_true(self):
        for row in WITHHOLDING_RATES:
            assert row[5] is True

    def test_rates_tipo_renta_non_empty(self):
        for row in WITHHOLDING_RATES:
            assert len(row[1]) > 0


class TestIrnrInstruccionesData:
    def test_instrucciones_not_empty(self):
        assert len(INSTRUCCIONES) > 0

    def test_instrucciones_correct_count(self):
        assert len(INSTRUCCIONES) == 11

    def test_instrucciones_have_four_fields(self):
        for row in INSTRUCCIONES:
            assert len(row) == 4

    def test_instrucciones_modelo_codes_valid(self):
        valid = {"124", "212", "116", "123", "216", "296", "878"}
        for row in INSTRUCCIONES:
            assert row[0] in valid

    def test_instrucciones_seccion_non_empty(self):
        for row in INSTRUCCIONES:
            assert len(row[1]) > 0

    def test_instrucciones_titulo_non_empty(self):
        for row in INSTRUCCIONES:
            assert len(row[2]) > 0

    def test_instrucciones_contenido_non_empty(self):
        for row in INSTRUCCIONES:
            assert len(row[3]) > 10
