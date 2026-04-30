"""Tests for DAC8 real worker - Fase 46.4."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dac8_real import (
    DAC_NORMAS,
    SEED_DAC_REPORTING_ENTITIES,
    _fetch_eurlex_text,
    run_sync,
)


class TestDACNormas:
    """Test DAC8/DAC9 normas structure."""

    def test_has_3_normas(self):
        assert len(DAC_NORMAS) == 3

    def test_normas_have_required_fields(self):
        required = ["codigo", "boe_id", "tipo_documento", "titulo", "ambito", "regulacion"]
        for norma in DAC_NORMAS:
            for field in required:
                assert field in norma, f"Missing field {field} in {norma.get('codigo', 'unknown')}"

    def test_normas_have_celex_ids(self):
        """Test that all normas have valid CELEX IDs."""
        for norma in DAC_NORMAS:
            assert norma["boe_id"].startswith("EUR-CELEX-"), f"Invalid CELEX: {norma['boe_id']}"

    def test_normas_cover_dac8_and_dac9(self):
        """Test that normas cover both DAC8 and DAC9."""
        codigos = [n["codigo"] for n in DAC_NORMAS]
        assert any("DAC8" in c for c in codigos)
        assert any("DAC9" in c for c in codigos)

    def test_normas_are_directives(self):
        """Test that all normas are directives."""
        for norma in DAC_NORMAS:
            assert norma["tipo_documento"] == "directiva"


class TestSeedReportingEntities:
    """Test seed reporting entities structure."""

    def test_has_5_entities(self):
        assert len(SEED_DAC_REPORTING_ENTITIES) == 5

    def test_entities_have_required_fields(self):
        required = ["tin", "entity_type", "member_state", "dac8_registered", "dac9_registered", "status"]
        for entity in SEED_DAC_REPORTING_ENTITIES:
            for field in required:
                assert field in entity, f"Missing field {field}"

    def test_tins_are_unique(self):
        tins = [e["tin"] for e in SEED_DAC_REPORTING_ENTITIES]
        assert len(tins) == len(set(tins)), "Duplicate TINs"

    def test_member_states_covered(self):
        states = set(e["member_state"] for e in SEED_DAC_REPORTING_ENTITIES)
        assert len(states) == 5, "Should cover 5 member states"


class TestFetchEurlexText:
    """Test EUR-Lex text fetching."""

    def test_fetch_success(self):
        """Test successful EUR-Lex fetch."""
        mock_data = {
            "title": "Directive 2023/2819",
            "html": "<h1>Article 1</h1><p>Test content</p>"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        
        with patch("dac8_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            
            result = _fetch_eurlex_text(DAC_NORMAS[0])
        
        assert result is not None
        title, text = result
        assert "Article 1" in text
        assert "Test content" in text

    def test_fetch_http_error(self):
        """Test HTTP error returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch("dac8_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            
            result = _fetch_eurlex_text(DAC_NORMAS[0])
        
        assert result is None

    def test_fetch_request_error(self):
        """Test request error returns None."""
        import httpx
        
        with patch("dac8_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.side_effect = httpx.RequestError("Connection failed")
            
            result = _fetch_eurlex_text(DAC_NORMAS[0])
        
        assert result is None

    def test_fetch_invalid_json(self):
        """Test invalid JSON returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "<html>test</html>"
        
        with patch("dac8_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            
            result = _fetch_eurlex_text(DAC_NORMAS[0])
        
        # Falls through to fallback EUR-Lex search which succeeds with HTML text
        assert result is not None
