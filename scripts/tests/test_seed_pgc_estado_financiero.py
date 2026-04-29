"""Tests para seed_pgc_estado_financiero.py — PGC financial statement states."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_pgc_estado_financiero import ESTADOS, ACCOUNT_UUIDS


class TestPgcEstadoFinancieroData:
    def test_records_not_empty(self):
        assert len(ESTADOS) > 0

    def test_records_correct_count(self):
        assert len(ESTADOS) == 14

    def test_records_have_nine_fields(self):
        for row in ESTADOS:
            assert len(row) == 9

    def test_records_account_ref_valid(self):
        for row in ESTADOS:
            assert row[0] in ACCOUNT_UUIDS

    def test_records_cuenta_code_valid(self):
        for row in ESTADOS:
            assert row[1].isdigit()

    def test_records_estado_non_empty(self):
        for row in ESTADOS:
            assert len(row[2]) > 0

    def test_records_tipo_presentacion_values(self):
        valid = {"anual", "trimestral", "semestral", "mensual"}
        for row in ESTADOS:
            assert row[3] in valid

    def test_records_orden_integer(self):
        for row in ESTADOS:
            assert isinstance(row[4], int)
            assert row[4] > 0

    def test_records_periodo_matches_tipo(self):
        for row in ESTADOS:
            assert row[5] == row[3]

    def test_records_nota_pieds_non_empty(self):
        for row in ESTADOS:
            assert len(row[8]) > 0

    def test_records_cover_all_tipos(self):
        tipos = {r[3] for r in ESTADOS}
        assert "anual" in tipos
        assert "trimestral" in tipos
        assert "semestral" in tipos
        assert "mensual" in tipos
