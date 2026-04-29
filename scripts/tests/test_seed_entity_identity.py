"""Tests para seed_entity_identity.py — Entity identities/LEI."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_entity_identity import ENTITY_IDENTIFIERS, ENTITY_ALIASES, _normalize_name


class TestEntityIdentifiers:
    """Validaciones de identidades de entidad."""

    def test_not_empty(self):
        assert len(ENTITY_IDENTIFIERS) > 0

    def test_correct_count(self):
        assert len(ENTITY_IDENTIFIERS) == 5

    def test_have_required_fields(self):
        required = {"empresa_id", "lei", "nombre_legal", "pais", "estado", "vigencia_desde", "vigencia_hasta", "fuente_ref"}
        for e in ENTITY_IDENTIFIERS:
            assert required.issubset(e.keys())

    def test_pais_es(self):
        for e in ENTITY_IDENTIFIERS:
            assert e["pais"] == "ES"

    def test_estado_active(self):
        for e in ENTITY_IDENTIFIERS:
            assert e["estado"] == "active"

    def test_lei_format(self):
        for e in ENTITY_IDENTIFIERS:
            assert len(e["lei"]) >= 18, f"LEI should be at least 18 chars: {e['lei']}"
            assert e["lei"].isalnum()

    def test_fuente_ref_gleif(self):
        for e in ENTITY_IDENTIFIERS:
            assert e["fuente_ref"].startswith("GLEIF:")

    def test_unique_empresas(self):
        ids = [e["empresa_id"] for e in ENTITY_IDENTIFIERS]
        assert len(ids) == len(set(ids))

    def test_known_entities(self):
        nombres = {e["nombre_legal"] for e in ENTITY_IDENTIFIERS}
        assert "IBERBANK, S.A." in nombres
        assert "BANCO SANTANDER, S.A." in nombres
        assert "BBVA, BANCO BILBAO VIZCAYA ARGENTARIA, S.A." in nombres


class TestEntityAliases:
    """Validaciones de aliases de entidad."""

    def test_not_empty(self):
        assert len(ENTITY_ALIASES) > 0

    def test_correct_count(self):
        assert len(ENTITY_ALIASES) == 10

    def test_have_required_fields(self):
        required = {"empresa_id", "alias", "fuente", "confianza"}
        for a in ENTITY_ALIASES:
            assert required.issubset(a.keys())

    def test_fuente_gleif(self):
        for a in ENTITY_ALIASES:
            assert a["fuente"] == "GLEIF"

    def test_confianza_range(self):
        for a in ENTITY_ALIASES:
            assert 0 < a["confianza"] <= 1.0

    def test_alias_not_empty(self):
        for a in ENTITY_ALIASES:
            assert len(a["alias"]) > 0


class TestNormalizeName:
    """Validaciones de normalizacion de nombres."""

    def test_lowercases(self):
        assert _normalize_name("BANCO SANTANDER") == "banco santander"

    def test_removes_accents(self):
        result = _normalize_name("CAFÉ")
        assert "cafe" in result

    def test_removes_special_chars(self):
        result = _normalize_name("S.A.")
        assert "sa" in result

    def test_handles_none(self):
        assert _normalize_name(None) == ""

    def test_strips_whitespace(self):
        assert _normalize_name("  test  ") == "test"
