"""Truth contract tests for AEAT modelos responses."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from main import app


@pytest.mark.asyncio
async def test_modelo_detail_marks_partial_when_campaign_lacks_official_instructions():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/303")

    assert response.status_code == 200
    data = response.json()

    assert data["codigo"] == "303"
    assert data["instrucciones"] == []
    assert data["casillas"] == []
    assert data["completeness"] == "parcial"
    assert data["verified"] is False


@pytest.mark.asyncio
async def test_modelo_campana_operativa_marks_partial_when_runtime_is_inferred():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/303/campana-operativa")

    assert response.status_code == 200
    data = response.json()

    assert data["codigo"] == "303"
    assert data["estado_metadato"] in (None, "inferido")
    assert data["completeness"] == "parcial"
    assert data["verified"] is False
