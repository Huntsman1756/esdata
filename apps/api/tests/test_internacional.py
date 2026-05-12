"""Tests for International Obligations router (FATCA / CRS).

Cubre: listado con filtros, detalle por codigo y fallos 404.
"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app


# ---------------------------------------------------------------------------
# Client fixture (uses conftest db tables + seed)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Obligaciones Internacionales
# ---------------------------------------------------------------------------


class TestListarObligacionesInternacionales:
    @pytest.mark.asyncio
    async def test_listado_sin_filtros(self, client):
        resp = await client.get("/v1/internacional/obligaciones")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 4
        assert len(body["items"]) >= 4
        assert body["limit"] == 100
        assert body["offset"] == 0

    @pytest.mark.asyncio
    async def test_listado_paginado(self, client):
        resp = await client.get("/v1/internacional/obligaciones?limit=2&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 4
        assert len(body["items"]) == 2
        assert body["has_more"] is True
        assert body["next_offset"] == 2

    @pytest.mark.asyncio
    async def test_listado_filtro_tipo(self, client):
        resp = await client.get("/v1/internacional/obligaciones?tipo=referencia_normativa")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert item["tipo"] == "referencia_normativa"

    @pytest.mark.asyncio
    async def test_listado_filtro_tipo_directiva(self, client):
        resp = await client.get("/v1/internacional/obligaciones?tipo=directiva")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert item["tipo"] == "directiva"

    @pytest.mark.asyncio
    async def test_listado_filtro_estado(self, client):
        resp = await client.get("/v1/internacional/obligaciones?estado=activo")
        assert resp.status_code == 200
        body = resp.json()
        for item in body["items"]:
            assert item["estado"] == "activo"

    @pytest.mark.asyncio
    async def test_listado_filtro_jurisdiccion(self, client):
        resp = await client.get("/v1/internacional/obligaciones?jurisdiccion=ES-US")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert item["jurisdiccion_origen"] == "ES-US"

    @pytest.mark.asyncio
    async def test_listado_filtro_estado_inactivo(self, client):
        resp = await client.get("/v1/internacional/obligaciones?estado=inactivo")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert item["estado"] == "inactivo"


class TestDetalleObligacionInternacional:
    @pytest.mark.asyncio
    async def test_detalle_fatca(self, client):
        resp = await client.get("/v1/internacional/obligaciones/FATCA")
        assert resp.status_code == 200
        body = resp.json()
        assert body["item"]["codigo"] == "FATCA"
        assert body["item"]["tipo"] == "referencia_normativa"
        assert body["item"]["estado"] == "activo"
        assert body["item"]["source_url"].startswith("https://www.boe.es/")
        assert body["item"]["source_worker"] == "official-regulatory-references"

    @pytest.mark.asyncio
    async def test_detalle_crs(self, client):
        resp = await client.get("/v1/internacional/obligaciones/CRS")
        assert resp.status_code == 200
        body = resp.json()
        assert body["item"]["codigo"] == "CRS"
        assert body["item"]["tipo"] == "referencia_normativa"
        assert body["item"]["source_url"].startswith("https://www.boe.es/")

    @pytest.mark.asyncio
    async def test_detalle_fatca_iga(self, client):
        resp = await client.get("/v1/internacional/obligaciones/FATCA_IGA_ES")
        assert resp.status_code == 200
        body = resp.json()
        assert body["item"]["codigo"] == "FATCA_IGA_ES"
        assert body["item"]["tipo"] == "convenio"

    @pytest.mark.asyncio
    async def test_detalle_dac6(self, client):
        resp = await client.get("/v1/internacional/obligaciones/DAC6")
        assert resp.status_code == 200
        body = resp.json()
        assert body["item"]["codigo"] == "DAC6"
        assert body["item"]["tipo"] == "directiva"

    @pytest.mark.asyncio
    async def test_detalle_404(self, client):
        resp = await client.get("/v1/internacional/obligaciones/NO_EXISTE")
        assert resp.status_code == 404
