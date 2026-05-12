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


def _seed_boe_diario():
    with db_session() as db:
        db.execute(
            text(
                """
                INSERT INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                    ambito, referencia, fecha, titulo, texto, url_fuente,
                    row_completeness, row_provenance, metadata
                )
                VALUES (
                    'anuncio_boe', 'BOE', 'es', 'boe_diario',
                    'boe_diario', 'BOE-B-2026-15000', '2026-05-11',
                    'FIGUERES', 'Texto oficial BOE diario', 
                    'https://www.boe.es/diario_boe/xml.php?id=BOE-B-2026-15000',
                    'complete', 'official_exact', '{"source_format":"boe_daily_xml"}'
                )
                ON CONFLICT (referencia) DO UPDATE SET
                    texto = excluded.texto,
                    tipo_fuente = excluded.tipo_fuente,
                    row_completeness = excluded.row_completeness
                """
            )
        )
        db.commit()


@pytest.mark.asyncio
async def test_boe_diario_list_and_detail_are_separate_from_boe_consolidado():
    _seed_boe_diario()

    async with _client() as c:
        listing = await c.get("/v1/boe-diario?limit=1")
        detail = await c.get("/v1/boe-diario/BOE-B-2026-15000")

    assert listing.status_code == 200
    item = listing.json()["documentos"][0]
    assert item["referencia"] == "BOE-B-2026-15000"
    assert item["row_completeness"] == "complete"
    assert item["row_provenance"] == "official_exact"

    assert detail.status_code == 200
    data = detail.json()
    assert data["referencia"] == "BOE-B-2026-15000"
    assert data["tipo_documento"] == "anuncio_boe"
    assert data["metadata"]["source_format"] == "boe_daily_xml"
