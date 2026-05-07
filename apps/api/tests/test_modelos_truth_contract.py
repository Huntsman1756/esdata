"""Truth contract tests for AEAT modelos responses."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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


@pytest.mark.asyncio
async def test_modelo_detail_keeps_strong_article_visible_for_model_100():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/100")

    assert response.status_code == 200
    data = response.json()

    assert data["codigo"] == "100"
    assert {"norma": "LIVA", "numero": "91"} in [
        {"norma": articulo["norma"], "numero": articulo["numero"]}
        for articulo in data["articulos"]
    ]
    assert any(
        articulo["norma"] == "LIVA"
        and articulo["numero"] == "91"
        and articulo["fuente"] == "Instrucciones Modelo 100 2025"
        for articulo in data["articulos"]
    )


@pytest.mark.asyncio
async def test_modelo_detail_hides_legacy_article_for_model_303():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/303")

    assert response.status_code == 200
    data = response.json()

    assert data["codigo"] == "303"
    assert data["articulos"] == []


@pytest.mark.asyncio
async def test_modelos_list_reports_zero_articulos_for_model_303_when_only_legacy_rows_exist():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos")

    assert response.status_code == 200
    data = response.json()

    modelo_303 = next(modelo for modelo in data["modelos"] if modelo["codigo"] == "303")
    assert modelo_303["articulos_count"] == 0


@pytest.mark.asyncio
async def test_modelo_detail_matches_campana_operativa_truth_contract_for_model_100():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        detail_response = await client.get("/v1/modelos/100")
        operativa_response = await client.get("/v1/modelos/100/campana-operativa")

    assert detail_response.status_code == 200
    assert operativa_response.status_code == 200

    detail_data = detail_response.json()
    operativa_data = operativa_response.json()

    assert operativa_data["estado_metadato"] is None
    assert operativa_data["completeness"] == "parcial"
    assert operativa_data["verified"] is False
    assert detail_data["completeness"] == operativa_data["completeness"]
    assert detail_data["verified"] == operativa_data["verified"]


@pytest.mark.asyncio
async def test_modelo_fuentes_oficiales_keeps_partial_truth_contract_for_model_100():
    request_id = "req-modelo-fuentes-100"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-secret-key",
            "x-request-id": request_id,
            "x-user-id": "test-user",
        },
    ) as client:
        response = await client.get("/v1/modelos/100/fuentes-oficiales")

    assert response.status_code == 200

    from services.query_audit import QueryAuditService

    entries = QueryAuditService().get_by_request_id(request_id)
    assert len(entries) == 1
    assert entries[0].tool_name == "get_modelo_fuentes_oficiales"
    assert entries[0].completeness == "parcial"
    assert entries[0].verified is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "tool_name"),
    [
        ("/v1/modelos/100/casillas", "get_modelo_casillas"),
        ("/v1/modelos/100/claves", "get_modelo_claves"),
        ("/v1/modelos/100/instrucciones", "get_modelo_instrucciones"),
    ],
)
async def test_modelo_subendpoints_keep_partial_truth_contract_for_model_100(
    path: str, tool_name: str
):
    request_id = f"req-{tool_name}-100"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-secret-key",
            "x-request-id": request_id,
            "x-user-id": "test-user",
        },
    ) as client:
        response = await client.get(path)

    assert response.status_code == 200

    from services.query_audit import QueryAuditService

    entries = QueryAuditService().get_by_request_id(request_id)
    assert len(entries) == 1
    assert entries[0].tool_name == tool_name
    assert entries[0].completeness == "parcial"
    assert entries[0].verified is False
