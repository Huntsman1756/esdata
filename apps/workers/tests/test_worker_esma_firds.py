"""Tests for ESMA FIRDS metadata-only loader."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import worker_esma_firds
from worker_esma_firds import FIRDS_SOLR_URL, search_dltins_files


def test_worker_esma_firds_is_metadata_only():
    source = Path(worker_esma_firds.__file__).read_text(encoding="utf-8")

    for forbidden in (
        "download_zip",
        "parse_dltins_instruments",
        "esma_firds_instrument",
        "response.content",
        "zipfile",
        "FinInstrm",
    ):
        assert forbidden not in source

    assert "metadata_only" in source
    assert "articulos=0" in source


def test_search_dltins_files_reads_solr_metadata_without_payload_download(monkeypatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "response": {
                    "docs": [
                        {
                            "publication_date": "2026-06-04T00:00:00Z",
                            "download_link": "https://firds.esma.europa.eu/firds/DLTINS_20260603_02of02.zip",
                            "file_name": "DLTINS_20260603_02of02.zip",
                            "file_type": "DLTINS",
                            "checksum": "abc123",
                        }
                    ]
                }
            }

    def fake_get(url: str, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return FakeResponse()

    monkeypatch.setattr(worker_esma_firds.httpx, "get", fake_get)

    files = search_dltins_files(days=1)

    assert captured["url"] == FIRDS_SOLR_URL
    assert captured["kwargs"]["params"]["fq"][1] == "file_type:DLTINS"
    assert files[0].file_name == "DLTINS_20260603_02of02.zip"
    assert files[0].checksum == "abc123"
