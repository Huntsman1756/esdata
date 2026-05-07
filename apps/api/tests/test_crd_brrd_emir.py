"""Tests para los routers de CRD V/CRR, BRRD y EMIR.

Fase 31.9.4 — Expansion regulatoria: CRD V/CRR, BRRD, EMIR.

Cobertura:
- CRD/CRR capital positions: list, get, create, update, 404 (4)
- CRD stress tests: list, get, create, update, 404 (5)
- BRRD bail-in: list, get, create, update, 404 (5)
- EMIR trade reports: list, get, create, update, 404 (5)
- EMIR clearing members: list, get, create, update, 404 (5)

Total: 37 tests
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent / "workers"))

import os
os.environ["APP_ENV"] = "test"
os.environ["ESDATA_API_KEY"] = "test-secret-key"
os.environ["MCP_API_KEY"] = "test-mcp-key"
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata")
os.environ["ESDATA_ALLOW_INSECURE_TEST_AUTH"] = "true"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy import text

CRD_BRRD_EMIR_SEED_SQL = [
    """
    INSERT INTO crd_capital_position (id, entity_id, reporting_date, cet1_ratio, tier1_ratio, total_capital_ratio, cet1_amount, tier1_amount, total_capital_amount, leverage_ratio, risk_weighted_assets, status)
    VALUES
        (1, 1, '2025-09-30', 14.5, 16.2, 18.7, 8500000000.00, 9500000000.00, 10950000000.00, 5.8, 58600000000.00, 'filed'),
        (2, 2, '2025-09-30', 13.2, 15.1, 17.3, 4200000000.00, 4800000000.00, 5500000000.00, 4.9, 32400000000.00, 'filed'),
        (3, 3, '2025-06-30', 15.1, 17.0, 19.4, 12300000000.00, 13800000000.00, 15700000000.00, 6.2, 78900000000.00, 'filed')
    ON CONFLICT (id) DO NOTHING;
    """,
    """
    INSERT INTO crd_stress_test (id, entity_id, test_date, scenario_name, cet1_impact_pct, tier1_impact_pct, capital_ratio_post_test, competent_authority, status)
    VALUES
        (1, 1, '2025-07-15', 'ECB Joint EU-wide stress test 2025', -2.8, -2.5, 11.7, 'Banco de Espana', 'published'),
        (2, 2, '2025-07-15', 'ECB Joint EU-wide stress test 2025', -3.1, -2.9, 10.1, 'Banco de Espana', 'published'),
        (3, 3, '2025-03-10', 'Banco de Espana national stress test 2025', -2.2, -2.0, 12.9, 'Banco de Espana', 'published')
    ON CONFLICT (id) DO NOTHING;
    """,
    """
    INSERT INTO brrd_bail_in (id, entity_id, total_eligible_liabilities, mrel_target_pct, mrel_compliance_pct, internal_mrel, resolution_status, status)
    VALUES
        (1, 1, 85000000000.00, 31.5, 32.1, 28.4, 'compliant', 'active'),
        (2, 2, 42000000000.00, 28.0, 27.5, 25.1, 'non_compliant', 'active'),
        (3, 3, 120000000000.00, 33.0, 34.2, 30.8, 'compliant', 'active')
    ON CONFLICT (id) DO NOTHING;
    """,
    """
    INSERT INTO emir_trade_report (id, trade_id, asset_class, instrument_class, clearing_obligation_applied, reporting_delay_days, counterparty_type, status)
    VALUES
        (1, 'EMIR-2025-001-XYZ', 'credit', 'CDS', true, 1, 'financial', 'reported'),
        (2, 'EMIR-2025-002-ABC', 'interest-rate', 'IRS', true, 0, 'financial', 'reported'),
        (3, 'EMIR-2025-003-DEF', 'equity', 'TRC', false, 2, 'non-financial', 'reported')
    ON CONFLICT (id) DO NOTHING;
    """,
    """
    INSERT INTO emir_clearing_member (id, entity_id, emir_registration, clearing_type, status)
    VALUES
        (1, 1, 'EMIR-CM-2024-00123', 'central', 'active'),
        (2, 2, 'EMIR-CM-2024-00456', 'otc', 'active'),
        (3, 3, 'EMIR-CM-2024-00789', 'central', 'active')
    ON CONFLICT (id) DO NOTHING;
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_crd_brrd_emir():
    """Seed CRD/BRRD/EMIR data for all tests."""
    from db import engine

    with engine.begin() as conn:
        for sql in CRD_BRRD_EMIR_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM emir_clearing_member"))
        conn.execute(text("DELETE FROM emir_trade_report"))
        conn.execute(text("DELETE FROM brrd_bail_in"))
        conn.execute(text("DELETE FROM crd_stress_test"))
        conn.execute(text("DELETE FROM crd_capital_position"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-mcp-key",
            "accept": "application/json",
            "content-type": "application/json",
        },
    ) as client:
        yield client


# =============================================================================
# CRD/CRR — Capital Position Tests
# =============================================================================

class TestCrdCapitalPositionsList:
    @pytest.mark.asyncio
    async def test_list_all(self, client):
        resp = await client.get("/v1/crd/capital-positions")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == len(data["items"])
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_filter_by_entity_id(self, client):
        resp = await client.get("/v1/crd/capital-positions?entity_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["entity_id"] == 1

    @pytest.mark.asyncio
    async def test_filter_by_status(self, client):
        resp = await client.get("/v1/crd/capital-positions?status=filed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        for item in data["items"]:
            assert item["status"] == "filed"


class TestCrdCapitalPositionGet:
    @pytest.mark.asyncio
    async def test_get_existing(self, client):
        resp = await client.get("/v1/crd/capital-positions/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == 1
        assert data["cet1_ratio"] == 14.5
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_404(self, client):
        resp = await client.get("/v1/crd/capital-positions/9999")
        assert resp.status_code == 404


class TestCrdCapitalPositionCreate:
    @pytest.mark.asyncio
    async def test_create(self, client):
        resp = await client.post("/v1/crd/capital-positions", json={
            "entity_id": 99,
            "reporting_date": "2025-12-31",
            "cet1_ratio": 12.0,
            "tier1_ratio": 14.0,
            "total_capital_ratio": 16.0,
            "status": "filed",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["entity_id"] == 99
        assert data["cet1_ratio"] == 12.0
        assert data["status"] == "filed"


class TestCrdCapitalPositionUpdate:
    @pytest.mark.asyncio
    async def test_update(self, client):
        resp = await client.put("/v1/crd/capital-positions/1", json={
            "cet1_ratio": 15.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["cet1_ratio"] == 15.0

    @pytest.mark.asyncio
    async def test_update_404(self, client):
        resp = await client.put("/v1/crd/capital-positions/9999", json={
            "cet1_ratio": 15.0,
        })
        assert resp.status_code == 404


# =============================================================================
# CRD — Stress Test Tests
# =============================================================================

class TestCrdStressTestsList:
    @pytest.mark.asyncio
    async def test_list_all(self, client):
        resp = await client.get("/v1/crd/stress-tests")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_filter_by_entity_id(self, client):
        resp = await client.get("/v1/crd/stress-tests?entity_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["entity_id"] == 1


class TestCrdStressTestGet:
    @pytest.mark.asyncio
    async def test_get_existing(self, client):
        resp = await client.get("/v1/crd/stress-tests/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == 1
        assert "ECB" in data["scenario_name"]
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_404(self, client):
        resp = await client.get("/v1/crd/stress-tests/9999")
        assert resp.status_code == 404


class TestCrdStressTestCreate:
    @pytest.mark.asyncio
    async def test_create(self, client):
        resp = await client.post("/v1/crd/stress-tests", json={
            "entity_id": 99,
            "test_date": "2025-11-01",
            "scenario_name": "Custom stress test",
            "cet1_impact_pct": -1.5,
            "status": "published",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["entity_id"] == 99
        assert data["scenario_name"] == "Custom stress test"


class TestCrdStressTestUpdate:
    @pytest.mark.asyncio
    async def test_update(self, client):
        resp = await client.put("/v1/crd/stress-tests/1", json={
            "scenario_name": "Updated scenario",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenario_name"] == "Updated scenario"

    @pytest.mark.asyncio
    async def test_update_404(self, client):
        resp = await client.put("/v1/crd/stress-tests/9999", json={
            "scenario_name": "Updated",
        })
        assert resp.status_code == 404


# =============================================================================
# BRRD — Bail-In Tests
# =============================================================================

class TestBrrdBailInList:
    @pytest.mark.asyncio
    async def test_list_all(self, client):
        resp = await client.get("/v1/crd/bail-in")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_filter_by_entity_id(self, client):
        resp = await client.get("/v1/crd/bail-in?entity_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["entity_id"] == 1


class TestBrrdBailInGet:
    @pytest.mark.asyncio
    async def test_get_existing(self, client):
        resp = await client.get("/v1/crd/bail-in/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == 1
        assert data["mrel_target_pct"] == 31.5
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_404(self, client):
        resp = await client.get("/v1/crd/bail-in/9999")
        assert resp.status_code == 404


class TestBrrdBailInCreate:
    @pytest.mark.asyncio
    async def test_create(self, client):
        resp = await client.post("/v1/crd/bail-in", json={
            "entity_id": 99,
            "total_eligible_liabilities": 50000000000.00,
            "mrel_target_pct": 30.0,
            "mrel_compliance_pct": 31.0,
            "status": "active",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["entity_id"] == 99
        assert data["mrel_target_pct"] == 30.0


class TestBrrdBailInUpdate:
    @pytest.mark.asyncio
    async def test_update(self, client):
        resp = await client.put("/v1/crd/bail-in/1", json={
            "mrel_compliance_pct": 33.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["mrel_compliance_pct"] == 33.0

    @pytest.mark.asyncio
    async def test_update_404(self, client):
        resp = await client.put("/v1/crd/bail-in/9999", json={
            "mrel_compliance_pct": 33.0,
        })
        assert resp.status_code == 404


# =============================================================================
# EMIR — Trade Report Tests
# =============================================================================

class TestEmirTradeReportsList:
    @pytest.mark.asyncio
    async def test_list_all(self, client):
        resp = await client.get("/v1/emir/trade-reports")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_filter_by_asset_class(self, client):
        resp = await client.get("/v1/emir/trade-reports?asset_class=credit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["asset_class"] == "credit"

    @pytest.mark.asyncio
    async def test_filter_by_counterparty_type(self, client):
        resp = await client.get("/v1/emir/trade-reports?counterparty_type=financial")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["counterparty_type"] == "financial"


class TestEmirTradeReportGet:
    @pytest.mark.asyncio
    async def test_get_existing(self, client):
        resp = await client.get("/v1/emir/trade-reports/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trade_id"] == "EMIR-2025-001-XYZ"
        assert data["asset_class"] == "credit"
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_404(self, client):
        resp = await client.get("/v1/emir/trade-reports/9999")
        assert resp.status_code == 404


class TestEmirTradeReportCreate:
    @pytest.mark.asyncio
    async def test_create(self, client):
        resp = await client.post("/v1/emir/trade-reports", json={
            "trade_id": "EMIR-2025-999-NEW",
            "asset_class": "fx",
            "instrument_class": "FX Swap",
            "clearing_obligation_applied": False,
            "counterparty_type": "non-financial",
            "status": "reported",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["trade_id"] == "EMIR-2025-999-NEW"
        assert data["asset_class"] == "fx"


class TestEmirTradeReportUpdate:
    @pytest.mark.asyncio
    async def test_update(self, client):
        resp = await client.put("/v1/emir/trade-reports/1", json={
            "clearing_obligation_applied": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["clearing_obligation_applied"] is False

    @pytest.mark.asyncio
    async def test_update_404(self, client):
        resp = await client.put("/v1/emir/trade-reports/9999", json={
            "clearing_obligation_applied": True,
        })
        assert resp.status_code == 404


# =============================================================================
# EMIR — Clearing Member Tests
# =============================================================================

class TestEmirClearingMembersList:
    @pytest.mark.asyncio
    async def test_list_all(self, client):
        resp = await client.get("/v1/emir/clearing-members")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_filter_by_clearing_type(self, client):
        resp = await client.get("/v1/emir/clearing-members?clearing_type=central")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["clearing_type"] == "central"


class TestEmirClearingMemberGet:
    @pytest.mark.asyncio
    async def test_get_existing(self, client):
        resp = await client.get("/v1/emir/clearing-members/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == 1
        assert data["clearing_type"] == "central"
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_404(self, client):
        resp = await client.get("/v1/emir/clearing-members/9999")
        assert resp.status_code == 404


class TestEmirClearingMemberCreate:
    @pytest.mark.asyncio
    async def test_create(self, client):
        resp = await client.post("/v1/emir/clearing-members", json={
            "entity_id": 99,
            "emir_registration": "EMIR-CM-2025-999",
            "clearing_type": "otc",
            "status": "active",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["entity_id"] == 99
        assert data["clearing_type"] == "otc"


class TestEmirClearingMemberUpdate:
    @pytest.mark.asyncio
    async def test_update(self, client):
        resp = await client.put("/v1/emir/clearing-members/1", json={
            "status": "suspended",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "suspended"

    @pytest.mark.asyncio
    async def test_update_404(self, client):
        resp = await client.put("/v1/emir/clearing-members/9999", json={
            "status": "suspended",
        })
        assert resp.status_code == 404
