"""Tests for IDD/Solvency II worker - Fase 46.12."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from insurance import (
    IDD_NORMAS,
    SEED_IDD_DISTRIBUTORS,
    SEED_IDD_PRODUCTS,
    SEED_SOLVENCY_ENTITIES,
    SEED_SOLVENCY_SFP,
    _fetch_eurlex_text,
)

class TestIDDNormas:
    def test_has_2_normas(self):
        assert len(IDD_NORMAS) == 2

    def test_normas_have_required_fields(self):
        required = ["codigo", "boe_id", "tipo_documento", "titulo", "ambito", "regulacion"]
        for norma in IDD_NORMAS:
            for field in required:
                assert field in norma

    def test_normas_have_celex_ids(self):
        for norma in IDD_NORMAS:
            assert norma["boe_id"].startswith("EUR-CELEX-")

    def test_normas_are_directives(self):
        for norma in IDD_NORMAS:
            assert norma["tipo_documento"] == "directiva"

    def test_normas_are_idd_related(self):
        for norma in IDD_NORMAS:
            assert norma["regulacion"] == "idd"

class TestSeedDistributors:
    def test_has_6_distributors(self):
        assert len(SEED_IDD_DISTRIBUTORS) == 6

    def test_distributors_have_7_fields(self):
        for dist in SEED_IDD_DISTRIBUTORS:
            assert len(dist) == 7

    def test_all_active(self):
        for dist in SEED_IDD_DISTRIBUTORS:
            assert dist[6] == "active"

class TestSeedProducts:
    def test_has_4_products(self):
        assert len(SEED_IDD_PRODUCTS) == 4

    def test_products_have_8_fields(self):
        for prod in SEED_IDD_PRODUCTS:
            assert len(prod) == 8

class TestSeedSolvencyEntities:
    def test_has_4_entities(self):
        assert len(SEED_SOLVENCY_ENTITIES) == 4

    def test_entities_have_7_fields(self):
        for ent in SEED_SOLVENCY_ENTITIES:
            assert len(ent) == 7

class TestSeedSolvencySFP:
    def test_has_3_sfp(self):
        assert len(SEED_SOLVENCY_SFP) == 3

    def test_sfp_have_6_fields(self):
        for sfp in SEED_SOLVENCY_SFP:
            assert len(sfp) == 6

class TestFetchEurlexText:
    def test_fetch_success(self):
        mock_data = {
            "title": "Directive 2016/97/EU",
            "html": "<h1>Article 1</h1><p>Scope and definitions</p>"
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        with patch("insurance.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(IDD_NORMAS[0])
        assert result is not None

    def test_fetch_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("insurance.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(IDD_NORMAS[0])
        assert result is None

    def test_fetch_request_error(self):
        import httpx
        with patch("insurance.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.side_effect = httpx.RequestError("Connection failed")
            result = _fetch_eurlex_text(IDD_NORMAS[0])
        assert result is None
