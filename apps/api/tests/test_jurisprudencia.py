from pathlib import Path
import sys

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from .conftest import engine
from main import app


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_jurisprudencia_buscar_returns_sentencias_only():
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                    ambito, referencia, fecha, titulo, texto, url_fuente
                )
                VALUES (
                    'consulta_vinculante', 'DGT', 'es', 'dgt',
                    'fiscal', 'V9999-26', '2026-01-15',
                    'Consulta DGT', 'Resumen de doctrina sobre IVA.',
                    'https://example.invalid/dgt'
                )
                ON CONFLICT DO NOTHING
                """
            )
        )

    async with _client() as c:
        response = await c.get("/v1/jurisprudencia/buscar?q=IVA")

    assert response.status_code == 200
    data = response.json()
    referencias = [item["referencia"] for item in data["resultados"]]
    assert "ECLI:ES:TS:2024:2741" in referencias
    assert all(item["tipo_documento"] in {"sentencia_ts", "sentencia"} for item in data["resultados"])


@pytest.mark.asyncio
async def test_jurisprudencia_buscar_returns_one_row_per_sentencia_and_prefers_title_fragment():
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO articulo (norma_id, numero, titulo, tipo)
                SELECT id, '92', 'Tipos impositivos especiales', 'articulo'
                FROM norma WHERE codigo = 'LIVA'
                ON CONFLICT DO NOTHING
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
                SELECT d.id, a.id, 'manual', 0.8, 'fixture extra'
                FROM documento_interpretativo d
                JOIN articulo a ON a.numero = '92'
                JOIN norma n ON n.id = a.norma_id
                WHERE d.referencia = 'ECLI:ES:TS:2024:2741' AND n.codigo = 'LIVA'
                ON CONFLICT DO NOTHING
                """
            )
        )

    async with _client() as c:
        response = await c.get("/v1/jurisprudencia/buscar?q=STS+741%2F2024")

    assert response.status_code == 200
    data = response.json()
    assert len(data["resultados"]) == 1
    assert data["resultados"][0]["referencia"] == "ECLI:ES:TS:2024:2741"
    assert data["resultados"][0]["fragmento"] == "STS 741/2024 - IVA"


@pytest.mark.asyncio
async def test_jurisprudencia_buscar_prefers_referencia_fragment_before_text_prefix():
    async with _client() as c:
        response = await c.get("/v1/jurisprudencia/buscar?q=ECLI:ES:TS:2024:2741")

    assert response.status_code == 200
    data = response.json()
    assert len(data["resultados"]) == 1
    assert data["resultados"][0]["fragmento"] == "ECLI:ES:TS:2024:2741"


@pytest.mark.asyncio
async def test_jurisprudencia_detalle_accepts_ecli_path_and_returns_doctrina_only():
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                    ambito, referencia, fecha, titulo, texto, url_fuente
                )
                VALUES (
                    'consulta_vinculante', 'DGT', 'es', 'dgt',
                    'fiscal', 'V2222-26', '2026-01-20',
                    'Consulta DGT IVA', 'Doctrina relacionada con LIVA 91.',
                    'https://example.invalid/dgt-2222'
                )
                ON CONFLICT DO NOTHING
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                    ambito, referencia, fecha, titulo, texto, url_fuente
                )
                VALUES (
                    'sentencia_an', 'AN', 'es', 'cendoj',
                    'tributario', 'ECLI:ES:AN:2024:1890', '2024-05-08',
                    'SAN 1890/2024', 'Otra sentencia relacionada.',
                    'https://example.invalid/an-1890'
                )
                ON CONFLICT DO NOTHING
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                    ambito, referencia, fecha, titulo, texto, url_fuente
                )
                VALUES (
                    'resolucion_teac', 'TEAC', 'es', 'teac',
                    'fiscal', '00/1234/2024', '2024-03-15',
                    'Resolucion TEAC IVA', 'Criterio TEAC relacionado con LIVA 91.',
                    'https://example.invalid/teac'
                )
                ON CONFLICT DO NOTHING
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
                SELECT d.id, a.id, 'manual', 1.0, 'fixture'
                FROM documento_interpretativo d
                JOIN articulo a ON a.numero = '91'
                JOIN norma n ON n.id = a.norma_id
                WHERE d.referencia IN ('V2222-26', 'ECLI:ES:AN:2024:1890', '00/1234/2024')
                  AND n.codigo = 'LIVA'
                ON CONFLICT DO NOTHING
                """
            )
        )

    async with _client() as c:
        response = await c.get("/v1/jurisprudencia/ECLI:ES:TS:2024:2741")

    assert response.status_code == 200
    data = response.json()
    assert data["referencia"] == "ECLI:ES:TS:2024:2741"
    refs = {item["referencia"] for item in data["doctrina_relacionada"]}
    assert "V2222-26" in refs
    assert "00/1234/2024" in refs
    assert "ECLI:ES:AN:2024:1890" not in refs
