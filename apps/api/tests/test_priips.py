"""Tests para el router de PRIIPs / LIVMC.

Fase 31.8 — Expansion regulatoria.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent / "workers"))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy import text

PRIIPS_SEED_SQL = [
    """
    INSERT INTO priips_kid (product_id, product_type, currency, risk_scale, cost_impact, negative_scenario_returns, version, publication_date, status)
    VALUES (101, 'fondo_inversion', 'EUR', 6, '{"entry_fee_pct": 0.0, "ongoing_cost_pct": 1.85}', '{"stress_1y": -0.35}', '2024.1', '2024-01-15', 'active')
    """,
    """
    INSERT INTO priips_kid (product_id, product_type, currency, risk_scale, cost_impact, negative_scenario_returns, version, publication_date, status)
    VALUES (102, 'etf', 'EUR', 3, '{"entry_fee_pct": 0.0, "ongoing_cost_pct": 0.25}', '{"stress_1y": -0.15}', '2024.1', '2024-02-01', 'active')
    """,
    """
    INSERT INTO priips_product (issuer_id, product_name, underlying_assets, maturity_date, currency, min_investment, distribution_channels, status)
    VALUES (1, 'Fondo Renta Variable Europa', '[{"type": "equity", "region": "Europa", "weight_pct": 100}]', NULL, 'EUR', 3000.0, '["banco", "banca_online"]', 'active')
    """,
    """
    INSERT INTO priips_product (issuer_id, product_name, underlying_assets, maturity_date, currency, min_investment, distribution_channels, status)
    VALUES (2, 'ETF Euro Stoxx 50', '[{"type": "index", "name": "Euro Stoxx 50", "weight_pct": 100}]', NULL, 'EUR', 100.0, '["plataforma_online", "banco"]', 'active')
    """,
    """
    INSERT INTO livmc_client_protection (client_id, protection_type, provider_id, coverage_amount, status)
    VALUES (1, 'dispute-resolution', 1, 20000.0, 'active')
    """,
    """
    INSERT INTO livmc_client_protection (client_id, protection_type, provider_id, coverage_amount, status)
    VALUES (2, 'mediation', 2, 50000.0, 'active')
    """,
    """
    INSERT INTO livmc_voice_procedure (entity_id, procedure_type, description, effective_date, next_review, status)
    VALUES (1, 'quejas_clientes', 'Procedimiento de gestion de quejas conforme a art. 10 LivMC', '2024-01-01', '2025-01-01', 'active')
    """,
    """
    INSERT INTO livmc_voice_procedure (entity_id, procedure_type, description, effective_date, next_review, status)
    VALUES (2, 'reclamaciones', 'Procedimiento de reclamaciones ante CNMV', '2024-01-01', '2025-01-01', 'active')
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_priips():
    """Semilla basica de datos PRIIPs/LIVMC para tests del router."""
    from db import engine

    with engine.begin() as conn:
        for sql in PRIIPS_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM livmc_voice_procedure"))
        conn.execute(text("DELETE FROM livmc_client_protection"))
        conn.execute(text("DELETE FROM priips_product"))
        conn.execute(text("DELETE FROM priips_kid"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestPriipsKids:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/priips/kids")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/priips/kids")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_product_type(self, client):
        resp = await client.get("/v1/priips/kids")
        data = resp.json()
        types = [k["product_type"] for k in data["items"]]
        assert "fondo_inversion" in types
        assert "etf" in types

    @pytest.mark.asyncio
    async def test_campo_risk_scale(self, client):
        resp = await client.get("/v1/priips/kids")
        data = resp.json()
        scales = [k["risk_scale"] for k in data["items"]]
        assert 6 in scales
        assert 3 in scales

    @pytest.mark.asyncio
    async def test_campo_cost_impact_json(self, client):
        resp = await client.get("/v1/priips/kids")
        data = resp.json()
        costs = data["items"][0]["cost_impact"]
        if isinstance(costs, str):
            costs = json.loads(costs)
        assert "ongoing_cost_pct" in costs

    @pytest.mark.asyncio
    async def test_filtro_product_type(self, client):
        resp = await client.get("/v1/priips/kids", params={"product_type": "etf"})
        data = resp.json()
        assert len(data["items"]) >= 1
        for k in data["items"]:
            assert k["product_type"] == "etf"


class TestPriipsProducts:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/priips/products")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/priips/products")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_product_name(self, client):
        resp = await client.get("/v1/priips/products")
        data = resp.json()
        names = [p["product_name"] for p in data["items"]]
        assert "Fondo Renta Variable Europa" in names

    @pytest.mark.asyncio
    async def test_campo_currency(self, client):
        resp = await client.get("/v1/priips/products")
        data = resp.json()
        for p in data["items"]:
            assert p["currency"] == "EUR"


class TestLivmcClientProtections:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/priips/client-protections")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/priips/client-protections")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_protection_type(self, client):
        resp = await client.get("/v1/priips/client-protections")
        data = resp.json()
        types = [p["protection_type"] for p in data["items"]]
        assert "dispute-resolution" in types
        assert "mediation" in types

    @pytest.mark.asyncio
    async def test_campo_coverage_amount(self, client):
        resp = await client.get("/v1/priips/client-protections")
        data = resp.json()
        amounts = [p["coverage_amount"] for p in data["items"]]
        assert 20000.0 in amounts
        assert 50000.0 in amounts


class TestLivmcVoiceProcedures:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/priips/voice-procedures")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/priips/voice-procedures")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_procedure_type(self, client):
        resp = await client.get("/v1/priips/voice-procedures")
        data = resp.json()
        types = [p["procedure_type"] for p in data["items"]]
        assert "quejas_clientes" in types
        assert "reclamaciones" in types

    @pytest.mark.asyncio
    async def test_campo_description(self, client):
        resp = await client.get("/v1/priips/voice-procedures")
        data = resp.json()
        descriptions = [p["description"] for p in data["items"]]
        combined = " ".join(descriptions)
        assert "LivMC" in combined
