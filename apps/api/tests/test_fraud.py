"""Tests para el router de Ley 11/2021 Antifraude.

Cubre: fraud prevention programs, risk assessments, fraud incidents.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent / "workers"))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy import text

# --- Seed de datos antifraude ---


FRAUD_SEED_SQL = [
    """
    INSERT INTO fraud_prevention_program (entity_id, code_of_conduct, internal_reporting_system, training_schedule, audit_frequency, compliance_officer_name, status)
    VALUES (1, true, true, 'mensual', 'semestral', 'Pedro Ruiz', 'active')
    """,
    """
    INSERT INTO fraud_prevention_program (entity_id, code_of_conduct, internal_reporting_system, training_schedule, audit_frequency, compliance_officer_name, status)
    VALUES (2, true, false, 'trimestral', 'anual', 'Laura Gomez', 'active')
    """,
    """
    INSERT INTO fraud_prevention_program (entity_id, code_of_conduct, internal_reporting_system, training_schedule, audit_frequency, compliance_officer_name, status)
    VALUES (3, false, false, '', '', '', 'inactive')
    """,
    """
    INSERT INTO fraud_risk_assessment (entity_id, assessment_date, risk_areas, mitigation_measures, next_review_date)
    VALUES (1, '2025-01-15', '{"money_laundering", "corruption", "tax_evasion"}', 'Enhanced due diligence, staff training', '2025-07-15')
    """,
    """
    INSERT INTO fraud_risk_assessment (entity_id, assessment_date, risk_areas, mitigation_measures, next_review_date)
    VALUES (1, '2025-06-01', '{"payment_fraud", "identity_theft"}', 'Multi-factor authentication, transaction monitoring', '2025-12-01')
    """,
    """
    INSERT INTO fraud_risk_assessment (entity_id, assessment_date, risk_areas, mitigation_measures, next_review_date)
    VALUES (2, '2025-03-01', '{"corruption", "bribery"}', 'Compliance officer appointment', '2025-09-01')
    """,
    """
    INSERT INTO fraud_incident (entity_id, incident_date, description, amount_eur, status, resolution_date, regulatory_notification)
    VALUES (1, '2025-04-10', 'Intento de fraude con tarjeta robada', 2500.00, 'resolved', '2025-04-20', false)
    """,
    """
    INSERT INTO fraud_incident (entity_id, incident_date, description, amount_eur, status, resolution_date, regulatory_notification)
    VALUES (1, '2025-05-15', 'Estructuracion de pagos para evadir umbrales', 48000.00, 'under_investigation', NULL, true)
    """,
    """
    INSERT INTO fraud_incident (entity_id, incident_date, description, amount_eur, status, resolution_date, regulatory_notification)
    VALUES (2, '2025-06-20', 'Colusion con proveedor para sobre facturacion', 120000.00, 'open', NULL, true)
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_fraud():
    """Semilla basica de datos antifraude para tests del router."""
    from db import engine

    with engine.begin() as conn:
        for sql in FRAUD_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fraud_incident"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='fraud_incident'"))
        conn.execute(text("DELETE FROM fraud_risk_assessment"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='fraud_risk_assessment'"))
        conn.execute(text("DELETE FROM fraud_prevention_program"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='fraud_prevention_program'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ====================================================================
# Test: GET /v1/fraud/programs (lista)
# ====================================================================


class TestFraudListPrograms:
    @pytest.mark.asyncio
    async def test_fraud_programs_lista_status_200(self, client):
        resp = await client.get("/v1/fraud/programs")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_fraud_programs_lista_response_model(self, client):
        resp = await client.get("/v1/fraud/programs")
        data = resp.json()
        assert "programs" in data
        assert isinstance(data["programs"], list)

    @pytest.mark.asyncio
    async def test_fraud_programs_lista_contiene_registros(self, client):
        resp = await client.get("/v1/fraud/programs")
        data = resp.json()
        assert len(data["programs"]) >= 3

    @pytest.mark.asyncio
    async def test_fraud_programs_campos(self, client):
        resp = await client.get("/v1/fraud/programs")
        data = resp.json()
        for p in data["programs"]:
            assert "id" in p
            assert "entity_id" in p
            assert "code_of_conduct" in p
            assert "internal_reporting_system" in p
            assert "compliance_officer_name" in p
            assert "status" in p

    @pytest.mark.asyncio
    async def test_fraud_programs_filtro_status(self, client):
        resp = await client.get("/v1/fraud/programs", params={"status": "active"})
        data = resp.json()
        assert len(data["programs"]) >= 2
        for p in data["programs"]:
            assert p["status"] == "active"

    @pytest.mark.asyncio
    async def test_fraud_programs_filtro_entity_id(self, client):
        resp = await client.get("/v1/fraud/programs", params={"entity_id": "1"})
        data = resp.json()
        assert len(data["programs"]) >= 1
        for p in data["programs"]:
            assert p["entity_id"] == 1


# ====================================================================
# Test: GET /v1/fraud/programs/{id} (detalle)
# ====================================================================


class TestFraudGetProgram:
    @pytest.mark.asyncio
    async def test_fraud_program_detalle_status_200(self, client):
        resp = await client.get("/v1/fraud/programs/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_fraud_program_detalle_campos(self, client):
        resp = await client.get("/v1/fraud/programs/1")
        data = resp.json()
        assert "code_of_conduct" in data
        assert "internal_reporting_system" in data
        assert "training_schedule" in data
        assert "audit_frequency" in data
        assert "compliance_officer_name" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_fraud_program_detalle_404(self, client):
        resp = await client.get("/v1/fraud/programs/9999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/fraud/risk-assessments (lista)
# ====================================================================


class TestFraudListRiskAssessments:
    @pytest.mark.asyncio
    async def test_risk_assessments_lista_status_200(self, client):
        resp = await client.get("/v1/fraud/risk-assessments")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_risk_assessments_lista_response_model(self, client):
        resp = await client.get("/v1/fraud/risk-assessments")
        data = resp.json()
        assert "assessments" in data
        assert len(data["assessments"]) >= 3

    @pytest.mark.asyncio
    async def test_risk_assessments_campos(self, client):
        resp = await client.get("/v1/fraud/risk-assessments")
        data = resp.json()
        for a in data["assessments"]:
            assert "id" in a
            assert "entity_id" in a
            assert "assessment_date" in a
            assert "risk_areas" in a
            assert "mitigation_measures" in a

    @pytest.mark.asyncio
    async def test_risk_assessments_filtro_entity_id(self, client):
        resp = await client.get("/v1/fraud/risk-assessments", params={"entity_id": "1"})
        data = resp.json()
        assert len(data["assessments"]) >= 2
        for a in data["assessments"]:
            assert a["entity_id"] == 1

    @pytest.mark.asyncio
    async def test_risk_assessments_filtro_search(self, client):
        resp = await client.get("/v1/fraud/risk-assessments", params={"search": "corruption"})
        data = resp.json()
        assert len(data["assessments"]) >= 1


# ====================================================================
# Test: GET /v1/fraud/risk-assessments/{id} (detalle)
# ====================================================================


class TestFraudGetRiskAssessment:
    @pytest.mark.asyncio
    async def test_risk_assessment_detalle_status_200(self, client):
        resp = await client.get("/v1/fraud/risk-assessments/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_risk_assessment_detalle_404(self, client):
        resp = await client.get("/v1/fraud/risk-assessments/9999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/fraud/incidents (lista)
# ====================================================================


class TestFraudListIncidents:
    @pytest.mark.asyncio
    async def test_fraud_incidents_lista_status_200(self, client):
        resp = await client.get("/v1/fraud/incidents")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_fraud_incidents_lista_response_model(self, client):
        resp = await client.get("/v1/fraud/incidents")
        data = resp.json()
        assert "incidents" in data
        assert len(data["incidents"]) >= 3

    @pytest.mark.asyncio
    async def test_fraud_incidents_campos(self, client):
        resp = await client.get("/v1/fraud/incidents")
        data = resp.json()
        for i in data["incidents"]:
            assert "id" in i
            assert "entity_id" in i
            assert "incident_date" in i
            assert "amount_eur" in i
            assert "status" in i
            assert "regulatory_notification" in i

    @pytest.mark.asyncio
    async def test_fraud_incidents_filtro_status(self, client):
        resp = await client.get("/v1/fraud/incidents", params={"status": "open"})
        data = resp.json()
        assert len(data["incidents"]) >= 1
        for i in data["incidents"]:
            assert i["status"] == "open"

    @pytest.mark.asyncio
    async def test_fraud_incidents_filtro_min_amount(self, client):
        resp = await client.get("/v1/fraud/incidents", params={"min_amount": "50000"})
        data = resp.json()
        assert len(data["incidents"]) >= 1
        for i in data["incidents"]:
            assert i["amount_eur"] >= 50000

    @pytest.mark.asyncio
    async def test_fraud_incidents_filtro_entity_id(self, client):
        resp = await client.get("/v1/fraud/incidents", params={"entity_id": "1"})
        data = resp.json()
        assert len(data["incidents"]) >= 2
        for i in data["incidents"]:
            assert i["entity_id"] == 1

    @pytest.mark.asyncio
    async def test_fraud_incidents_filtro_search(self, client):
        resp = await client.get("/v1/fraud/incidents", params={"search": "fraude"})
        data = resp.json()
        assert len(data["incidents"]) >= 1


# ====================================================================
# Test: GET /v1/fraud/incidents/{id} (detalle)
# ====================================================================


class TestFraudGetIncident:
    @pytest.mark.asyncio
    async def test_fraud_incident_detalle_status_200(self, client):
        resp = await client.get("/v1/fraud/incidents/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_fraud_incident_detalle_amount(self, client):
        resp = await client.get("/v1/fraud/incidents/1")
        data = resp.json()
        assert data["amount_eur"] == 2500.00

    @pytest.mark.asyncio
    async def test_fraud_incident_detalle_404(self, client):
        resp = await client.get("/v1/fraud/incidents/9999")
        assert resp.status_code == 404
