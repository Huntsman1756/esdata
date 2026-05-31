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
                DELETE FROM documento_empresa
                WHERE documento_id IN (
                    SELECT id FROM documento_interpretativo
                    WHERE referencia = 'BORME-A-2026-88-02'
                )
                """
            )
        )
        db.execute(
            text("DELETE FROM empresa WHERE nombre = 'ALDITRAEX SOCIEDAD LIMITADA'")
        )
        db.execute(
            text(
                "DELETE FROM documento_interpretativo WHERE referencia = 'BORME-A-2026-88-02'"
            )
        )
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
                """
            )
        )
        db.execute(
            text(
                """
                INSERT INTO empresa (nombre, nif, domicilio, fuente_inicial)
                VALUES ('ALDITRAEX SOCIEDAD LIMITADA', NULL, 'C SANTA LUCIA 19', 'BORME')
                """
            )
        )
        db.execute(
            text(
                """
                INSERT INTO documento_empresa (documento_id, empresa_id, rol, confianza_extraccion, nota)
                SELECT d.id, e.id, 'principal', 0.85, 'Extraccion heuristica desde BORME'
                FROM documento_interpretativo d
                JOIN empresa e ON e.nombre = 'ALDITRAEX SOCIEDAD LIMITADA'
                WHERE d.referencia = 'BORME-A-2026-88-02'
                ON CONFLICT (documento_id, empresa_id) DO UPDATE SET
                    rol = excluded.rol,
                    confianza_extraccion = excluded.confianza_extraccion,
                    nota = excluded.nota
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


@pytest.mark.asyncio
async def test_borme_list_filters_by_related_company():
    _seed_borme()

    async with _client() as c:
        match = await c.get("/v1/borme", params={"empresa": "ALDITRAEX", "limit": 10})
        miss = await c.get("/v1/borme", params={"empresa": "NO EXISTE", "limit": 10})

    assert match.status_code == 200
    assert match.json()["total"] >= 1
    assert match.json()["actos"][0]["referencia"] == "BORME-A-2026-88-02"
    assert miss.status_code == 200
    assert miss.json()["total"] == 0
