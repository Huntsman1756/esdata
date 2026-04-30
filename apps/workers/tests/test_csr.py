"""Tests for CSRD worker - Fase 46.8."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from csr import (
    CSRD_NORMAS,
    SEED_CSRD_COMPANIES,
    _fetch_eurlex_text,
)

class TestCSRDNormas:
    def test_has_3_normas(self):
        assert len(CSRD_NORMAS) == 3

    def test_normas_have_required_fields(self):
        required = ["codigo", "boe_id", "tipo_documento", "titulo", "ambito", "regulacion"]
        for norma in CSRD_NORMAS:
            for field in required:
                assert field in norma

    def test_normas_have_celex_ids(self):
        for norma in CSRD_NORMAS:
            assert norma["boe_id"].startswith("EUR-CELEX-")

    def test_normas_are_csrd_related(self):
        for norma in CSRD_NORMAS:
            assert norma["regulacion"] == "csrd"

class TestSeedCompanies:
    def test_has_7_companies(self):
        assert len(SEED_CSRD_COMPANIES) == 7

    def test_companies_have_7_fields(self):
        for comp in SEED_CSRD_COMPANIES:
            assert len(comp) == 7

    def test_all_have_company_names(self):
        for comp in SEED_CSRD_COMPANIES:
            assert comp[1]  # company_name

    def test_all_active(self):
        for comp in SEED_CSRD_COMPANIES:
            assert comp[6] == "active"

class TestFetchEurlexText:
    def test_fetch_success(self):
        mock_data = {
            "title": "Directive 2014/95/EU",
            "html": "<h1>Article 19</h1><p>Non-financial statement</p>"
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        with patch("csr.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(CSRD_NORMAS[0])
        assert result is not None

    def test_fetch_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("csr.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(CSRD_NORMAS[0])
        assert result is None

    def test_fetch_request_error(self):
        import httpx
        with patch("csr.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.side_effect = httpx.RequestError("Connection failed")
            result = _fetch_eurlex_text(CSRD_NORMAS[0])
        assert result is None
