"""Tests for CRD/BRRD/EMIR worker - Fase 46.10."""

# ruff: noqa: I001

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crd_brrd_emir import (
    CRD_BRRD_NORMAS,
    SEED_CRD_ENTITIES,
    _fetch_eurlex_text,
)

class TestCRDNormas:
    def test_has_5_normas(self):
        assert len(CRD_BRRD_NORMAS) == 5

    def test_normas_have_required_fields(self):
        required = ["codigo", "boe_id", "tipo_documento", "titulo", "ambito", "regulacion"]
        for norma in CRD_BRRD_NORMAS:
            for field in required:
                assert field in norma

    def test_normas_have_celex_ids(self):
        for norma in CRD_BRRD_NORMAS:
            assert norma["boe_id"].startswith("EUR-CELEX-")

    def test_normas_are_crd_brrd_emir_related(self):
        for norma in CRD_BRRD_NORMAS:
            assert norma["regulacion"] == "crd_brrd_emir"

    def test_has_both_directives_and_regulations(self):
        tipos = set(n["tipo_documento"] for n in CRD_BRRD_NORMAS)
        assert "directiva" in tipos
        assert "reglamento" in tipos

    def test_has_crd_brrd_and_emir(self):
        codigos = [n["codigo"] for n in CRD_BRRD_NORMAS]
        assert any("CRD" in c for c in codigos)
        assert any("BRRD" in c for c in codigos)
        assert any("EMIR" in c for c in codigos)

    def test_crd_and_crr_normas_use_validated_celex_ids(self):
        normas_by_codigo = {norma["codigo"]: norma for norma in CRD_BRRD_NORMAS}

        assert normas_by_codigo["CRD_V_2019_2058"]["boe_id"] == "EUR-CELEX-32019L0878"
        assert normas_by_codigo["CRR_II_2019_2057"]["boe_id"] == "EUR-CELEX-32019R0876"

class TestSeedEntities:
    def test_has_5_entities(self):
        assert len(SEED_CRD_ENTITIES) == 5

    def test_entities_have_7_fields(self):
        for ent in SEED_CRD_ENTITIES:
            assert len(ent) == 7

    def test_all_have_entity_names(self):
        for ent in SEED_CRD_ENTITIES:
            assert ent[1]  # entity_name

    def test_all_cumple_crd(self):
        for ent in SEED_CRD_ENTITIES:
            assert ent[6] == "active"

class TestFetchEurlexText:
    def test_fetch_success(self):
        mock_data = {
            "title": "Directive 2019/879",
            "html": "<h1>Article 468</h1><p>Own funds requirements</p>"
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        with patch("crd_brrd_emir.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(CRD_BRRD_NORMAS[0])
        assert result is not None

    def test_fetch_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("crd_brrd_emir.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(CRD_BRRD_NORMAS[0])
        assert result is None

    def test_fetch_request_error(self):
        import httpx
        with patch("crd_brrd_emir.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.side_effect = httpx.RequestError("Connection failed")
            result = _fetch_eurlex_text(CRD_BRRD_NORMAS[0])
        assert result is None
