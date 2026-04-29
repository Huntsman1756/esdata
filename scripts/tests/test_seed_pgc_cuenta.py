"""Tests para seed_pgc_cuenta.py — PGC chart of accounts."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_pgc_cuenta import CUENTAS


class TestPgcCuentaData:
    def test_cuentas_not_empty(self):
        assert len(CUENTAS) > 0

    def test_cuentas_correct_count(self):
        assert len(CUENTAS) == 270

    def test_cuentas_have_nine_fields(self):
        for row in CUENTAS:
            assert len(row) == 9

    def test_cuentas_codigos_unique(self):
        codigos = [r[0] for r in CUENTAS]
        assert len(codigos) == len(set(codigos))

    def test_cuentas_codigos_numeric(self):
        for row in CUENTAS:
            assert row[0].isdigit()

    def test_cuentas_nivel_valid(self):
        for row in CUENTAS:
            assert row[3] in (1, 2)

    def test_cuentas_saldo_normal_valid(self):
        valid = {"Debe", "Haber"}
        for row in CUENTAS:
            assert row[7] in valid

    def test_cuentas_tipo_cuenta_valid(self):
        valid = {"patrimonio", "financiamiento", "activo_no_corriente", "activo_corriente", "circulante", "financiero", "gastos", "ingresos", "ejercicios_anteriores"}
        for row in CUENTAS:
            assert row[8] in valid

    def test_cuentas_clase_range(self):
        clases = set(r[6] for r in CUENTAS)
        assert {"1", "2", "3", "4", "5", "6", "7", "8"}.issubset(clases)

    def test_cuentas_descriptions_non_empty(self):
        for row in CUENTAS:
            assert len(row[1]) > 0

    def test_cuentas_grupos_valid(self):
        for row in CUENTAS:
            assert row[5].isdigit()
