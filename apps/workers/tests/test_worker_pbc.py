"""Tests for PBC worker - Fase 46.11."""

# ruff: noqa: I001

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pbc import (
    PBC_NORMAS,
    SEED_PBC_ENTITIES,
    _fetch_eurlex_text,
)

class TestPBCNormas:
    def test_has_2_normas(self):
        assert len(PBC_NORMAS) == 2

    def test_normas_have_required_fields(self):
        required = ["codigo", "boe_id", "tipo_documento", "titulo", "ambito", "regulacion"]
        for norma in PBC_NORMAS:
            for field in required:
                assert field in norma

    def test_normas_have_celex_ids(self):
        for norma in PBC_NORMAS:
            assert norma["boe_id"].startswith("EUR-CELEX-")

    def test_normas_are_pbc_related(self):
        for norma in PBC_NORMAS:
            assert norma["regulacion"] == "pbc"

    def test_normas_use_validated_celex_ids(self):
        normas_by_codigo = {norma["codigo"]: norma for norma in PBC_NORMAS}

        assert normas_by_codigo["PBC_CRD_V_2019_879"]["boe_id"] == "EUR-CELEX-32019L0878"
        assert normas_by_codigo["PBC_CRR_II_2019_2057"]["boe_id"] == "EUR-CELEX-32019R0876"

class TestSeedEntities:
    def test_has_4_entities(self):
        assert len(SEED_PBC_ENTITIES) == 4

    def test_entities_have_7_fields(self):
        for ent in SEED_PBC_ENTITIES:
            assert len(ent) == 7

    def test_all_have_entity_names(self):
        for ent in SEED_PBC_ENTITIES:
            assert ent[1]  # entity_name

    def test_all_active(self):
        for ent in SEED_PBC_ENTITIES:
            assert ent[6] == "active"

class TestFetchEurlexText:
    def test_fetch_success(self):
        mock_data = {
            "title": "Directive 2019/879",
            "html": "<h1>Article 468</h1><p>Capital buffer</p>"
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        with patch("pbc.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(PBC_NORMAS[0])
        assert result is not None

    def test_fetch_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("pbc.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(PBC_NORMAS[0])
        assert result is None

    def test_fetch_request_error(self):
        import httpx
        with patch("pbc.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.side_effect = httpx.RequestError("Connection failed")
            result = _fetch_eurlex_text(PBC_NORMAS[0])
        assert result is None
