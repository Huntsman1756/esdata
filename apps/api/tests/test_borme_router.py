import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import db_session
from main import app


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _seed_borme():
    with db_session() as db:
        db.execute(
            text(
                """
                INSERT INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                    ambito, referencia, fecha, titulo, texto, url_fuente,
                    row_completeness, row_provenance
                )
                VALUES (
                    'cambio_domicilio', 'BORME', 'es', 'borme',
                    'mercantil', 'BORME-A-2026-88-02', '2026-05-11',
                    'Actos de TEST del BORME num. 88',
                    'Texto oficial BORME con extraccion societaria heuristica.',
                    'https://www.boe.es/borme/dias/2026/05/11/pdfs/BORME-A-2026-88-02.pdf',
                    'partial', 'official_best_effort'
                )
                ON CONFLICT (referencia) DO UPDATE SET
                    texto = excluded.texto,
                    tipo_fuente = excluded.tipo_fuente,
                    row_completeness = excluded.row_completeness,
                    row_provenance = excluded.row_provenance
                """
            )
        )
        db.commit()


@pytest.mark.asyncio
async def test_borme_list_and_detail_expose_partial_heuristic_quality():
    _seed_borme()

    async with _client() as c:
        listing = await c.get("/v1/borme", params={"q": "TEST", "limit": 1})
        detail = await c.get("/v1/borme/BORME-A-2026-88-02")

    assert listing.status_code == 200
    listing_data = listing.json()
    assert listing_data["quality_signal"] == "partial_heuristic"
    item = listing_data["actos"][0]
    assert item["referencia"] == "BORME-A-2026-88-02"
    assert item["row_completeness"] == "partial"
    assert item["row_provenance"] == "official_best_effort"
    assert item["quality_signal"] == "partial_heuristic"

    assert detail.status_code == 200
    detail_data = detail.json()
    assert detail_data["row_completeness"] == "partial"
    assert detail_data["row_provenance"] == "official_best_effort"
    assert detail_data["quality_signal"] == "partial_heuristic"
