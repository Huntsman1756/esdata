"""Tests for GIIN worker - Fase 46.2."""

import csv
import io
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giin import discover_latest_irs_csv_zip, fetch_giin_csv, fetch_giin_zip


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
        assert result[0]["estado_fatca"] == "activo"
        assert result[1]["giin"] == "AESA01.9999.99.99.99"
        assert result[1]["estado_fatca"] == "inactivo"

    def test_fetch_zip_success_parses_current_irs_headers(self):
        """Test current IRS ZIP CSV headers: GIIN, FINm, CountryNm."""
        csv_content = "GIIN,FINm,CountryNm\n"
        csv_content += "88QF1F.99999.SL.136,\"Orchid Asia IV, L.P.\",CAYMAN ISLANDS\n"
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zipped:
            zipped.writestr("FATCA Foreign Financial Institution.csv", csv_content)

        with patch("giin.urlopen", return_value=MockResponse(buffer.getvalue())):
            result, source_url = fetch_giin_zip("https://www.irs.gov/pub/fatca/current.zip")

        assert source_url == "https://www.irs.gov/pub/fatca/current.zip"
        assert len(result) == 1
        assert result[0]["giin"] == "88QF1F.99999.SL.136"
        assert result[0]["entidad_nombre"] == "Orchid Asia IV, L.P."
        assert result[0]["entidad_pais"] == "CAYMAN ISLANDS"
        assert result[0]["tipo_entidad"] == "FFI"
        assert result[0]["estado_fatca"] == "activo"

    def test_discover_latest_csv_zip_from_official_listing(self):
        html = (
            '<a href="/pub/fatca/fatca-foreign-financial-institution-ffi-april-2026-csv.zip">'
            "CSV</a>"
        )

        with patch("giin.urlopen", return_value=MockResponse(html.encode("utf-8"))):
            result = discover_latest_irs_csv_zip("https://www.irs.gov/downloads/fatca")

        assert result == "https://www.irs.gov/pub/fatca/fatca-foreign-financial-institution-ffi-april-2026-csv.zip"

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


class TestGIINWorker:
    """Integration tests for GIIN worker."""

    def test_run_once_with_mock_db(self):
        """Test run_once with mocked database."""
        from giin import run_sync

        engine = create_engine(
            "sqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE giin_registry (
                    giin TEXT PRIMARY KEY,
                    entidad_nombre TEXT NOT NULL,
                    entidad_pais TEXT NOT NULL,
                    tipo_entidad TEXT NOT NULL,
                    estado_fatca TEXT NOT NULL,
                    fecha_registro TEXT,
                    fecha_expiracion TEXT,
                    es_exempt_beneficial_owner BOOLEAN NOT NULL,
                    es_sponsored_ffo BOOLEAN NOT NULL,
                    nota TEXT,
                    actualizado_en TEXT
                )
            """))

        rows = [
            {
                "giin": "AA9079.99999.99.99.999",
                "entidad_nombre": "ABN AMRO BANK N.V.",
                "entidad_pais": "NL",
                "tipo_entidad": "FFI",
                "estado_fatca": "activo",
                "es_exempt_beneficial_owner": False,
                "es_sponsored_ffo": False,
                "fecha_registro": None,
                "fecha_expiracion": None,
                "nota": None,
            }
        ]
        with (
            patch("giin.create_engine", return_value=engine),
            patch("giin.fetch_giin_zip", return_value=(rows, "https://www.irs.gov/pub/fatca/current.zip")),
        ):
            result = run_sync(worker_name="test-giin")

        assert result["processed"] == 1
        assert result["source"] == "irs_fatca_ffi_csv_zip"
        assert result["source_url"] == "https://www.irs.gov/pub/fatca/current.zip"
        assert result["worker"] == "test-giin"
        assert "started_at" in result
