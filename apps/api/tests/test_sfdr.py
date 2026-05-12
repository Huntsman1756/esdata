"""Tests para el router de SFDR (Sustainable Finance Disclosure Regulation).

Fase 31.9.1 — Expansion regulatoria: SFDR.
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

SFDR_SEED_SQL = [
    """
    INSERT INTO sfdr_product (id, product_name, product_type, sustainability_strategy,
        principal_adverse_impact, paci_aggregated, paci_detailed_url,
        distribution_country, status)
    VALUES (1, 'Green Equity Fund SRI', 'art-8', 'Inversion sostenible con criterios ESG integrados',
        'true', '{"sa_1_co2": 150.5, "sa_2_carbon_intensity": 85.2}',
        'https://www.esap-finance.eu/sfdr/paci/green-equity-sri',
        '["ES", "FR", "DE", "PT"]', 'active')
    """,
    """
    INSERT INTO sfdr_product (id, product_name, product_type, sustainability_strategy,
        principal_adverse_impact, paci_aggregated, paci_detailed_url,
        distribution_country, status)
    VALUES (2, 'EU Climate Transition ETF', 'art-8', 'Indice alineado con transicion climatica EU',
        'true', '{"sa_1_co2": 95.0, "sa_3_fossil": 0.05}',
        'https://www.esap-finance.eu/sfdr/paci/climate-transition-etf',
        '["ES", "DE", "NL", "BE"]', 'active')
    """,
    """
    INSERT INTO sfdr_product (id, product_name, product_type, sustainability_strategy,
        principal_adverse_impact, paci_aggregated, paci_detailed_url,
        distribution_country, status)
    VALUES (3, 'Global Impact Fund', 'art-9', 'Inversion de impacto con objetivos ODS',
        'true', '{"sa_1_co2": 50.0, "sa_5_water": 0.02}',
        'https://www.esap-finance.eu/sfdr/paci/global-impact',
        '["ES", "FR", "IT", "PT"]', 'active')
    """,
    """
    INSERT INTO sfdr_product (id, product_name, product_type, sustainability_strategy,
        principal_adverse_impact, paci_aggregated, paci_detailed_url,
        distribution_country, status)
    VALUES (4, 'ESR Equities Europe', 'art-8', 'Acciones Europa con consideracion PCAI',
        'true', '{"sa_1_co2": 120.0}',
        'https://www.esap-finance.eu/sfdr/paci/esr-europe',
        '["ES", "FR", "DE"]', 'active')
    """,
    """
    INSERT INTO sfdr_product (id, product_name, product_type, sustainability_strategy,
        principal_adverse_impact, paci_aggregated, paci_detailed_url,
        distribution_country, status)
    VALUES (5, 'Standard Euro Bond Fund', 'art-6', NULL,
        'false', NULL, NULL,
        '["ES"]', 'active')
    """,
    """
    INSERT INTO sfdr_paci_indicator (product_id, indicator_code, indicator_name,
        value, unit, reference_period, methodology, status)
    VALUES (1, 'sa.1', 'Greenhouse gas emissions', 150.5, 'tCO2e', '2024', 'Scope 1+2', 'active')
    """,
    """
    INSERT INTO sfdr_paci_indicator (product_id, indicator_code, indicator_name,
        value, unit, reference_period, methodology, status)
    VALUES (1, 'sa.2', 'Carbon footprint', 85.2, 'tCO2e/M EUR', '2024', 'Total portfolio', 'active')
    """,
    """
    INSERT INTO sfdr_paci_indicator (product_id, indicator_code, indicator_name,
        value, unit, reference_period, methodology, status)
    VALUES (2, 'sa.1', 'Greenhouse gas emissions', 95.0, 'tCO2e', '2024', 'Scope 1+2', 'active')
    """,
    """
    INSERT INTO sfdr_paci_indicator (product_id, indicator_code, indicator_name,
        value, unit, reference_period, methodology, status)
    VALUES (3, 'sa.1', 'Greenhouse gas emissions', 50.0, 'tCO2e', '2024', 'Scope 1+2+3', 'active')
    """,
    """
    INSERT INTO sfdr_entity_paci (entity_id, reporting_year, aggregated_paci,
        sectoral_decarbonization, status)
    VALUES (1, 2024, '{"sa_1_met": true, "sa_2_met": true}',
        '{"decarbonization_target": "net_zero_2050"}', 'published')
    """,
    """
    INSERT INTO sfdr_entity_paci (entity_id, reporting_year, aggregated_paci,
        sectoral_decarbonization, status)
    VALUES (2, 2024, '{"sa_1_met": true, "sa_3_met": true}',
        '{"transition_alignment": "1.5c"}', 'published')
    """,
    """
    INSERT INTO sfdr_pre_contractual (product_id, document_type, url,
        published_date, version, status)
    VALUES (1, 'KID', 'https://www.esap-finance.eu/documents/green-equity-sri-kid.pdf',
        '2024-01-15', '2024.1', 'active')
    """,
    """
    INSERT INTO sfdr_pre_contractual (product_id, document_type, url,
        published_date, version, status)
    VALUES (1, 'PPI', 'https://www.esap-finance.eu/documents/green-equity-sri-ppi.pdf',
        '2024-01-15', '2024.1', 'active')
    """,
    """
    INSERT INTO sfdr_pre_contractual (product_id, document_type, url,
        published_date, version, status)
    VALUES (3, 'KID', 'https://www.esap-finance.eu/documents/global-impact-kid.pdf',
        '2024-02-01', '2024.1', 'active')
    """,
    """
    INSERT INTO sfdr_annual_report (entity_id, reporting_year, paci_results,
        engagement_activities, good_practice_examples, url, published_date, status)
    VALUES (1, 2024, '{"sa_1_met": true, "sa_2_met": true}',
        'Active engagement with portfolio companies on Scope 3 reduction',
        'Carbon offset program for high-emission holdings',
        'https://www.esap-finance.eu/reports/sfdr-2024-entity-1.pdf',
        '2025-03-31', 'published')
    """,
    """
    INSERT INTO sfdr_annual_report (entity_id, reporting_year, paci_results,
        engagement_activities, good_practice_examples, url, published_date, status)
    VALUES (2, 2024, '{"sa_1_met": true, "sa_3_met": true}',
        'Climate transition alignment monitoring',
        'Net-zero benchmark tracking',
        'https://www.esap-finance.eu/reports/sfdr-2024-entity-2.pdf',
        '2025-04-15', 'published')
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_sfdr():
    """Semilla basica de datos SFDR para tests del router."""
    from db import engine
    from middleware.domain_availability import invalidate_cache

    with engine.begin() as conn:
        for sql in SFDR_SEED_SQL:
            conn.execute(text(sql))
    invalidate_cache()

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM sfdr_annual_report"))
        conn.execute(text("DELETE FROM sfdr_pre_contractual"))
        conn.execute(text("DELETE FROM sfdr_entity_paci"))
        conn.execute(text("DELETE FROM sfdr_paci_indicator"))
        conn.execute(text("DELETE FROM sfdr_product"))
    invalidate_cache()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestSfdrProducts:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/sfdr/products")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/sfdr/products")
        data = resp.json()
        assert len(data["items"]) >= 5

    @pytest.mark.asyncio
    async def test_campo_product_name(self, client):
        resp = await client.get("/v1/sfdr/products")
        data = resp.json()
        names = [i["product_name"] for i in data["items"]]
        assert "Green Equity Fund SRI" in names
        assert "Global Impact Fund" in names

    @pytest.mark.asyncio
    async def test_campo_product_type(self, client):
        resp = await client.get("/v1/sfdr/products")
        data = resp.json()
        types = [i["product_type"] for i in data["items"]]
        assert "art-8" in types
        assert "art-9" in types
        assert "art-6" in types

    @pytest.mark.asyncio
    async def test_filtro_product_type(self, client):
        resp = await client.get("/v1/sfdr/products", params={"product_type": "art-9"})
        data = resp.json()
        assert len(data["items"]) >= 1
        types = [i["product_type"] for i in data["items"]]
        assert all(t == "art-9" for t in types)

    @pytest.mark.asyncio
    async def test_filtro_search(self, client):
        resp = await client.get("/v1/sfdr/products", params={"search": "Green"})
        data = resp.json()
        assert len(data["items"]) >= 1
        names = [i["product_name"] for i in data["items"]]
        assert "Green Equity Fund SRI" in names

    @pytest.mark.asyncio
    async def test_get_product_by_id(self, client):
        resp = await client.get("/v1/sfdr/products/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["product_name"] == "Green Equity Fund SRI"
        assert data["product_type"] == "art-8"

    @pytest.mark.asyncio
    async def test_get_product_404(self, client):
        resp = await client.get("/v1/sfdr/products/9999")
        assert resp.status_code == 404


class TestSfdrPacaiIndicators:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/sfdr/pacai-indicators")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/sfdr/pacai-indicators")
        data = resp.json()
        assert len(data["items"]) >= 4

    @pytest.mark.asyncio
    async def test_campo_indicator_code(self, client):
        resp = await client.get("/v1/sfdr/pacai-indicators")
        data = resp.json()
        codes = [i["indicator_code"] for i in data["items"]]
        assert "sa.1" in codes
        assert "sa.2" in codes

    @pytest.mark.asyncio
    async def test_campo_unit(self, client):
        resp = await client.get("/v1/sfdr/pacai-indicators")
        data = resp.json()
        units = [i["unit"] for i in data["items"] if i["unit"]]
        assert "tCO2e" in units
        assert "tCO2e/M EUR" in units

    @pytest.mark.asyncio
    async def test_filtro_indicator_code(self, client):
        resp = await client.get("/v1/sfdr/pacai-indicators", params={"indicator_code": "sa.1"})
        data = resp.json()
        assert len(data["items"]) >= 1
        codes = [i["indicator_code"] for i in data["items"]]
        assert all(c == "sa.1" for c in codes)


class TestSfdrEntityPaci:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/sfdr/entity-paci")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/sfdr/entity-paci")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_reporting_year(self, client):
        resp = await client.get("/v1/sfdr/entity-paci")
        data = resp.json()
        years = [i["reporting_year"] for i in data["items"]]
        assert 2024 in years

    @pytest.mark.asyncio
    async def test_campo_status(self, client):
        resp = await client.get("/v1/sfdr/entity-paci")
        data = resp.json()
        for r in data["items"]:
            assert r["status"] in ("draft", "published")

    @pytest.mark.asyncio
    async def test_filtro_reporting_year(self, client):
        resp = await client.get("/v1/sfdr/entity-paci", params={"reporting_year": 2024})
        data = resp.json()
        assert len(data["items"]) >= 2


class TestSfdrPreContractual:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/sfdr/pre-contractual")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/sfdr/pre-contractual")
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_campo_document_type(self, client):
        resp = await client.get("/v1/sfdr/pre-contractual")
        data = resp.json()
        types = [i["document_type"] for i in data["items"]]
        assert "KID" in types
        assert "PPI" in types

    @pytest.mark.asyncio
    async def test_campo_status(self, client):
        resp = await client.get("/v1/sfdr/pre-contractual")
        data = resp.json()
        for r in data["items"]:
            assert r["status"] == "active"

    @pytest.mark.asyncio
    async def test_filtro_document_type(self, client):
        resp = await client.get("/v1/sfdr/pre-contractual", params={"document_type": "KID"})
        data = resp.json()
        assert len(data["items"]) >= 1
        types = [i["document_type"] for i in data["items"]]
        assert all(t == "KID" for t in types)


class TestSfdrAnnualReports:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/sfdr/annual-reports")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/sfdr/annual-reports")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_reporting_year(self, client):
        resp = await client.get("/v1/sfdr/annual-reports")
        data = resp.json()
        years = [i["reporting_year"] for i in data["items"]]
        assert 2024 in years

    @pytest.mark.asyncio
    async def test_campo_status(self, client):
        resp = await client.get("/v1/sfdr/annual-reports")
        data = resp.json()
        for r in data["items"]:
            assert r["status"] in ("draft", "published")

    @pytest.mark.asyncio
    async def test_filtro_reporting_year(self, client):
        resp = await client.get("/v1/sfdr/annual-reports", params={"reporting_year": 2024})
        data = resp.json()
        assert len(data["items"]) >= 2
