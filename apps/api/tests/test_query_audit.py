"""Tests for persistent query audit log service."""

import sys
from pathlib import Path

import pytest
from conftest import engine
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

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


def test_query_audit_persists_minimum_mcp_contract_fields():
    service = QueryAuditService()
    created = service.record_query(
        request_id="req-query-contract-001",
        user_id="auditor-contract",
        path="/mcp/tools/get_norma",
        query_text='{"codigo":"LIVA"}',
        retrieved_chunks=[{"chunk_id": "chk-1", "source_url": "https://boe.es/diario_boe"}],
        response_summary="ok",
        tool_name="get_norma",
        sources=[
            {
                "title": "Ley del IVA",
                "url": "https://boe.es/diario_boe",
                "trust_tier": "fuente_oficial_primaria",
            }
        ],
        confidence={"score": 0.98, "label": "alta"},
        completeness="completa",
        verified=True,
    )

    fresh_service = QueryAuditService()
    entries = fresh_service.get_by_request_id("req-query-contract-001")

    assert created.tool_name == "get_norma"
    assert created.sources[0]["url"] == "https://boe.es/diario_boe"
    assert created.confidence == {"score": 0.98, "label": "alta"}
    assert created.completeness == "completa"
    assert created.verified is True
    assert len(entries) == 1
    assert entries[0].tool_name == "get_norma"
    assert entries[0].sources[0]["trust_tier"] == "fuente_oficial_primaria"
    assert entries[0].confidence["score"] == 0.98
    assert entries[0].completeness == "completa"
    assert entries[0].verified is True


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
                    user_id TEXT,
                    path TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    retrieved_chunks TEXT NOT NULL DEFAULT '[]',
                    response_summary TEXT NOT NULL DEFAULT '',
                    model_version TEXT,
                    config_version TEXT,
                    created_at TEXT NOT NULL
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
        columns = {
            row[1] for row in conn.execute(text("PRAGMA table_info(query_audit_log)"))
        }

    assert {"grounding_status", "prompt_injection_detected", "grounding_summary", "response_payload"}.issubset(columns)

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT grounding_status, prompt_injection_detected, grounding_summary, response_payload
                FROM query_audit_log
                WHERE entry_id = :entry_id
                """
            ),
            {"entry_id": created.entry_id},
        ).mappings().one()

    assert row["grounding_status"] == "full"
    assert row["prompt_injection_detected"] == 0
    assert row["grounding_summary"]
    assert row["response_payload"] == "{}"


def test_query_audit_legacy_repair_covers_full_mcp_contract_columns():
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS query_audit_log"))
        conn.execute(
            text(
                """
                CREATE TABLE query_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT NOT NULL UNIQUE,
                    request_id TEXT NOT NULL,
                    user_id TEXT,
                    path TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    retrieved_chunks TEXT NOT NULL DEFAULT '[]',
                    response_summary TEXT NOT NULL DEFAULT '',
                    model_version TEXT,
                    config_version TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
        )

    QueryAuditService()

    with engine.begin() as conn:
        columns = {
            row[1] for row in conn.execute(text("PRAGMA table_info(query_audit_log)"))
        }

    assert {
        "tool_name",
        "sources",
        "confidence",
        "completeness",
        "verified",
        "grounding_status",
        "prompt_injection_detected",
        "grounding_summary",
        "response_payload",
    }.issubset(columns)


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
    assert entry.response_payload["consulta"] == "tipo reducido iva"
    assert isinstance(entry.response_payload["resultados"], list)
    assert "confianza" in entry.response_payload


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
async def test_buscar_legislacion_alias_persists_query_audit_entry():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key", "x-request-id": "req-buscar-leg-audit-001", "x-user-id": "internal-leg-user"},
    ) as client:
        response = await client.get("/v1/legislacion/buscar?q=tipo+reducido+iva")

    assert response.status_code == 200

    entries = QueryAuditService().get_by_request_id("req-buscar-leg-audit-001")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.path == "/v1/legislacion/buscar"
    assert entry.user_id == "internal-leg-user"
    assert "tipo reducido iva" in entry.query_text.lower()
    assert entry.response_summary


@pytest.mark.asyncio
async def test_buscar_legislacion_hybrid_persists_query_audit_entry(monkeypatch):
    from routers import buscar as buscar_router

    monkeypatch.setattr(
        buscar_router,
        "hybrid_search_legislacion",
        lambda *args, **kwargs: {"q": args[0], "resultados": []},
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key", "x-request-id": "req-buscar-hybrid-audit-001", "x-user-id": "internal-hybrid-user"},
    ) as client:
        response = await client.get("/v1/legislacion/buscar/hybrid?q=tipo+reducido+iva")

    assert response.status_code == 200

    entries = QueryAuditService().get_by_request_id("req-buscar-hybrid-audit-001")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.path == "/v1/legislacion/buscar/hybrid"
    assert entry.user_id == "internal-hybrid-user"
    assert "tipo reducido iva" in entry.query_text.lower()
    assert "resultados=0" in entry.response_summary


@pytest.mark.asyncio
async def test_buscar_legislacion_hybrid_sqlite_fallback_persists_query_audit_entry():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key", "x-request-id": "req-buscar-hybrid-sqlite-001", "x-user-id": "internal-hybrid-user"},
    ) as client:
        response = await client.get("/v1/legislacion/buscar/hybrid?q=tipo+reducido+iva")

    assert response.status_code == 200
    data = response.json()
    assert data["search_mode"] == "fulltext"

    entries = QueryAuditService().get_by_request_id("req-buscar-hybrid-sqlite-001")
    assert len(entries) == 1
    assert entries[0].path == "/v1/legislacion/buscar/hybrid"


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
