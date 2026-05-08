"""Tests for SFDR worker - Fase 46.7."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sfdr import (
    SFDR_NORMAS,
    SEED_SFDR_FUNDS,
    _fetch_eurlex_text,
)

class TestSFDRNormas:
    def test_has_3_normas(self):
        assert len(SFDR_NORMAS) == 3

    def test_normas_have_required_fields(self):
        required = ["codigo", "boe_id", "tipo_documento", "titulo", "ambito", "regulacion"]
        for norma in SFDR_NORMAS:
            for field in required:
                assert field in norma

    def test_normas_have_celex_ids(self):
        for norma in SFDR_NORMAS:
            assert norma["boe_id"].startswith("EUR-CELEX-")

    def test_normas_are_sfdr_related(self):
        for norma in SFDR_NORMAS:
            assert norma["regulacion"] == "sfdr"

class TestSeedFunds:
    def test_has_5_funds(self):
        assert len(SEED_SFDR_FUNDS) == 5

    def test_funds_have_7_fields(self):
        for fund in SEED_SFDR_FUNDS:
            assert len(fund) == 7

    def test_all_have_fund_names(self):
        for fund in SEED_SFDR_FUNDS:
            assert fund[1]  # fund_name

    def test_all_active(self):
        for fund in SEED_SFDR_FUNDS:
            assert fund[6] == "active"

class TestFetchEurlexText:
    def test_fetch_success(self):
        mock_data = {
            "title": "Regulation 2019/2088",
            "html": "<h1>Article 5</h1><p>Principal adverse impact</p>"
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        with patch("sfdr.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(SFDR_NORMAS[0])
        assert result is not None

    def test_fetch_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("sfdr.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(SFDR_NORMAS[0])
        assert result is None

    def test_fetch_request_error(self):
        import httpx
        with patch("sfdr.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.side_effect = httpx.RequestError("Connection failed")
            result = _fetch_eurlex_text(SFDR_NORMAS[0])
        assert result is None
