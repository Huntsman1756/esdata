"""Fail-closed regressions for critical retrieval failures in consulta."""

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
async def test_consulta_fail_closed_when_requested_unified_retrieval_breaks(monkeypatch):
    import routers.consulta as consulta_module

    def broken_unified_search(*args, **kwargs):
        raise RuntimeError("vector index unavailable")

    monkeypatch.setattr(
        consulta_module,
        "unified_multi_source_search",
        broken_unified_search,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key", "x-request-id": "req-consulta-fail-closed-001"},
    ) as client:
        response = await client.get(
            "/v1/consulta",
            params={"q": "tipo reducido iva", "sources": "legislacion"},
        )

    assert response.status_code == 200
    data = response.json()

    assert data["resultados"] == []
    assert data["cited_chunks"] == []
    assert data["claim_citations"] == []
    assert data["confianza"]["review_required"] is True
    assert "NO VERIFICADO" in (data["confianza"].get("aviso") or "")
