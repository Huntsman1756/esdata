"""Tests for persistent query audit log service."""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from .conftest import engine

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from main import app
from services.query_audit import QueryAuditService, reset_query_audit_service


def setup_function():
    reset_query_audit_service()


def teardown_function():
    reset_query_audit_service()


def test_query_audit_persists_entries_across_service_instances():
    service = QueryAuditService()
    created = service.record_query(
        request_id="req-query-001",
        user_id="auditor-1",
        path="/v1/consulta",
        query_text="iva deducible",
        retrieved_chunks=[{"chunk_id": "chk-1", "score": 0.93}],
        response_summary="2 resultados relevantes",
        model_version="llm-v1",
        config_version="cfg-v1",
    )

    fresh_service = QueryAuditService()
    entries = fresh_service.get_by_request_id("req-query-001")

    assert created.entry_id
    assert len(entries) == 1
    assert entries[0].query_text == "iva deducible"
    assert entries[0].retrieved_chunks[0]["chunk_id"] == "chk-1"


def test_query_audit_can_filter_by_path():
    service = QueryAuditService()
    service.record_query(
        request_id="req-query-010",
        user_id="u1",
        path="/v1/consulta",
        query_text="consulta 1",
        retrieved_chunks=[],
        response_summary="ok",
    )
    service.record_query(
        request_id="req-query-011",
        user_id="u2",
        path="/v1/search",
        query_text="consulta 2",
        retrieved_chunks=[],
        response_summary="ok",
    )

    filtered = service.get_entries(path="/v1/consulta")

    assert len(filtered) == 1
    assert filtered[0].request_id == "req-query-010"


def test_query_audit_repairs_legacy_postgres_columns():
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS query_audit_log"))
        conn.execute(
            text(
                """
                CREATE TABLE query_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT NOT NULL UNIQUE,
                    request_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL DEFAULT '',
                    user_id TEXT,
                    path TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    retrieved_chunks TEXT NOT NULL DEFAULT '[]',
                    sources TEXT NOT NULL DEFAULT '[]',
                    response_summary TEXT NOT NULL DEFAULT '',
                    confidence TEXT NOT NULL DEFAULT '{}',
                    completeness TEXT NOT NULL DEFAULT 'parcial',
                    verified INTEGER NOT NULL DEFAULT 0,
                    model_version TEXT,
                    config_version TEXT,
                    created_at TEXT NOT NULL,
                    grounding_status TEXT DEFAULT '',
                    prompt_injection_detected INTEGER NOT NULL DEFAULT 0,
                    grounding_summary TEXT NOT NULL DEFAULT '{}',
                    response_payload TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
        )

    service = QueryAuditService()
    created = service.record_query(
        request_id="req-query-legacy-001",
        user_id="auditor-legacy",
        path="/v1/consulta",
        query_text="plazo prescripcion lgt",
        retrieved_chunks=[{"chunk_id": "chk-legacy-1"}],
        response_summary="resultados=1",
        grounding_status="full",
        prompt_injection_detected=False,
        grounding_summary={"grounding_status": "full", "total_claims": 1},
    )

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT grounding_status, prompt_injection_detected, grounding_summary
                FROM query_audit_log
                WHERE entry_id = :entry_id
                """
            ),
            {"entry_id": created.entry_id},
        ).mappings().one()

    assert row["grounding_status"] == "full"
    assert row["prompt_injection_detected"] == 0
    assert row["grounding_summary"]


@pytest.mark.asyncio
async def test_consulta_runtime_persists_query_audit_entry():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key", "x-request-id": "req-consulta-audit-001", "x-user-id": "internal-user"},
    ) as client:
        response = await client.get("/v1/consulta?q=tipo+reducido+iva")

    assert response.status_code == 200

    service = QueryAuditService()
    entries = service.get_by_request_id("req-consulta-audit-001")

    assert len(entries) == 1
    entry = entries[0]
    assert entry.path == "/v1/consulta"
    assert entry.user_id == "internal-user"
    assert "tipo reducido iva" in entry.query_text.lower()
    assert entry.response_summary
    assert entry.model_version == "esdata-ai-v1"
    assert entry.config_version == "consulta-faithfulness-v1"


@pytest.mark.asyncio
async def test_buscar_runtime_persists_query_audit_entry():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key", "x-request-id": "req-buscar-audit-001", "x-user-id": "internal-search-user"},
    ) as client:
        response = await client.get("/v1/buscar?q=tipo+reducido+iva")

    assert response.status_code == 200

    service = QueryAuditService()
    entries = service.get_by_request_id("req-buscar-audit-001")

    assert len(entries) == 1
    entry = entries[0]
    assert entry.path == "/v1/buscar"
    assert entry.user_id == "internal-search-user"
    assert "tipo reducido iva" in entry.query_text.lower()
    assert entry.response_summary


@pytest.mark.asyncio
async def test_doctrina_buscar_runtime_persists_query_audit_entry():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key", "x-request-id": "req-doctrina-audit-001", "x-user-id": "internal-doctrina-user"},
    ) as client:
        response = await client.get("/v1/doctrina/buscar?q=tipo+reducido+iva")

    assert response.status_code == 200

    service = QueryAuditService()
    entries = service.get_by_request_id("req-doctrina-audit-001")

    assert len(entries) == 1
    entry = entries[0]
    assert entry.path == "/v1/doctrina/buscar"
    assert entry.user_id == "internal-doctrina-user"
    assert "tipo reducido iva" in entry.query_text.lower()
    assert entry.response_summary


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "request_id", "expected_path", "expected_tool", "query_fragment"),
    [
        ("/v1/eurlex/buscar?q=MiFID+II+articulo+1", "req-eurlex-audit-001", "/v1/eurlex/buscar", "buscar_eurlex", "mifid"),
        ("/v1/aepd/buscar?q=RGPD+AEPD&limit=1", "req-aepd-audit-001", "/v1/aepd/buscar", "buscar_aepd", "rgpd"),
        ("/v1/cnmv/buscar?q=circular&limit=1", "req-cnmv-audit-001", "/v1/cnmv/buscar", "buscar_cnmv", "circular"),
        ("/v1/mica/casp/buscar?q=crypto&limit=1", "req-mica-audit-001", "/v1/mica/casp/buscar", "buscar_casp", "crypto"),
    ],
)
async def test_domain_search_endpoints_persist_query_audit_entries(
    path: str,
    request_id: str,
    expected_path: str,
    expected_tool: str,
    query_fragment: str,
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key", "x-request-id": request_id, "x-user-id": "domain-audit-user"},
    ) as client:
        response = await client.get(path)

    assert response.status_code == 200

    entries = QueryAuditService().get_by_request_id(request_id)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.path == expected_path
    assert entry.tool_name == expected_tool
    assert entry.user_id == "domain-audit-user"
    assert query_fragment in entry.query_text.lower()
    assert entry.response_summary
