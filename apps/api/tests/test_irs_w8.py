"""Tests for IRS W-8 Forms router (Fase 25.6).

Cubre: listado con filtros, detalle por codigo y fallos 404.
"""

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

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
# IRS W-8 Forms
# ---------------------------------------------------------------------------


class TestListW8Forms:
    @pytest.mark.asyncio
    async def test_listado_sin_filtros(self, client):
        resp = await client.get("/v1/irs/w8-forms")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        assert len(body["forms"]) >= 2

    @pytest.mark.asyncio
    async def test_listado_filtro_tipo_sujeto(self, client):
        resp = await client.get("/v1/irs/w8-forms?tipo_sujeto=persona_fisica")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for f in body["forms"]:
            assert f["tipo_sujeto"] == "persona_fisica"

    @pytest.mark.asyncio
    async def test_listado_filtro_tipo_sujeto_juridica(self, client):
        resp = await client.get("/v1/irs/w8-forms?tipo_sujeto=persona_juridica")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for f in body["forms"]:
            assert f["tipo_sujeto"] == "persona_juridica"

    @pytest.mark.asyncio
    async def test_listado_filtro_estado(self, client):
        resp = await client.get("/v1/irs/w8-forms?estado=activo")
        assert resp.status_code == 200
        body = resp.json()
        for f in body["forms"]:
            assert f["estado"] == "activo"

    @pytest.mark.asyncio
    async def test_listado_sin_resultados(self, client):
        resp = await client.get("/v1/irs/w8-forms?tipo_sujeto=entidad_no_existe")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert len(body["forms"]) == 0


class TestGetW8Form:
    @pytest.mark.asyncio
    async def test_detalle_w8ben(self, client):
        resp = await client.get("/v1/irs/w8-forms/W8BEN")
        assert resp.status_code == 200
        body = resp.json()
        assert body["form"]["codigo"] == "W8BEN"
        assert body["form"]["tipo_sujeto"] == "persona_fisica"

    @pytest.mark.asyncio
    async def test_detalle_w8ben_e(self, client):
        resp = await client.get("/v1/irs/w8-forms/W8BENE")
        assert resp.status_code == 200
        body = resp.json()
        assert body["form"]["codigo"] == "W8BENE"
        assert body["form"]["tipo_sujeto"] == "persona_juridica"

    @pytest.mark.asyncio
    async def test_detalle_404(self, client):
        resp = await client.get("/v1/irs/w8-forms/NO_EXISTE")
        assert resp.status_code == 200
        body = resp.json()
        assert "error" in body
        assert body["codigo"] == "NO_EXISTE"
