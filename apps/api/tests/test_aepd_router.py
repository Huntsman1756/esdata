import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent / "workers"))

from main import app


@pytest.mark.asyncio
async def test_aepd_list_exposes_traceable_pagination_contract():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/aepd", params={"limit": 2})

    assert response.status_code == 200
    payload = response.json()
    assert "documentos" in payload
    assert "items" in payload
    assert payload["limit"] == 2
    assert payload["offset"] == 0
    assert isinstance(payload["total"], int)
    if payload["items"]:
        first = payload["items"][0]
        assert first["url_aepd"] == first["url_fuente"]


@pytest.mark.asyncio
async def test_aepd_search_alias_is_not_captured_as_document_reference():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/aepd/buscar", params={"q": "proteccion datos", "limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert "items" in payload
    assert isinstance(payload["total"], int)
