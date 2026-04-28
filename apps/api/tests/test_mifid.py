"""Tests para el router de MiFID II/MiFIR.

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

# --- Seed de datos MiFID II/MiFIR ---

MIFID_SEED_SQL = [
    """
    INSERT INTO mifid_client_category (id, entity_id, category, assessment_date, knowledge_level, experience_level, status)
    VALUES (1, 1, 'retail', '2024-01-15', 'bajo', 'limitado', 'active')
    """,
    """
    INSERT INTO mifid_client_category (id, entity_id, category, assessment_date, knowledge_level, experience_level, status)
    VALUES (2, 2, 'professional', '2024-02-01', 'alto', 'extenso', 'active')
    """,
    """
    INSERT INTO mifid_suitability_report (id, client_id, product_id, assessment_date, suitability_score, recommendation, advisor_id, status)
    VALUES (1, 1, 101, '2024-01-20', 3, 'no_recommended', 1, 'active')
    """,
    """
    INSERT INTO mifid_suitability_report (id, client_id, product_id, assessment_date, suitability_score, recommendation, advisor_id, status)
    VALUES (2, 2, 102, '2024-02-05', 8, 'recommended', 2, 'active')
    """,
    """
    INSERT INTO mifid_best_execution_record (id, order_id, venue, execution_price, market_impact, speed_ms, quality_metrics, execution_timestamp, status)
    VALUES (1, 5001, 'BME', 15.45, 0.0023, 45, '{"slippage": 0.001}', '2024-03-01 10:30:00+01', 'active')
    """,
    """
    INSERT INTO mifid_conflict_of_interest_registry (id, department, conflict_type, description, mitigation_measure, identified_date, review_date, status)
    VALUES (1, 'trading', 'personal_dealing', 'Empleados con posiciones en instrumentos', 'pre-clearing', '2024-01-10', '2024-07-10', 'active')
    """,
    """
    INSERT INTO mifid_product_governance (id, product_id, target_market, distribution_channels, key_features, risk_level, review_date, status)
    VALUES (1, 101, 'investidor_profesional', '["distribuidor_bancario"]', 'derivados complejos', 6, '2024-12-31', 'active')
    """,
    """
    INSERT INTO mifid_order_record (id, client_id, instrument, direction, quantity, price, timestamp, venue, status, retention_until)
    VALUES (1, 1, 'IBE.MC', 'buy', 100, 15.42, '2024-03-01 10:29:55+01', 'BME', 'executed', '2029-03-01')
    """,
    """
    INSERT INTO mifid_insider_list (id, insider_name, insider_tin, entity_id, inside_information_description, date_created, status)
    VALUES (1, 'Maria Garcia', '12345678A', 1, 'Plan de adquisicion de participaciones', '2024-01-20', 'active')
    """,
    """
    INSERT INTO mifid_compensation_policy (id, entity_id, policy_version, alignment_score, risk_adjustment_applied, approval_date, next_review, status)
    VALUES (1, 1, '2024.1', 85, true, '2024-01-01', '2025-01-01', 'active')
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_mifid():
    """Semilla basica de datos MiFID para tests del router."""
    from db import engine

    with engine.begin() as conn:
        for sql in MIFID_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mifid_compensation_policy"))
        conn.execute(text("DELETE FROM mifid_insider_list"))
        conn.execute(text("DELETE FROM mifid_order_record"))
        conn.execute(text("DELETE FROM mifid_product_governance"))
        conn.execute(text("DELETE FROM mifid_conflict_of_interest_registry"))
        conn.execute(text("DELETE FROM mifid_best_execution_record"))
        conn.execute(text("DELETE FROM mifid_suitability_report"))
        conn.execute(text("DELETE FROM mifid_client_category"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestMifidClientCategories:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mifid/client-categories")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_model(self, client):
        resp = await client.get("/v1/mifid/client-categories")
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mifid/client-categories")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_category(self, client):
        resp = await client.get("/v1/mifid/client-categories")
        data = resp.json()
        categorias = [c["category"] for c in data["items"]]
        assert "retail" in categorias
        assert "professional" in categorias

    @pytest.mark.asyncio
    async def test_filtro_status(self, client):
        resp = await client.get("/v1/mifid/client-categories", params={"status": "active"})
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_filtro_category(self, client):
        resp = await client.get("/v1/mifid/client-categories", params={"category": "retail"})
        data = resp.json()
        assert len(data["items"]) >= 1
        for c in data["items"]:
            assert c["category"] == "retail"

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/mifid/client-categories/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == 1
        assert data["category"] == "retail"

    @pytest.mark.asyncio
    async def test_get_404(self, client):
        resp = await client.get("/v1/mifid/client-categories/99999")
        assert resp.status_code == 404


class TestMifidSuitabilityReports:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mifid/suitability-reports")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mifid/suitability-reports")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_recommendation(self, client):
        resp = await client.get("/v1/mifid/suitability-reports")
        data = resp.json()
        recs = [r["recommendation"] for r in data["items"]]
        assert "recommended" in recs
        assert "no_recommended" in recs

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/mifid/suitability-reports/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["client_id"] == 1


class TestMifidBestExecution:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mifid/best-execution-records")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mifid/best-execution-records")
        data = resp.json()
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_campo_venue(self, client):
        resp = await client.get("/v1/mifid/best-execution-records")
        data = resp.json()
        venues = [r["venue"] for r in data["items"]]
        assert "BME" in venues


class TestMifidConflictsOfInterest:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mifid/conflict-of-interest")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mifid/conflict-of-interest")
        data = resp.json()
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_campo_conflict_type(self, client):
        resp = await client.get("/v1/mifid/conflict-of-interest")
        data = resp.json()
        types = [c["conflict_type"] for c in data["items"]]
        assert "personal_dealing" in types


class TestMifidProductGovernance:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mifid/product-governance")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mifid/product-governance")
        data = resp.json()
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_campo_risk_level(self, client):
        resp = await client.get("/v1/mifid/product-governance")
        data = resp.json()
        risk_levels = [r["risk_level"] for r in data["items"]]
        assert 6 in risk_levels


class TestMifidOrderRecords:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mifid/order-records")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mifid/order-records")
        data = resp.json()
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_campo_instrument(self, client):
        resp = await client.get("/v1/mifid/order-records")
        data = resp.json()
        instruments = [r["instrument"] for r in data["items"]]
        assert "IBE.MC" in instruments


class TestMifidInsiderLists:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mifid/insider-lists")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mifid/insider-lists")
        data = resp.json()
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_campo_insider_name(self, client):
        resp = await client.get("/v1/mifid/insider-lists")
        data = resp.json()
        names = [i["insider_name"] for i in data["items"]]
        assert "Maria Garcia" in names


class TestMifidCompensationPolicies:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mifid/compensation-policies")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mifid/compensation-policies")
        data = resp.json()
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_campo_alignment_score(self, client):
        resp = await client.get("/v1/mifid/compensation-policies")
        data = resp.json()
        scores = [p["alignment_score"] for p in data["items"]]
        assert 85 in scores
