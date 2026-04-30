"""Tests for Screening Real worker - Fase 46.1."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from screening_real import (
    fetch_ofac_sdn,
    fetch_un_consolidated,
    fetch_eu_sanctions,
    SEED_LISTS,
    SEED_ENTRIES,
    _normalize_name,
)


class MockResponse:
    """Mock HTTP response for urlopen."""
    def __init__(self, content):
        self.content = content
    
    def read(self):
        return self.content


class TestNormalizeName:
    """Test name normalization."""

    def test_basic_normalization(self):
        assert _normalize_name("John Doe") == "john doe"

    def test_special_chars(self):
        assert _normalize_name("AL-RASHID") == "al rashid"

    def test_underscores(self):
        assert _normalize_name("GLOBAL_Finance") == "global finance"

    def test_accents(self):
        result = _normalize_name("Jose Luis Mendez")
        assert "jose" in result and "luis" in result and "mendez" in result

    def test_empty_string(self):
        assert _normalize_name("") == ""

    def test_uppercase(self):
        assert _normalize_name("TEST COMPANY") == "test company"


class TestFetchOFACSDN:
    """Test OFAC SDN fetching."""

    def test_fetch_success(self):
        """Test successful OFAC JSON parsing."""
        sdn_data = {
            "sdn_list": [
                {
                    "uid": 1,
                    "id": "25001",
                    "name": "AL-RASHID TRADING COMPANY",
                    "type": "Entity",
                    "country": "SY",
                    "title": "Proliferation activities",
                    "effective_date": "2024-06-15T00:00:00",
                    "program": "SYRIA",
                    "executive_order": "13582",
                    "aka_list": ["RASHID TRADING", "RASHID CO"],
                }
            ]
        }
        
        with patch("screening_real.urlopen", return_value=MockResponse(json.dumps(sdn_data).encode("utf-8"))):
            result = fetch_ofac_sdn(["https://test.example.com/sdn.json"])
        
        assert result is not None
        assert len(result) == 1
        assert result[0]["list_id"] == "OFAC_SDN"
        assert result[0]["entidad_id"] == "OFAC-25001"
        assert result[0]["nombre"] == "AL-RASHID TRADING COMPANY"
        assert result[0]["tipo_entidad"] == "entity"
        assert result[0]["pais"] == "SY"
        assert result[0]["activo"] is True

    def test_fetch_empty_list(self):
        """Test empty OFAC list returns None."""
        sdn_data = {"sdn_list": []}
        
        with patch("screening_real.urlopen", return_value=MockResponse(json.dumps(sdn_data).encode("utf-8"))):
            result = fetch_ofac_sdn(["https://test.example.com/sdn.json"])
        
        assert result is None

    def test_fetch_urlopen_error(self):
        """Test network error returns None."""
        from urllib.error import URLError
        
        with patch("screening_real.urlopen", side_effect=URLError("Connection refused")):
            result = fetch_ofac_sdn(["https://test.example.com/sdn.json"])
        
        assert result is None

    def test_fetch_invalid_json(self):
        """Test invalid JSON returns None."""
        with patch("screening_real.urlopen", return_value=MockResponse(b"not json")):
            result = fetch_ofac_sdn(["https://test.example.com/sdn.json"])
        
        assert result is None

    def test_fetch_deceased_person(self):
        """Test that deceased persons are marked inactive."""
        sdn_data = {
            "sdn_list": [
                {
                    "id": "25002",
                    "name": "DECEASED PERSON",
                    "type": "Deceased",
                    "country": "IR",
                }
            ]
        }
        
        with patch("screening_real.urlopen", return_value=MockResponse(json.dumps(sdn_data).encode("utf-8"))):
            result = fetch_ofac_sdn(["https://test.example.com/sdn.json"])
        
        assert result is not None
        assert result[0]["activo"] is False


class TestFetchUNConsolidated:
    """Test UN Consolidated List fetching."""

    def test_fetch_success(self):
        """Test successful UN JSON parsing."""
        un_data = {
            "list": [
                {
                    "id": "40001",
                    "name": "AHMED AL-MANSOUR",
                    "type": "Individual",
                    "country_code": "YE",
                    "date_of_birth": "1965-03-20T00:00:00",
                    "summary": "Arms trafficking",
                    "date_listed": "2023-12-01T00:00:00",
                    "resolution": "1718",
                    "aliases": ["A. AL-MANSOUR"],
                }
            ]
        }
        
        with patch("screening_real.urlopen", return_value=MockResponse(json.dumps(un_data).encode("utf-8"))):
            result = fetch_un_consolidated(["https://test.example.com/consolidated.json"])
        
        assert result is not None
        assert len(result) == 1
        assert result[0]["list_id"] == "UN_SANCTIONS"
        assert result[0]["entidad_id"] == "UN-40001"
        assert result[0]["tipo_entidad"] == "person"
        assert result[0]["pais"] == "YE"
        assert result[0]["fecha_nacimiento"] == "1965-03-20"
        assert result[0]["metadata_json"]["resolution"] == "1718"

    def test_fetch_empty_list(self):
        """Test empty UN list returns None."""
        un_data = {"list": []}
        
        with patch("screening_real.urlopen", return_value=MockResponse(json.dumps(un_data).encode("utf-8"))):
            result = fetch_un_consolidated(["https://test.example.com/consolidated.json"])
        
        assert result is None

    def test_fetch_urlopen_error(self):
        """Test network error returns None."""
        from urllib.error import URLError
        
        with patch("screening_real.urlopen", side_effect=URLError("Timeout")):
            result = fetch_un_consolidated(["https://test.example.com/consolidated.json"])
        
        assert result is None


class TestFetchEUSanctions:
    """Test EU Sanctions fetching."""

    def test_fetch_success(self):
        """Test successful EU HTML scraping."""
        html = """
        <table>
            <tr>
                <td>BELARUS INDUSTRIAL GROUP</td>
                <td>Entity supporting the Belarusian regime</td>
            </tr>
            <tr>
                <td>DONBAS ENERGY SOLUTIONS</td>
                <td>Energy company in occupied territories</td>
            </tr>
        </table>
        """
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        
        with patch("screening_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            
            result = fetch_eu_sanctions(["https://test.example.com/"])
        
        assert result is not None
        assert len(result) == 2
        assert result[0]["list_id"] == "EU_SANCTIONS"
        assert result[0]["nombre"] == "BELARUS INDUSTRIAL GROUP"
        assert result[0]["categorias"] == ["sanctions", "eu"]

    def test_fetch_http_error(self):
        """Test HTTP error returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch("screening_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            
            result = fetch_eu_sanctions(["https://test.example.com/"])
        
        assert result is None

    def test_fetch_request_error(self):
        """Test request error returns None."""
        import httpx
        
        with patch("screening_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.side_effect = httpx.RequestError("Connection failed")
            
            result = fetch_eu_sanctions(["https://test.example.com/"])
        
        assert result is None

    def test_fetch_empty_table(self):
        """Test empty HTML table returns None."""
        html = "<table></table>"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        
        with patch("screening_real.httpx.Client") as mock_client:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = ctx
            ctx.get.return_value = mock_response
            
            result = fetch_eu_sanctions(["https://test.example.com/"])
        
        assert result is None


class TestSeedData:
    """Test seed data structure."""

    def test_seed_lists_count(self):
        assert len(SEED_LISTS) == 5

    def test_seed_lists_have_required_fields(self):
        required = ["codigo", "nombre", "tipo", "organismo", "pais", "url_fuente", "descripcion", "actualizada", "activo"]
        for list_data in SEED_LISTS:
            for field in required:
                assert field in list_data, f"Missing field {field} in list {list_data.get('codigo', 'unknown')}"

    def test_seed_entries_count(self):
        assert len(SEED_ENTRIES) == 14

    def test_seed_entries_have_required_fields(self):
        required = ["list_id", "entidad_id", "nombre", "tipo_entidad", "pais", "categorias", "activo"]
        for entry in SEED_ENTRIES:
            for field in required:
                assert field in entry, f"Missing field {field} in entry {entry.get('entidad_id', 'unknown')}"

    def test_seed_entries_cover_all_lists(self):
        """Test that seed entries cover all 5 lists."""
        list_codes = set(e["list_id"] for e in SEED_ENTRIES)
        expected = {"OFAC_SDN", "EU_SANCTIONS", "UN_SANCTIONS", "SEPBLAC", "ES_PEPS"}
        assert list_codes == expected

    def test_seed_entry_ids_are_unique(self):
        """Test that all entidad_id values are unique."""
        ids = [e["entidad_id"] for e in SEED_ENTRIES]
        assert len(ids) == len(set(ids)), "Duplicate entidad_id values in seed data"

    def test_seed_entry_types(self):
        """Test that entity types are valid."""
        valid_types = {"person", "entity", "vessel", "aircraft"}
        for entry in SEED_ENTRIES:
            assert entry["tipo_entidad"] in valid_types, f"Invalid tipo_entidad: {entry['tipo_entidad']}"

    def test_seed_list_types(self):
        """Test that list types are valid."""
        valid_types = {"sanctions", "pep", "watchlist"}
        for list_data in SEED_LISTS:
            assert list_data["tipo"] in valid_types, f"Invalid tipo: {list_data['tipo']}"


class TestScreeningRealWorker:
    """Integration tests for Screening Real worker."""

    def test_fetch_all_sources_fallback_to_seed(self):
        """Test that when all sources fail, we fall back to seed data."""
        from urllib.error import URLError
        
        def mock_urlopen(*args, **kwargs):
            raise URLError("All sources down")
        
        with patch("screening_real.urlopen", side_effect=mock_urlopen):
            with patch("screening_real.httpx.Client") as mock_client:
                ctx = MagicMock()
                ctx.__enter__ = MagicMock(return_value=ctx)
                ctx.__exit__ = MagicMock(return_value=None)
                mock_client.return_value = ctx
                ctx.get.side_effect = Exception("No network")
                
                # Verify that individual fetchers return None
                assert fetch_ofac_sdn() is None
                assert fetch_un_consolidated() is None
                assert fetch_eu_sanctions() is None
        
        # Seed data should be used as fallback
        assert len(SEED_ENTRIES) == 14
        assert len(SEED_LISTS) == 5

    def test_ofac_fetch_returns_entries(self):
        """Test that OFAC fetch returns properly structured entries."""
        sdn_data = {
            "sdn_list": [
                {
                    "id": "25001",
                    "name": "TEST ENTITY",
                    "type": "Entity",
                    "country": "SY",
                }
            ]
        }
        
        with patch("screening_real.urlopen", return_value=MockResponse(json.dumps(sdn_data).encode("utf-8"))):
            result = fetch_ofac_sdn()
        
        assert result is not None
        assert len(result) == 1
        assert result[0]["list_id"] == "OFAC_SDN"
        assert result[0]["entidad_id"] == "OFAC-25001"
        assert result[0]["nombre"] == "TEST ENTITY"
