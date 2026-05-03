"""Golden regressions for historically risky MCP-style fiscal questions."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from main import app


RISKY_QUERIES = [
    "como rellenar el modelo 296",
    "casilla 0490 del modelo 100",
    "FACTA/FATCA entidad pasiva USA",
    "dime casilla a casilla el modelo 100",
    "si no hay instrucciones oficiales, que me puedes decir del modelo 303",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("query", RISKY_QUERIES)
async def test_risky_queries_fail_closed_with_explicit_no_verificado(query: str):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/consulta", params={"q": query})

    assert response.status_code == 200
    data = response.json()
    confianza = data["confianza"]

    assert data["resultados"] == []
    assert data["cited_chunks"] == []
    assert confianza["review_required"] is True
    assert "NO VERIFICADO" in (confianza.get("aviso") or "")
