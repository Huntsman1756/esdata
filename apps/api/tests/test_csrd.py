"""Tests para el router de CSRD (Corporate Sustainability Reporting Directive).

Fase 31.9.2 — Expansion regulatoria: CSRD.
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

CSRD_SEED_SQL = [
    """
    INSERT INTO csrd_entity_report (id, entity_id, reporting_year, esap_url, assurance_status, reporting_standard, status)
    VALUES
        (1, 101, 2024, 'https://esap.eu/acme-2024.pdf', 'limited', 'ESGAS', 'published'),
        (2, 102, 2024, 'https://esap.eu/iberia-2024.pdf', 'reasonable', 'ESGAS', 'published'),
        (3, 103, 2023, 'https://esap.eu/telefonica-2023.pdf', 'limited', 'ESGAS', 'published');
    """,
    """
    INSERT INTO csrd_esg_data_point (id, report_id, topic, indicator_code, value, unit, scope, verification_status)
    VALUES
        (1, 1, 'environment', 'ESRS E1-10', 12500.0, 'tCO2e', 1, 'verified'),
        (2, 1, 'environment', 'ESRS E1-11', 45000.0, 'tCO2e', 2, 'verified'),
        (3, 1, 'environment', 'ESRS E1-12', 120000.0, 'tCO2e', 3, 'limited'),
        (4, 1, 'social', 'ESRS S1-10', 15200.0, 'headcount', NULL, 'verified'),
        (5, 2, 'environment', 'ESRS E1-10', 8200.0, 'tCO2e', 1, 'verified'),
        (6, 2, 'social', 'ESRS S1-10', 32000.0, 'headcount', NULL, 'verified'),
        (7, 3, 'environment', 'ESRS E1-10', 18500.0, 'tCO2e', 1, 'verified');
    """,
    """
    INSERT INTO csrd_ess (id, standard_code, topic, applicable_from_year, description, status)
    VALUES
        (1, 'ESRS E1', 'Climate change', 2024, 'Emission of greenhouse gases', 'active'),
        (2, 'ESRS E2', 'Pollution', 2025, 'Pollution prevention and control', 'active'),
        (3, 'ESRS S1', 'Own workforce', 2024, 'Working conditions and social', 'active'),
        (4, 'ESRS G1', 'Business conduct', 2024, 'Anti-corruption and governance', 'active');
    """,
    """
    INSERT INTO csrd_double_materiality (id, entity_id, impact_materiality, financial_materiality, assessment_date, key_impacts, key_dependencies, status)
    VALUES
        (1, 101, '{"assessed": true, "impacts": ["GHG", "waste"]}', '{"assessed": true, "risks": ["carbon pricing"]}', '2024-06-15', 'GHG emissions, waste', 'Raw materials, labor', 'published'),
        (2, 102, '{"assessed": true, "impacts": ["aviation emissions"]}', '{"assessed": true, "risks": ["fuel prices"]}', '2024-07-01', 'CO2 from flights', 'Fuel supply', 'published');
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_csrd():
    """Semilla basica de datos CSRD para tests del router."""
    from db import engine

    with engine.begin() as conn:
        for sql in CSRD_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM csrd_double_materiality"))
        conn.execute(text("DELETE FROM csrd_ess"))
        conn.execute(text("DELETE FROM csrd_esg_data_point"))
        conn.execute(text("DELETE FROM csrd_entity_report"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ===========================================================================
# Entity Reports
# ===========================================================================


class TestCsrdEntityReports:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/csrd/entity-reports")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/csrd/entity-reports")
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_campo_entity_id(self, client):
        resp = await client.get("/v1/csrd/entity-reports")
        data = resp.json()
        ids = [i["entity_id"] for i in data["items"]]
        assert 101 in ids or 102 in ids or 103 in ids

    @pytest.mark.asyncio
    async def test_campo_reporting_year(self, client):
        resp = await client.get("/v1/csrd/entity-reports")
        data = resp.json()
        years = [i["reporting_year"] for i in data["items"]]
        assert 2024 in years or 2023 in years

    @pytest.mark.asyncio
    async def test_campo_status(self, client):
        resp = await client.get("/v1/csrd/entity-reports")
        data = resp.json()
        for r in data["items"]:
            assert r["status"] in ("draft", "published")

    @pytest.mark.asyncio
    async def test_filtro_reporting_year(self, client):
        resp = await client.get("/v1/csrd/entity-reports", params={"reporting_year": 2024})
        data = resp.json()
        assert len(data["items"]) >= 2
        years = [i["reporting_year"] for i in data["items"]]
        assert all(y == 2024 for y in years)

    @pytest.mark.asyncio
    async def test_filtro_entity_id(self, client):
        resp = await client.get("/v1/csrd/entity-reports", params={"entity_id": 101})
        data = resp.json()
        assert len(data["items"]) >= 1
        entity_ids = [i["entity_id"] for i in data["items"]]
        assert all(e == 101 for e in entity_ids)

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/csrd/entity-reports/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["entity_id"] == 101
        assert data["reporting_year"] == 2024
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_no_encontrado(self, client):
        resp = await client.get("/v1/csrd/entity-reports/9999")
        assert resp.status_code == 404


# ===========================================================================
# ESG Data Points
# ===========================================================================


class TestCsrdEsgDataPoints:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/csrd/esg-data-points")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/csrd/esg-data-points")
        data = resp.json()
        assert len(data["items"]) >= 7

    @pytest.mark.asyncio
    async def test_campo_topic(self, client):
        resp = await client.get("/v1/csrd/esg-data-points")
        data = resp.json()
        topics = set(i["topic"] for i in data["items"])
        assert "environment" in topics
        assert "social" in topics

    @pytest.mark.asyncio
    async def test_campo_value(self, client):
        resp = await client.get("/v1/csrd/esg-data-points")
        data = resp.json()
        for r in data["items"]:
            assert "value" in r or r["value"] is None

    @pytest.mark.asyncio
    async def test_filtro_topic(self, client):
        resp = await client.get("/v1/csrd/esg-data-points", params={"topic": "environment"})
        data = resp.json()
        assert len(data["items"]) >= 5
        topics = [i["topic"] for i in data["items"]]
        assert all(t == "environment" for t in topics)

    @pytest.mark.asyncio
    async def test_filtro_report_id(self, client):
        resp = await client.get("/v1/csrd/esg-data-points", params={"report_id": 1})
        data = resp.json()
        assert len(data["items"]) >= 4
        report_ids = [i["report_id"] for i in data["items"]]
        assert all(r == 1 for r in report_ids)

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/csrd/esg-data-points/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["report_id"] == 1
        assert data["topic"] == "environment"
        assert data["value"] == 12500.0
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_no_encontrado(self, client):
        resp = await client.get("/v1/csrd/esg-data-points/9999")
        assert resp.status_code == 404


# ===========================================================================
# ES Standards
# ===========================================================================


class TestCsrdEss:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/csrd/ess")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/csrd/ess")
        data = resp.json()
        assert len(data["items"]) >= 4

    @pytest.mark.asyncio
    async def test_campo_standard_code(self, client):
        resp = await client.get("/v1/csrd/ess")
        data = resp.json()
        codes = [i["standard_code"] for i in data["items"]]
        assert "ESRS E1" in codes

    @pytest.mark.asyncio
    async def test_filtro_topic(self, client):
        resp = await client.get("/v1/csrd/ess", params={"topic": "Climate change"})
        data = resp.json()
        assert len(data["items"]) >= 1
        topics = [i["topic"] for i in data["items"]]
        assert all(t == "Climate change" for t in topics)

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/csrd/ess/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["standard_code"] == "ESRS E1"
        assert data["topic"] == "Climate change"
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_no_encontrado(self, client):
        resp = await client.get("/v1/csrd/ess/9999")
        assert resp.status_code == 404


# ===========================================================================
# Double Materiality
# ===========================================================================


class TestCsrdDoubleMateriality:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/csrd/double-materiality")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/csrd/double-materiality")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_entity_id(self, client):
        resp = await client.get("/v1/csrd/double-materiality")
        data = resp.json()
        entity_ids = [i["entity_id"] for i in data["items"]]
        assert 101 in entity_ids or 102 in entity_ids

    @pytest.mark.asyncio
    async def test_campo_impact_materiality(self, client):
        resp = await client.get("/v1/csrd/double-materiality")
        data = resp.json()
        for r in data["items"]:
            assert "impact_materiality" in r
            assert "financial_materiality" in r

    @pytest.mark.asyncio
    async def test_filtro_entity_id(self, client):
        resp = await client.get("/v1/csrd/double-materiality", params={"entity_id": 101})
        data = resp.json()
        assert len(data["items"]) >= 1
        entity_ids = [i["entity_id"] for i in data["items"]]
        assert all(e == 101 for e in entity_ids)

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/csrd/double-materiality/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["entity_id"] == 101
        assert "impact_materiality" in data
        assert "financial_materiality" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_no_encontrado(self, client):
        resp = await client.get("/v1/csrd/double-materiality/9999")
        assert resp.status_code == 404
