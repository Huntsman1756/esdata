"""Tests para seed_aeat_irnr.py — IRNR models."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_aeat_irnr import IRNR_MODELOS


class TestIrnrData:
    """Validaciones basicas de los datos IRNR."""

    def test_modeles_not_empty(self):
        assert len(IRNR_MODELOS) > 0

    def test_modeles_correct_count(self):
        assert len(IRNR_MODELOS) == 7

    def test_modeles_have_required_fields(self):
        required = {"codigo", "nombre", "periodo", "impuesto", "url_info"}
        for m in IRNR_MODELOS:
            assert required.issubset(m.keys()), f"Missing fields: {required - m.keys()}"

    def test_modeles_impuesto_irnr(self):
        for m in IRNR_MODELOS:
            assert m["impuesto"] == "IRNR"

    def test_modeles_periodo_valid(self):
        valid = {"mensual", "trimestral", "anual"}
        for m in IRNR_MODELOS:
            assert m["periodo"] in valid

    def test_modeles_urls_valid(self):
        for m in IRNR_MODELOS:
            assert "agenciatributaria.gob.es" in m["url_info"]

    def test_modeles_unique_codigos(self):
        codigos = [m["codigo"] for m in IRNR_MODELOS]
        assert len(codigos) == len(set(codigos))

    def test_modeles_known_codigos(self):
        expected = {"116", "123", "124", "212", "216", "296", "878"}
        codigos = {m["codigo"] for m in IRNR_MODELOS}
        assert codigos == expected
