"""Tests for Consumer Credit real worker - Fase 46.5."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from consumer_credit_real import (
    CONSUMER_CREDIT_NORMAS,
    _fetch_eurlex_text,
)


class TestConsumerCreditNormas:
    """Test consumer credit normas structure."""

    def test_has_4_normas(self):
        assert len(CONSUMER_CREDIT_NORMAS) == 4

    def test_normas_have_required_fields(self):
        required = ["codigo", "boe_id", "tipo_documento", "titulo", "ambito", "regulacion"]
        for norma in CONSUMER_CREDIT_NORMAS:
            for field in required:
                assert field in norma, f"Missing field {field} in {norma.get('codigo', 'unknown')}"

    def test_normas_have_celex_ids(self):
        """Test that all normas have valid CELEX IDs."""
        for norma in CONSUMER_CREDIT_NORMAS:
            assert norma["boe_id"].startswith("EUR-CELEX-"), f"Invalid CELEX: {norma['boe_id']}"

    def test_normas_are_directives_and_regulations(self):
        """Test that normas cover both directives and regulations."""
        tipos = set(n["tipo_documento"] for n in CONSUMER_CREDIT_NORMAS)
        assert "directiva" in tipos
        assert "reglamento" in tipos

    def test_normas_are_consumer_credit_related(self):
        """Test that all normas are related to consumer credit."""
        for norma in CONSUMER_CREDIT_NORMAS:
            assert norma["regulacion"] == "consumer_credit"

    def test_normas_have_eli_uris(self):
        """Test that all normas have ELI URIs."""
        for norma in CONSUMER_CREDIT_NORMAS:
            assert norma["eli_uri"].startswith("https://eur-lex.europa.eu/eli/")


class TestFetchEurlexText:
    """Test EUR-Lex text fetching."""

    def test_fetch_success(self):
        """Test successful EUR-Lex fetch."""
        mock_data = {
            "title": "Directive 2008/48/EC",
            "html": "<h1>Article 1</h1><p>Consumer credit definition</p><h1>Article 2</h1><p>Scope</p>"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        
        with patch("consumer_credit_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            
            result = _fetch_eurlex_text(CONSUMER_CREDIT_NORMAS[0])
        
        assert result is not None
        title, text = result
        assert "Article 1" in text
        assert "Consumer credit definition" in text
        assert "Article 2" in text

    def test_fetch_http_error(self):
        """Test HTTP error returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch("consumer_credit_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            
            result = _fetch_eurlex_text(CONSUMER_CREDIT_NORMAS[0])
        
        # Falls through to fallback search which also fails
        assert result is None

    def test_fetch_request_error(self):
        """Test request error returns None."""
        import httpx
        
        with patch("consumer_credit_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.side_effect = httpx.RequestError("Connection failed")
            
            result = _fetch_eurlex_text(CONSUMER_CREDIT_NORMAS[0])
        
        assert result is None

    def test_fetch_invalid_json(self):
        """Test invalid JSON falls back to search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "<html>test</html>"
        
        with patch("consumer_credit_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            
            result = _fetch_eurlex_text(CONSUMER_CREDIT_NORMAS[0])
        
        # Falls through to fallback search
        assert result is not None
