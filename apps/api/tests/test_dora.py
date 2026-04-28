"""Tests para el router de DORA (Digital Operational Resilience Act).

Fase 31.8 — Expansion regulatoria.
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

DORA_SEED_SQL = [
    """
    INSERT INTO dora_tic_incident (entity_id, incident_severity, description, impact_scope, detection_date, resolution_date, root_cause, classification, status)
    VALUES (1, 'high', 'Ataque ransomware afectando sistema de trading', 'sistemas_de_negocio_principales', '2024-02-15', '2024-02-20', 'phishing_email_empleado', 'cyber-attack', 'resolved')
    """,
    """
    INSERT INTO dora_tic_incident (entity_id, incident_severity, description, impact_scope, detection_date, resolution_date, root_cause, classification, status)
    VALUES (2, 'medium', 'Interrupcion servicio cloud proveedor AWS', 'plataforma_online_clientes', '2024-03-01', '2024-03-01', 'fallos_proveedor', 'outage', 'resolved')
    """,
    """
    INSERT INTO dora_tic_incident (entity_id, incident_severity, description, impact_scope, detection_date, resolution_date, root_cause, classification, status)
    VALUES (1, 'critical', 'Fuga de datos personales de 5000 clientes', 'base_datos_clientes_completa', '2024-03-10', NULL, 'vulnerabilidad_api', 'data-breach', 'open')
    """,
    """
    INSERT INTO dora_third_party_provider (provider_name, provider_type, criticality_assessment, contract_start, contract_end, eu_supervision_status, exit_strategy, status)
    VALUES ('Amazon Web Services EU', 'cloud', 'critical', '2020-01-01', '2026-12-31', 'bajo_supervision_EBA', 'plan_migracion_multi-cloud', 'active')
    """,
    """
    INSERT INTO dora_third_party_provider (provider_name, provider_type, criticality_assessment, contract_start, contract_end, eu_supervision_status, exit_strategy, status)
    VALUES ('Microsoft Azure EU', 'cloud', 'high', '2021-06-01', '2025-05-31', 'bajo_supervision_EBA', 'migracion_planificada', 'active')
    """,
    """
    INSERT INTO dora_ict_risk_register (entity_id, risk_description, likelihood, impact, mitigation, owner, review_date, status)
    VALUES (1, 'Dependencia de unico proveedor cloud', 'probable', 'alto', 'multi-cloud strategy, contratos con SLA', 'CISO', '2024-06-30', 'active')
    """,
    """
    INSERT INTO dora_penetration_test (entity_id, test_type, tester, test_date, findings_count, critical_findings, remediation_deadline, status)
    VALUES (1, 'black_box', 'Cure53', '2024-01-15', 12, 2, '2024-03-15', 'completed')
    """,
    """
    INSERT INTO dora_penetration_test (entity_id, test_type, tester, test_date, findings_count, critical_findings, remediation_deadline, status)
    VALUES (2, 'white_box', 'SecuriTeam', '2024-02-20', 8, 0, '2024-04-20', 'completed')
    """,
    """
    INSERT INTO dora_incident_classification_framework (framework_version, severity_thresholds, reporting_timelines, effective_date, status)
    VALUES ('1.0', '{"low": {"max_impact": "isolated", "max_duration_minutes": 30}}', '{"critical": "4_hours"}', '2024-01-01', 'active')
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_dora():
    """Semilla basica de datos DORA para tests del router."""
    from db import engine

    with engine.begin() as conn:
        for sql in DORA_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dora_incident_classification_framework"))
        conn.execute(text("DELETE FROM dora_penetration_test"))
        conn.execute(text("DELETE FROM dora_ict_risk_register"))
        conn.execute(text("DELETE FROM dora_third_party_provider"))
        conn.execute(text("DELETE FROM dora_tic_incident"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestDoraTicIncidents:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/dora/tic-incidents")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/dora/tic-incidents")
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_campo_severity(self, client):
        resp = await client.get("/v1/dora/tic-incidents")
        data = resp.json()
        severities = [i["incident_severity"] for i in data["items"]]
        assert "high" in severities
        assert "critical" in severities

    @pytest.mark.asyncio
    async def test_campo_classification(self, client):
        resp = await client.get("/v1/dora/tic-incidents")
        data = resp.json()
        classifications = [i["classification"] for i in data["items"]]
        assert "cyber-attack" in classifications

    @pytest.mark.asyncio
    async def test_filtro_status(self, client):
        resp = await client.get("/v1/dora/tic-incidents", params={"status": "open"})
        data = resp.json()
        assert len(data["items"]) >= 1
        for i in data["items"]:
            assert i["status"] == "open"

    @pytest.mark.asyncio
    async def test_filtro_severity(self, client):
        resp = await client.get("/v1/dora/tic-incidents", params={"incident_severity": "critical"})
        data = resp.json()
        assert len(data["items"]) >= 1


class TestDoraThirdPartyProviders:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/dora/third-party-providers")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/dora/third-party-providers")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_provider_name(self, client):
        resp = await client.get("/v1/dora/third-party-providers")
        data = resp.json()
        names = [p["provider_name"] for p in data["items"]]
        assert "Amazon Web Services EU" in names

    @pytest.mark.asyncio
    async def test_campo_criticality(self, client):
        resp = await client.get("/v1/dora/third-party-providers")
        data = resp.json()
        criticalities = [p["criticality_assessment"] for p in data["items"]]
        assert "critical" in criticalities


class TestDoraIctRiskRegister:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/dora/ict-risk-registers")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/dora/ict-risk-registers")
        data = resp.json()
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_campo_risk_description(self, client):
        resp = await client.get("/v1/dora/ict-risk-registers")
        data = resp.json()
        assert "proveedor cloud" in data["items"][0]["risk_description"]


class TestDoraPenetrationTests:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/dora/penetration-tests")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/dora/penetration-tests")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_test_type(self, client):
        resp = await client.get("/v1/dora/penetration-tests")
        data = resp.json()
        types = [t["test_type"] for t in data["items"]]
        assert "black_box" in types
        assert "white_box" in types

    @pytest.mark.asyncio
    async def test_campo_critical_findings(self, client):
        resp = await client.get("/v1/dora/penetration-tests")
        data = resp.json()
        criticals = [t["critical_findings"] for t in data["items"]]
        assert 2 in criticals
        assert 0 in criticals


class TestDoraIncidentClassificationFramework:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/dora/incident-classification-frameworks")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/dora/incident-classification-frameworks")
        data = resp.json()
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_campo_framework_version(self, client):
        resp = await client.get("/v1/dora/incident-classification-frameworks")
        data = resp.json()
        versions = [f["framework_version"] for f in data["items"]]
        assert "1.0" in versions
