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
