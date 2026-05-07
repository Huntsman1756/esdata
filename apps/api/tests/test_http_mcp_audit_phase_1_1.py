"""Audit coverage for prioritized HTTP MCP operations (Fase 1.1)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _get_app_and_audit_service():
    from main import app
    from services.query_audit import QueryAuditService, reset_query_audit_service

    return app, QueryAuditService, reset_query_audit_service


def setup_function() -> None:
    _, _, reset_query_audit_service = _get_app_and_audit_service()
    reset_query_audit_service()


def teardown_function() -> None:
    _, _, reset_query_audit_service = _get_app_and_audit_service()
    reset_query_audit_service()


def _assert_minimum_contract(entry, *, path: str, tool_name: str, query_text: str, user_id: str):
    assert entry.path == path
    assert entry.tool_name == tool_name
    assert entry.query_text == query_text
    assert entry.user_id == user_id
    assert isinstance(entry.sources, list)
    assert isinstance(entry.confidence, dict)
    assert entry.completeness in {"completa", "parcial"}
    assert isinstance(entry.verified, bool)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("request_id", "path", "tool_name", "query_text"),
    [
        ("req-http-mcp-001", "/v1/legislacion/buscar?q=tipo+reducido+iva", "buscar_legislacion", "tipo reducido iva"),
        ("req-http-mcp-002", "/v1/legislacion/LIVA", "get_norma", "LIVA"),
        ("req-http-mcp-003", "/v1/legislacion/LIVA/articulos/91", "get_articulo", "LIVA:91"),
        ("req-http-mcp-004", "/v1/legislacion/LIVA/articulos/91/historial", "get_articulo_historial", "LIVA:91"),
        ("req-http-mcp-005", "/v1/doctrina/V0000-26", "get_doctrina", "V0000-26"),
        ("req-http-mcp-006", "/v1/modelos/100", "get_modelo", "100"),
        ("req-http-mcp-007", "/v1/modelos/100/casillas", "get_modelo_casillas", "100"),
        ("req-http-mcp-008", "/v1/modelos/100/claves", "get_modelo_claves", "100"),
        ("req-http-mcp-009", "/v1/modelos/100/instrucciones", "get_modelo_instrucciones", "100"),
        ("req-http-mcp-010", "/v1/modelos/100/fuentes-oficiales", "get_modelo_fuentes_oficiales", "100"),
    ],
)
async def test_prioritized_http_mcp_operations_persist_query_audit(
    request_id: str,
    path: str,
    tool_name: str,
    query_text: str,
):
    app, query_audit_service_cls, _ = _get_app_and_audit_service()
    user_id = "internal-http-mcp-user"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-secret-key",
            "x-request-id": request_id,
            "x-user-id": user_id,
        },
    ) as client:
        response = await client.get(path)

    assert response.status_code == 200

    entries = query_audit_service_cls().get_by_request_id(request_id)

    assert len(entries) == 1
    _assert_minimum_contract(
        entries[0],
        path=path.split("?")[0],
        tool_name=tool_name,
        query_text=query_text,
        user_id=user_id,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("request_id", "path", "tool_name", "response_key"),
    [
        ("req-http-mcp-empty-001", "/v1/modelos/100/casillas?campana=2099", "get_modelo_casillas", "casillas"),
        ("req-http-mcp-empty-002", "/v1/modelos/100/claves?campana=2099", "get_modelo_claves", "claves"),
        ("req-http-mcp-empty-003", "/v1/modelos/100/instrucciones?campana=2099", "get_modelo_instrucciones", "instrucciones"),
    ],
)
async def test_modelo_campaign_endpoints_audit_empty_success_responses(
    request_id: str,
    path: str,
    tool_name: str,
    response_key: str,
):
    app, query_audit_service_cls, _ = _get_app_and_audit_service()
    user_id = "internal-http-mcp-user"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-secret-key",
            "x-request-id": request_id,
            "x-user-id": user_id,
        },
    ) as client:
        response = await client.get(path)

    assert response.status_code == 200
    assert response.json()[response_key] == []

    entries = query_audit_service_cls().get_by_request_id(request_id)

    assert len(entries) == 1
    _assert_minimum_contract(
        entries[0],
        path=path.split("?")[0],
        tool_name=tool_name,
        query_text="100",
        user_id=user_id,
    )
    assert entries[0].response_summary == f"{response_key}=0"
    assert entries[0].completeness == "parcial"
    assert entries[0].verified is False
