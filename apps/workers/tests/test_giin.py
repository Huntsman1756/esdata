"""Tests for GIIN worker - Fase 46.2."""

import csv
import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giin import fetch_giin_csv, SEED_GIIN


class MockResponse:
    """Mock HTTP response for urlopen."""
    def __init__(self, content):
        self.content = content
    
    def read(self):
        return self.content


class TestFetchGIINCSV:
    """Test CSV fetching from IRS."""

    def test_fetch_success_parses_csv(self):
        """Test that a valid CSV response is parsed correctly."""
        csv_content = "GIIN,Legal Name,Country,Type,Status\n"
        csv_content += "AA9079.99999.99.99.999,ABN AMRO BANK N.V.,NL,Bank,Active\n"
        csv_content += "AESA01.9999.99.99.99,BANCO DE LA NACION ARGENTINA,AR,Bank,Inactive\n"
        
        with patch("giin.urlopen", return_value=MockResponse(csv_content.encode("utf-8-sig"))):
            result = fetch_giin_csv(["https://test.example.com/giin.csv"])
        
        assert result is not None
        assert len(result) == 2
        assert result[0]["giin"] == "AA9079.99999.99.99.999"
        assert result[0]["entidad_nombre"] == "ABN AMRO BANK N.V."
        assert result[0]["entidad_pais"] == "NL"
        assert result[0]["estado_fatca"] == "active"
        assert result[1]["giin"] == "AESA01.9999.99.99.99"
        assert result[1]["estado_fatca"] == "inactive"

    def test_fetch_empty_csv_returns_none(self):
        """Test that an empty CSV returns None."""
        mock = MockResponse(b"GIIN,Legal Name,Country\n")
        
        with patch("giin.urlopen", return_value=mock):
            result = fetch_giin_csv(["https://test.example.com/giin.csv"])
        
        assert result is None

    def test_fetch_urlopen_error_returns_none(self):
        """Test that network errors return None."""
        from urllib.error import URLError
        
        with patch("giin.urlopen", side_effect=URLError("Connection refused")):
            result = fetch_giin_csv(["https://test.example.com/giin.csv"])
        
        assert result is None

    def test_fetch_multiple_urls_fallback(self):
        """Test that it tries multiple URLs and uses the first successful one."""
        csv_content = "GIIN,Legal Name,Country,Type,Status\n"
        csv_content += "AA9079.99999.99.99.999,TEST BANK,NL,Bank,Active\n"
        
        from urllib.error import URLError
        
        def side_effect(url, *args, **kwargs):
            if "fail" in url:
                raise URLError("Timeout")
            return MockResponse(csv_content.encode("utf-8-sig"))
        
        with patch("giin.urlopen", side_effect=side_effect):
            result = fetch_giin_csv(["https://fail.example.com", "https://success.example.com"])
        
        assert result is not None
        assert len(result) == 1
        assert result[0]["giin"] == "AA9079.99999.99.99.999"

    def test_fetch_bom_encoding(self):
        """Test that UTF-8 BOM is handled correctly."""
        csv_content = "\ufeffGIIN,Legal Name,Country,Type,Status\n"
        csv_content += "AA9079.99999.99.99.999,TEST BANK,NL,Bank,Active\n"
        
        with patch("giin.urlopen", return_value=MockResponse(csv_content.encode("utf-8"))):
            result = fetch_giin_csv(["https://test.example.com/giin.csv"])
        
        assert result is not None
        assert result[0]["giin"] == "AA9079.99999.99.99.999"


class TestSeedGIIN:
    """Test seed data structure."""

    def test_seed_has_required_fields(self):
        """Test that all seed entries have required fields."""
        required = ["giin", "entidad_nombre", "entidad_pais", "tipo_entidad", 
                    "estado_fatca", "es_exempt_beneficial_owner", "es_sponsored_ffo"]
        
        for entry in SEED_GIIN:
            for field in required:
                assert field in entry, f"Missing field {field} in entry {entry.get('giin', 'unknown')}"

    def test_seed_giin_values_are_unique(self):
        """Test that all GIIN values are unique."""
        giins = [e["giin"] for e in SEED_GIIN]
        assert len(giins) == len(set(giins)), "Duplicate GIIN values in seed data"

    def test_seed_has_15_entries(self):
        """Test that seed data has 15 entries."""
        assert len(SEED_GIIN) == 15

    def test_seed_countries_represented(self):
        """Test that seed data covers multiple countries."""
        countries = set(e["entidad_pais"] for e in SEED_GIIN)
        assert len(countries) > 5, "Seed should cover multiple countries"


class TestGIINWorker:
    """Integration tests for GIIN worker."""

    def test_run_once_with_mock_db(self):
        """Test run_once with mocked database."""
        from giin import run_sync
        
        result = run_sync(worker_name="test-giin")
        
        assert result["processed"] == 15
        assert result["source"] == "seed"
        assert result["worker"] == "test-giin"
        assert "started_at" in result
