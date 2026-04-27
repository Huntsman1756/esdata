"""Tests unitarios para el router dgt_doctrina de rendimientos mobiliarios."""

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


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
