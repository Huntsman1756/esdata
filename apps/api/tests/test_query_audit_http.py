"""HTTP integration tests for query_audit router (Fase 30.2)."""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from main import app  # noqa: E402
from services.query_audit import reset_query_audit_service  # noqa: E402


@pytest.fixture(autouse=True)
def clean_query_audit():
    reset_query_audit_service()
    yield
    reset_query_audit_service()


@pytest.mark.asyncio
async def test_query_audit_list_empty():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/query-audit")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["entries"] == []
    assert data["path"] is None


@pytest.mark.asyncio
async def test_query_audit_list_after_write():
    from services.query_audit import get_query_audit_service

    svc = get_query_audit_service()
    svc.record_query(
        request_id="req-http-001",
        user_id="test-user",
        path="/v1/consulta",
        query_text="iva deducible",
        retrieved_chunks=[{"chunk_id": "c1", "score": 0.9}],
        response_summary="2 resultados",
        model_version="v1",
        config_version="cfg-v1",
        tool_name="buscar_legislacion",
        sources=[{"title": "BOE", "url": "https://boe.es/liva"}],
        confidence={"score": 0.9, "label": "alta"},
        completeness="completa",
        verified=True,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/query-audit")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    entry = data["entries"][0]
    assert entry["request_id"] == "req-http-001"
    assert entry["query_text"] == "iva deducible"
    assert entry["path"] == "/v1/consulta"
    assert entry["user_id"] == "test-user"
    assert entry["model_version"] == "v1"
    assert entry["config_version"] == "cfg-v1"
    assert entry["tool_name"] == "buscar_legislacion"
    assert entry["sources"] == [{"title": "BOE", "url": "https://boe.es/liva"}]
    assert entry["confidence"] == {"score": 0.9, "label": "alta"}
    assert entry["completeness"] == "completa"
    assert entry["verified"] is True


@pytest.mark.asyncio
async def test_query_audit_list_exposes_negative_contract_when_not_verified():
    from services.query_audit import get_query_audit_service

    svc = get_query_audit_service()
    svc.record_query(
        request_id="req-http-negative-001",
        user_id="test-user",
        path="/mcp/tools/get_modelo",
        query_text='{"codigo":"100"}',
        retrieved_chunks=[],
        response_summary="no verificado",
        tool_name="get_modelo",
        sources=[],
        confidence={"score": 0.0, "label": "baja"},
        completeness="parcial",
        verified=False,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/query-audit/req-http-negative-001")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    entry = data["entries"][0]
    assert entry["tool_name"] == "get_modelo"
    assert entry["sources"] == []
    assert entry["completeness"] == "parcial"
    assert entry["verified"] is False


@pytest.mark.asyncio
async def test_query_audit_filter_by_path():
    from services.query_audit import get_query_audit_service

    svc = get_query_audit_service()
    svc.record_query(
        request_id="req-path-001",
        user_id="u1",
        path="/v1/consulta",
        query_text="consulta",
        retrieved_chunks=[],
        response_summary="ok",
    )
    svc.record_query(
        request_id="req-path-002",
        user_id="u2",
        path="/v1/buscar",
        query_text="buscar",
        retrieved_chunks=[],
        response_summary="ok",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/query-audit", params={"path": "/v1/consulta"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["path"] == "/v1/consulta"
    assert data["entries"][0]["request_id"] == "req-path-001"


@pytest.mark.asyncio
async def test_query_audit_by_request_id():
    from services.query_audit import get_query_audit_service

    svc = get_query_audit_service()
    svc.record_query(
        request_id="req-get-001",
        user_id="u1",
        path="/v1/consulta",
        query_text="test",
        retrieved_chunks=[],
        response_summary="ok",
    )
    svc.record_query(
        request_id="req-get-002",
        user_id="u1",
        path="/v1/consulta",
        query_text="test2",
        retrieved_chunks=[],
        response_summary="ok",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/query-audit/req-get-001")

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "req-get-001"
    assert data["total"] == 1
    assert data["entries"][0]["query_text"] == "test"


@pytest.mark.asyncio
async def test_query_audit_by_request_id_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/query-audit/nonexistent")

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "nonexistent"
    assert data["total"] == 0
    assert data["entries"] == []


@pytest.mark.asyncio
async def test_query_audit_list_exposes_runtime_grounding_and_truth_fields_from_consulta():
    request_id = "req-query-audit-runtime-001"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-secret-key",
            "x-request-id": request_id,
            "x-user-id": "runtime-user",
        },
    ) as client:
        consulta_response = await client.get("/v1/consulta?q=tipo+reducido+iva")
        assert consulta_response.status_code == 200

        response = await client.get("/v1/ai/query-audit", params={"path": "/v1/consulta"})

    assert response.status_code == 200
    data = response.json()
    entry = next(item for item in data["entries"] if item["request_id"] == request_id)

    assert entry["grounding_status"] in {"full", "partial", "none", "empty"}
    assert isinstance(entry["prompt_injection_detected"], bool)
    assert isinstance(entry["grounding_summary"], dict)
    assert entry["grounding_summary"]["grounding_status"] == entry["grounding_status"]
    assert entry["completeness"] in {"completa", "parcial"}
    assert isinstance(entry["verified"], bool)


@pytest.mark.asyncio
async def test_query_audit_by_request_id_exposes_runtime_grounding_and_truth_fields_from_consulta():
    request_id = "req-query-audit-runtime-002"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-secret-key",
            "x-request-id": request_id,
            "x-user-id": "runtime-user",
        },
    ) as client:
        consulta_response = await client.get("/v1/consulta?q=tipo+reducido+iva")
        assert consulta_response.status_code == 200

        response = await client.get(f"/v1/ai/query-audit/{request_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == request_id
    assert data["total"] == 1

    entry = data["entries"][0]
    assert entry["path"] == "/v1/consulta"
    assert entry["grounding_status"] in {"full", "partial", "none", "empty"}
    assert isinstance(entry["prompt_injection_detected"], bool)
    assert isinstance(entry["grounding_summary"], dict)
    assert entry["grounding_summary"]["grounding_status"] == entry["grounding_status"]
    assert entry["completeness"] in {"completa", "parcial"}
    assert isinstance(entry["verified"], bool)
