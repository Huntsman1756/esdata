import json
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def test_domain_availability_classifies_empty_tables_from_ralph_registry(tmp_path, monkeypatch):
    from services import domain_availability

    registry = {
        "tables": [
            {
                "table": "empty_workflow",
                "classification": "workflow_empty",
                "domain": "Workflow",
                "official_source_family": "not_applicable_workflow_or_operational",
                "target_path": "gate_schema_rls_test",
                "action": "User workflow table; no fake rows.",
            },
            {
                "table": "empty_allowed",
                "classification": "allowed_empty",
                "domain": "Operational",
                "official_source_family": "not_applicable_workflow_or_operational",
                "target_path": "gate_schema_rls_test",
                "action": "Alert table; empty is healthy if no SLA breach.",
            },
            {
                "table": "empty_configured",
                "classification": "configured_but_unavailable",
                "domain": "Official registry",
                "official_source_family": "CNMV/ESMA official source",
                "target_path": "apps/workers/aifmd.py",
                "action": "Fund registry table; keep empty until official CNMV/ESMA fund ingestion is configured.",
            },
            {
                "table": "populated_table",
                "classification": "workflow_empty",
                "domain": "Live",
                "official_source_family": "official_source_required",
                "target_path": "worker",
                "action": "Verify provenance.",
            },
        ]
    }
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.setenv("ESDATA_TABLE_REGISTRY_PATH", str(registry_path))
    domain_availability.clear_registry_cache()

    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        for table in ("empty_workflow", "empty_allowed", "empty_configured", "populated_table"):
            conn.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
        conn.execute(text("INSERT INTO populated_table (id) VALUES (1)"))
        records = {r["table"]: r for r in domain_availability.list_domain_availability(conn)}

    assert records["empty_workflow"]["availability_status"] == "workflow_empty"
    assert records["empty_allowed"]["availability_status"] == "allowed_empty"
    assert records["empty_configured"]["availability_status"] == "configured_but_unavailable"
    assert records["populated_table"]["availability_status"] == "populated"
    assert records["empty_configured"]["safe_to_answer"] is False

    domain_availability.clear_registry_cache()


def test_domain_availability_endpoint_exposes_empty_statuses():
    from main import app

    with TestClient(app) as client:
        response = client.get(
            "/v1/domain-availability",
            params={"only_empty": "true"},
            headers={"x-api-key": "test-secret-key"},
        )

    assert response.status_code == 200
    payload = response.json()
    statuses = {item["availability_status"] for item in payload["items"]}
    assert statuses <= {"workflow_empty", "allowed_empty", "configured_but_unavailable"}
    assert "not_available" not in statuses
    assert "operational_data" not in statuses


def test_empty_domain_router_uses_explicit_availability_status():
    from main import app

    with TestClient(app) as client:
        response = client.get("/v1/mica/casp", headers={"x-api-key": "test-secret-key"})

    assert response.status_code == 200
    payload = response.json()
    if payload.get("total", 0) == 0:
        assert payload["availability_status"] in {
            "workflow_empty",
            "allowed_empty",
            "configured_but_unavailable",
        }
        assert payload["status"] == payload["availability_status"]
        assert payload["items"] == []


@pytest.mark.asyncio
async def test_consulta_abstains_when_query_depends_on_empty_domain():
    from main import app
    from services.query_audit import QueryAuditService, reset_query_audit_service

    reset_query_audit_service()
    request_id = "req-availability-guard-001"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key", "x-request-id": request_id},
    ) as client:
        response = await client.get("/v1/consulta", params={"q": "lista CASP MiCA autorizados en España"})

    assert response.status_code == 200
    payload = response.json()
    confianza = payload["confianza"]
    availability = confianza["availability"]

    assert payload["resultados"] == []
    assert payload["cited_chunks"] == []
    assert confianza["review_required"] is True
    assert "NO VERIFICADO" in confianza["aviso"]
    assert availability["blocked"] is True
    assert any(item["table"] == "casp" for item in availability["tables"])
    assert all(item["safe_to_answer"] is False for item in availability["tables"])

    entries = QueryAuditService().get_by_request_id(request_id)
    assert len(entries) == 1
    assert entries[0].grounding_status == "availability_blocked"
    assert entries[0].verified is False
    assert entries[0].response_payload["confianza"]["availability"]["blocked"] is True


@pytest.mark.asyncio
async def test_consulta_regular_aeat_query_is_not_blocked_by_availability_guard():
    from main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/consulta", params={"q": "modelo 100 irpf"})

    assert response.status_code == 200
    payload = response.json()
    assert "availability" not in (payload["confianza"] or {})
