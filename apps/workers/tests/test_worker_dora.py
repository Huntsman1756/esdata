"""Tests for DORA worker - Fase 46.6."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dora import (
    DORA_NORMAS,
    SEED_DORA_PROVIDERS,
    _fetch_eurlex_text,
)

class TestDORANormas:
    def test_has_1_norma(self):
        assert len(DORA_NORMAS) == 1

    def test_normas_have_required_fields(self):
        required = ["codigo", "boe_id", "tipo_documento", "titulo", "ambito", "regulacion"]
        for norma in DORA_NORMAS:
            for field in required:
                assert field in norma

    def test_normas_have_celex_ids(self):
        for norma in DORA_NORMAS:
            assert norma["boe_id"].startswith("EUR-CELEX-")

    def test_normas_are_regulation(self):
        for norma in DORA_NORMAS:
            assert norma["tipo_documento"] == "reglamento"

    def test_normas_are_dora_related(self):
        for norma in DORA_NORMAS:
            assert norma["regulacion"] == "dora"

class TestSeedProviders:
    def test_has_5_providers(self):
        assert len(SEED_DORA_PROVIDERS) == 5

    def test_providers_have_8_fields(self):
        for prov in SEED_DORA_PROVIDERS:
            assert len(prov) == 8

    def test_all_have_provider_names(self):
        for prov in SEED_DORA_PROVIDERS:
            assert prov[0]  # provider_name

    def test_all_active(self):
        for prov in SEED_DORA_PROVIDERS:
            assert prov[7] == "active"

class TestFetchEurlexText:
    def test_fetch_success(self):
        mock_data = {
            "title": "Regulation 2022/2535",
            "html": "<h1>Article 4</h1><p>Digital operational resilience</p>"
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        with patch("dora.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(DORA_NORMAS[0])
        assert result is not None

    def test_fetch_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("dora.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            result = _fetch_eurlex_text(DORA_NORMAS[0])
        assert result is None

    def test_fetch_request_error(self):
        import httpx
        with patch("dora.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.side_effect = httpx.RequestError("Connection failed")
            result = _fetch_eurlex_text(DORA_NORMAS[0])
        assert result is None
