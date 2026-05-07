"""Tests para seed_modelo_articulo.py — AEAT model ↔ article mappings."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_modelo_articulo import MAPPINGS


class TestModeloArticuloData:
    LEGACY_PSEUDO_IMPUESTOS = {
        "IRPF",
        "IS",
        "IVA",
        "OP.347",
        "FACTA",
        "IVA.A",
        "IRPF.T",
        "DAC2",
        "SII",
        "BIEN.EX",
        "PROV.NR",
    }

    def test_mappings_not_empty(self):
        assert len(MAPPINGS) > 0

    def test_mappings_have_seven_fields(self):
        for row in MAPPINGS:
            assert len(row) == 7

    def test_mappings_use_exact_article_keys(self):
        for row in MAPPINGS:
            modelo_codigo, norma, numero, casilla, nota, fuente, url_fuente = row
            assert modelo_codigo
            assert norma not in self.LEGACY_PSEUDO_IMPUESTOS
            assert numero
            assert nota

            if casilla is not None:
                assert isinstance(casilla, str)
                assert casilla

    def test_mappings_have_source_fields(self):
        for row in MAPPINGS:
            _, _, _, _, _, fuente, url_fuente = row
            assert fuente
            assert url_fuente.startswith("https://")

    def test_mappings_are_unique(self):
        assert len(MAPPINGS) == len(set(MAPPINGS))
