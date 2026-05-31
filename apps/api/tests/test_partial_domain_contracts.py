import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent / "workers"))

from main import app


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/v1/bde", "/v1/sepblac"])
async def test_partial_document_domains_expose_fail_closed_coverage_contract(path: str):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get(path)

    assert response.status_code == 200
    payload = response.json()
    assert "documentos" in payload
    assert "items" in payload
    assert isinstance(payload["total"], int)
    assert payload["coverage_status"] in {"partial_loaded", "workflow_empty"}
    assert payload["safe_to_answer"] is False

    if payload["documentos"]:
        first = payload["documentos"][0]
        assert first["url_fuente"]
        assert first["row_completeness"] == "partial"
        assert first["row_provenance"] == "official_best_effort"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/v1/bdns", "/v1/cendoj"])
async def test_very_limited_document_domains_expose_fail_closed_coverage_contract(path: str):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get(path)

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert isinstance(payload["total"], int)
    assert payload["coverage_status"] in {"very_limited", "workflow_empty"}
    assert payload["safe_to_answer"] is False

    if payload["items"]:
        first = payload["items"][0]
        assert first["url_fuente"]
        assert first["row_completeness"] == "partial"
        assert first["row_provenance"] == "official_best_effort"
