"""Tests unitarios para RIRNR a traves del router legislacion existente."""

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
async def test_rirnr_norma_returns_200(client):
    r = await client.get("/v1/legislacion/RIRNR")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "RIRNR"


@pytest.mark.asyncio
async def test_rirnr_norma_has_correct_metadata(client):
    r = await client.get("/v1/legislacion/RIRNR")
    data = r.json()
    assert data["codigo"] == "RIRNR"
    assert "RIRNR" in data["titulo"] or "Reglamento" in data["titulo"]


@pytest.mark.asyncio
async def test_rirnr_articulos_returns_200(client):
    r = await client.get("/v1/legislacion/RIRNR/articulos")
    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "RIRNR"
    assert "articulos" in data
    assert len(data["articulos"]) > 0
    assert data["total"] >= len(data["articulos"])
    assert data["limit"] == 200
    assert data["offset"] == 0
    assert isinstance(data["has_more"], bool)


@pytest.mark.asyncio
async def test_rirnr_articulos_support_pagination_metadata(client):
    r = await client.get("/v1/legislacion/RIRNR/articulos", params={"limit": 1, "offset": 0})
    assert r.status_code == 200
    data = r.json()
    assert len(data["articulos"]) == 1
    assert data["total"] >= 1
    assert data["limit"] == 1
    assert data["offset"] == 0
    assert data["has_more"] == (data["total"] > 1)


@pytest.mark.asyncio
async def test_rirnr_articulo_31_returns_200(client):
    r = await client.get("/v1/legislacion/RIRNR/articulos/31")
    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "RIRNR"
    assert data["numero"] == "31"
    assert "rendimiento" in data["texto"].lower() or "dividendo" in data["texto"].lower()


@pytest.mark.asyncio
async def test_rirnr_articulo_32_returns_200(client):
    r = await client.get("/v1/legislacion/RIRNR/articulos/32")
    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "RIRNR"
    assert data["numero"] == "32"
    assert "tipo" in data["texto"].lower() or "retencion" in data["texto"].lower()


@pytest.mark.asyncio
async def test_rirnr_articulo_33_returns_200(client):
    r = await client.get("/v1/legislacion/RIRNR/articulos/33")
    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "RIRNR"
    assert data["numero"] == "33"


@pytest.mark.asyncio
async def test_rirnr_articulo_34_returns_200(client):
    r = await client.get("/v1/legislacion/RIRNR/articulos/34")
    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "RIRNR"
    assert data["numero"] == "34"


@pytest.mark.asyncio
async def test_rirnr_articulo_35_returns_200(client):
    r = await client.get("/v1/legislacion/RIRNR/articulos/35")
    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "RIRNR"
    assert data["numero"] == "35"


@pytest.mark.asyncio
async def test_rirnr_articulo_99_returns_404(client):
    r = await client.get("/v1/legislacion/RIRNR/articulos/99")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_rirnr_nonexistent_norma_returns_404(client):
    r = await client.get("/v1/legislacion/RIRNRX")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_rirnr_cobertura_shows_articles(client):
    r = await client.get("/v1/legislacion/cobertura")
    data = r.json()
    rirnr_entry = next(
        (n for n in data["normas"] if n["codigo"] == "RIRNR"), None
    )
    assert rirnr_entry is not None
    assert rirnr_entry["articulos"] > 0
