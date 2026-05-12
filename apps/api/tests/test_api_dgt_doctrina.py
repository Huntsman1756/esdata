"""Tests unitarios para el router dgt_doctrina de rendimientos mobiliarios."""

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _seed_dgt_fixture(reference: str, metodo_enlace: str, confianza_enlace: float):
    engine = app.state.engine

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
                    'fiscal', :reference, '2026-01-15', 'Consulta DGT fixture',
                    'Texto fixture sin terminos de busqueda adicionales.', :url_fuente
                )
                """
            ),
            {
                "reference": reference,
                "url_fuente": f"https://example.invalid/dgt/{reference}",
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
                SELECT d.id, a.id, :metodo_enlace, :confianza_enlace, 'Test fixture'
                FROM documento_interpretativo d
                JOIN articulo a ON a.numero = '91'
                JOIN norma n ON n.id = a.norma_id
                WHERE d.referencia = :reference AND n.codigo = 'LIVA'
                """
            ),
            {
                "reference": reference,
                "metodo_enlace": metodo_enlace,
                "confianza_enlace": confianza_enlace,
            },
        )


@pytest.mark.asyncio
async def test_dgt_doctrina_search_returns_200(client):
    r = await client.get("/v1/doctrina/dgt/buscar", params={"q": "dividendos"})
    assert r.status_code == 200
    data = r.json()
    assert "q" in data
    assert "resultados" in data


@pytest.mark.asyncio
async def test_dgt_doctrina_search_empty_results(client):
    r = await client.get(
        "/v1/doctrina/dgt/buscar",
        params={"q": "xxyznoexistentefilterabc"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["q"] == "xxyznoexistentefilterabc"
    assert data["resultados"] == []


@pytest.mark.asyncio
async def test_dgt_doctrina_detail_returns_404(client):
    r = await client.get("/v1/doctrina/dgt/V9999-99")
    assert r.status_code == 404
    data = r.json()
    assert "V9999-99" in data["detail"]["error"]


@pytest.mark.asyncio
async def test_dgt_doctrina_search_with_filters(client):
    r = await client.get(
        "/v1/doctrina/dgt/buscar",
        params={
            "q": "retenciones",
            "tipo": "consulta_vinculante",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "q" in data
    assert "resultados" in data


@pytest.mark.asyncio
async def test_dgt_doctrina_search_with_organismo_filter(client):
    r = await client.get(
        "/v1/doctrina/dgt/buscar",
        params={
            "q": "dividendos",
            "organismo_emisor": "DGT",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "q" in data
    assert "resultados" in data


@pytest.mark.asyncio
async def test_dgt_doctrina_search_with_desde_filter(client):
    r = await client.get(
        "/v1/doctrina/dgt/buscar",
        params={
            "q": "rendimientos",
            "desde": "2020-01-01",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "q" in data
    assert "resultados" in data


@pytest.mark.asyncio
async def test_dgt_doctrina_detail_returns_404_for_non_dgt_doc(client):
    """Verifica que la consulta solo busca documentos DGT (tipo_fuente='dgt')."""
    r = await client.get("/v1/doctrina/dgt/V0000-00")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_dgt_doctrina_detail_requires_exact_link_for_strong_anchor(client):
    from services.query_audit import QueryAuditService, reset_query_audit_service

    reference = "VDGT-HEUR-26"
    request_id = "req-dgt-doctrina-heuristic-detail-001"
    reset_query_audit_service()
    _seed_dgt_fixture(reference, "auto_link_heuristic", 0.85)

    r = await client.get(
        f"/v1/doctrina/dgt/{reference}",
        headers={
            "x-api-key": "test-secret-key",
            "x-request-id": request_id,
            "x-user-id": "internal-dgt-user",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["articulos_relacionados"] == [
        {
            "norma": "LIVA",
            "numero": "91",
            "metodo_enlace": "auto_link_heuristic",
            "confianza_enlace": 0.85,
        }
    ]
    assert data["confianza"]["nivel"] == 1

    entries = QueryAuditService().get_by_request_id(request_id)
    assert len(entries) == 1
    assert entries[0].tool_name == "get_dgt_doctrina"
    assert entries[0].completeness == "parcial"
    assert entries[0].verified is False
    assert entries[0].confidence == {"score": 0.5, "label": "media"}


@pytest.mark.asyncio
async def test_dgt_doctrina_detail_keeps_exact_links_as_strong_anchors(client):
    from services.query_audit import QueryAuditService, reset_query_audit_service

    reference = "VDGT-EXACT-26"
    request_id = "req-dgt-doctrina-exact-detail-001"
    reset_query_audit_service()
    _seed_dgt_fixture(reference, "manual", 1.0)

    r = await client.get(
        f"/v1/doctrina/dgt/{reference}",
        headers={
            "x-api-key": "test-secret-key",
            "x-request-id": request_id,
            "x-user-id": "internal-dgt-user",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["articulos_relacionados"] == [
        {
            "norma": "LIVA",
            "numero": "91",
            "metodo_enlace": "manual",
            "confianza_enlace": 1.0,
        }
    ]
    assert data["confianza"]["nivel"] == 2

    entries = QueryAuditService().get_by_request_id(request_id)
    assert len(entries) == 1
    assert entries[0].tool_name == "get_dgt_doctrina"
    assert entries[0].completeness == "completa"
    assert entries[0].verified is True
    assert entries[0].confidence == {"score": 0.9, "label": "alta"}
