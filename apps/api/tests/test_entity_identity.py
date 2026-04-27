"""Tests para el router /v1/entidades (LEI y entity identity)."""

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(API_DIR))

from main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_entidad_por_lei(client):
    r = await client.get("/v1/entidades/lei/5493001KJTIURC11JN06")
    assert r.status_code == 200
    data = r.json()
    assert data["entidad"]["lei"] == "5493001KJTIURC11JN06"
    assert data["entidad"]["estado"] == "active"
    assert data["entidad"]["pais"] == "ES"
    assert len(data["entidad"]["aliases"]) >= 2
    alias_nombres = [a["alias"] for a in data["entidad"]["aliases"]]
    assert "BBVA" in alias_nombres


@pytest.mark.asyncio
async def test_get_entidad_por_lei_no_existe(client):
    r = await client.get("/v1/entidades/lei/00000000000000000000")
    assert r.status_code == 404
    assert "Entidad no encontrada" in r.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_get_entidad_por_lei_case_insensitive(client):
    r = await client.get("/v1/entidades/lei/5493001kjt iurc11jn06")
    assert r.status_code == 200
    data = r.json()
    assert data["entidad"]["lei"] == "5493001KJTIURC11JN06"


@pytest.mark.asyncio
async def test_buscar_entidades_por_nombre(client):
    r = await client.get("/v1/entidades/buscar?q=alvarez")
    assert r.status_code == 200
    data = r.json()
    assert data["q"] == "alvarez"
    assert len(data["resultados"]) >= 1
    resultados = data["resultados"]
    assert any("alvarez" in r["nombre"].lower() for r in resultados)


@pytest.mark.asyncio
async def test_buscar_entidades_por_alias(client):
    r = await client.get("/v1/entidades/buscar?q=bbva")
    assert r.status_code == 200
    data = r.json()
    assert len(data["resultados"]) >= 1
    resultados = data["resultados"]
    # bbva coincide con nombre_legal "BBVA BANCO POPULAR ESPAÑOL" (prioridad alta)
    assert any(r["motivo"] in ("alias_exacto", "alias", "nombre_legal_exacto", "nombre_legal", "nombre_exacto") for r in resultados)


@pytest.mark.asyncio
async def test_buscar_entidades_por_lei(client):
    r = await client.get("/v1/entidades/buscar?q=5493001KJTIURC11JN06")
    assert r.status_code == 200
    data = r.json()
    assert len(data["resultados"]) >= 1
    assert data["resultados"][0]["lei"] == "5493001KJTIURC11JN06"
    assert data["resultados"][0]["motivo"] == "lei_match"


@pytest.mark.asyncio
async def test_buscar_entidades_sin_resultados(client):
    r = await client.get("/v1/entidades/buscar?q=empresa_inexistente_xyz123")
    assert r.status_code == 200
    data = r.json()
    assert data["resultados"] == []


@pytest.mark.asyncio
async def test_get_entidad_por_empresa_con_identificadores(client):
    r = await client.get("/v1/entidades/1")
    assert r.status_code == 200
    data = r.json()
    assert data["empresa"]["nombre"] == "ALVAREZ GARCIA GANADERIA, S.L."
    assert data["entidad"] is not None
    assert data["entidad"]["lei"] == "5493001KJTIURC11JN06"
    assert len(data["entidad"]["aliases"]) >= 2


@pytest.mark.asyncio
async def test_get_entidad_por_empresa_sin_identificadores(client):
    r = await client.get("/v1/entidades/2")
    assert r.status_code == 200
    data = r.json()
    assert data["empresa"]["nombre"] == "MURILLO & BARRERO, SOCIEDAD LIMITADA"
    assert data["entidad"] is None


@pytest.mark.asyncio
async def test_get_entidad_empresa_no_existe(client):
    r = await client.get("/v1/entidades/999999")
    assert r.status_code == 404
    assert "Empresa no encontrada" in r.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_entidad_incluye_vlei_placeholder(client):
    r = await client.get("/v1/entidades/lei/5493001KJTIURC11JN06")
    assert r.status_code == 200
    data = r.json()
    entidad = data["entidad"]
    assert "vlei_status" in entidad
    assert "vlei_cred_url" in entidad
