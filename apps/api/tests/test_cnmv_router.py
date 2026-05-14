import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


def _client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_cnmv_buscar_alias_returns_traceable_documents():
    async with _client() as client:
        response = await client.get("/v1/cnmv/buscar?q=circular&limit=5")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    first = data["documentos"][0]
    assert first["tipo_documento"].startswith("circular")
    assert first["fecha_publicacion"] is not None
    assert first["url_cnmv"] or first["boe_referencia"]
    assert data["vigencia_filter"] == "current"
    assert data["included_estados_vigencia"] == ["vigente", "vigente_modificado"]
    assert "no cargado" in data["coverage_note"]


@pytest.mark.asyncio
async def test_cnmv_buscar_excludes_derogados_by_default():
    async with _client() as client:
        response = await client.get("/v1/cnmv/buscar?q=circular&limit=50")

    assert response.status_code == 200
    data = response.json()
    estados = {doc["estado_vigencia"] for doc in data["documentos"]}
    referencias = {doc["referencia"] for doc in data["documentos"]}
    assert "derogado" not in estados
    assert "vigente" in estados
    assert "vigente_modificado" in estados
    assert "CNMV-Circular-0-2020" not in referencias
    assert "CNMV-Circular-2-2024" in referencias


@pytest.mark.asyncio
async def test_cnmv_buscar_allows_derogados_when_requested():
    async with _client() as client:
        response = await client.get("/v1/cnmv/buscar?q=circular&vigencia=all&limit=50")

    assert response.status_code == 200
    data = response.json()
    estados = {doc["estado_vigencia"] for doc in data["documentos"]}
    referencias = {doc["referencia"] for doc in data["documentos"]}
    assert data["vigencia_filter"] == "all"
    assert data["included_estados_vigencia"] is None
    assert "derogado" in estados
    assert "CNMV-Circular-0-2020" in referencias


@pytest.mark.asyncio
async def test_cnmv_detail_exposes_source_aliases():
    async with _client() as client:
        response = await client.get("/v1/cnmv/CNMV-Circular-1-2025")

    assert response.status_code == 200
    data = response.json()
    assert data["referencia"] == "CNMV-Circular-1-2025"
    assert data["fecha_publicacion"] == "2025-03-05"
    assert data["url_cnmv"] == "https://example.invalid/cnmv/circular-1-2025"
    assert data["boe_referencia"] == "BOE-A-2025-1234"
