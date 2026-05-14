"""Regression coverage for JSON consulta libre compatibility endpoint."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from main import app
from routers.consulta import _extract_keywords, _resolve_modelos


@pytest.mark.asyncio
async def test_consulta_libre_fatca_query_returns_safe_contract():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key", "x-request-id": "req-consulta-libre-fatca"},
    ) as client:
        response = await client.post(
            "/v1/ai/consulta",
            json={"query": "FATCA passive entity modelo 290"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["consulta"] == "FATCA passive entity modelo 290"
    assert data["status"] in {"matched", "evidence_limited", "no_results"}
    assert data["safe_to_answer"] is not None


def test_fatca_passive_query_routes_to_modelo_290_before_irnr():
    keywords = _extract_keywords("FATCA passive NFFE no residente modelo 290", "")
    resolved = _resolve_modelos(keywords)

    assert resolved[0] == "290"
    assert "216" not in resolved[:1]


@pytest.mark.asyncio
async def test_consulta_libre_empty_query_returns_400_not_500():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.post("/v1/ai/consulta", json={"query": "  "})

    assert response.status_code == 400
    assert response.status_code != 500


@pytest.mark.asyncio
async def test_consulta_libre_very_long_query_returns_400_not_500():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.post("/v1/ai/consulta", json={"query": "x" * 1001})

    assert response.status_code == 400
    assert response.status_code != 500
