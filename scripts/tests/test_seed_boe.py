"""Tests para seed_boe.py — BOE legislation."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_boe import NORMAS_DATA, ARTICULOS_DATA, VERSIONES_DATA, MATERIAS_DATA


class TestBoeNormas:
    """Validaciones de las normas BOE."""

    def test_normas_not_empty(self):
        assert len(NORMAS_DATA) > 0

    def test_normas_have_required_fields(self):
        required = {"codigo", "titulo", "boe_id", "eli_uri", "jurisdiccion", "tipo_fuente", "tipo_documento", "ambito"}
        for n in NORMAS_DATA:
            assert required.issubset(n.keys()), f"Missing fields: {required - n.keys()}"

    def test_normas_jurisdiccion_es(self):
        for n in NORMAS_DATA:
            assert n["jurisdiccion"] == "es"

    def test_normas_tipo_fuente_boe(self):
        for n in NORMAS_DATA:
            assert n["tipo_fuente"] == "boe"

    def test_normas_unique_codigos(self):
        codigos = [n["codigo"] for n in NORMAS_DATA]
        assert len(codigos) == len(set(codigos))

    def test_normas_known_codigos(self):
        expected = {"LIVA", "LIRPF", "LIS", "LGT", "ITPAJD"}
        codigos = {n["codigo"] for n in NORMAS_DATA}
        assert codigos == expected

    def test_normas_boe_id_format(self):
        for n in NORMAS_DATA:
            assert n["boe_id"].startswith("BOE-A-")

    def test_normas_eli_uri_valid(self):
        for n in NORMAS_DATA:
            assert "boe.es" in n["eli_uri"]


class TestBoeArticulos:
    """Validaciones de los articulos."""

    def test_articulos_not_empty(self):
        assert len(ARTICULOS_DATA) > 0

    def test_articulos_have_required_fields(self):
        required = {"norma_codigo", "numero", "titulo", "tipo"}
        for a in ARTICULOS_DATA:
            assert required.issubset(a.keys()), f"Missing fields: {required - a.keys()}"

    def test_articulos_reference_norma(self):
        norma_codigos = {n["codigo"] for n in NORMAS_DATA}
        for a in ARTICULOS_DATA:
            assert a["norma_codigo"] in norma_codigos, f"Unknown norma: {a['norma_codigo']}"

    def test_articulos_tipo_articulo(self):
        for a in ARTICULOS_DATA:
            assert a["tipo"] == "articulo"


class TestBoeVersiones:
    """Validaciones de las versiones de articulo."""

    def test_versiones_not_empty(self):
        assert len(VERSIONES_DATA) > 0

    def test_versiones_have_required_fields(self):
        required = {"norma_codigo", "articulo_numero", "texto", "vigente_desde", "boe_bloque_id"}
        for v in VERSIONES_DATA:
            assert required.issubset(v.keys()), f"Missing fields: {required - v.keys()}"


class TestBoeMaterias:
    """Validaciones de las materias."""

    def test_materias_not_empty(self):
        assert len(MATERIAS_DATA) > 0

    def test_materias_have_required_fields(self):
        required = {"slug", "etiqueta"}
        for m in MATERIAS_DATA:
            assert required.issubset(m.keys()), f"Missing fields: {required - m.keys()}"

    def test_materias_slug_not_empty(self):
        for m in MATERIAS_DATA:
            assert len(m["slug"]) > 0
