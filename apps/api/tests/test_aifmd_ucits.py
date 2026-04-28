"""Tests para los routers de AIFMD y UCITS.

Fase 31.9.3 — Expansion regulatoria: AIFMD y UCITS.
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

AIFMD_UCITS_SEED_SQL = [
    """
    INSERT INTO aifmd_fund (id, fund_name, aifm_id, fund_type, registration_date, home_member_state, cross_border_passport, total_aum_eur, investor_type, lock_up_period, redemption_frequency, leverage_method, leverage_max_pct, status)
    VALUES
        (1, 'Iberian Real Estate Fund', 501, 'real-estate', '2020-03-15', 'ES', true, 250000000.00, 'professional', '2 years', 'quarterly', 'asset-by-asset', 200.00, 'active'),
        (2, 'European Growth Capital III', 502, 'alternative', '2021-06-01', 'DE', true, 780000000.00, 'professional', '5 years', 'annually', 'portfolio', 300.00, 'active'),
        (3, 'Strategic Credit Opportunities', 503, 'alternative', '2019-11-20', 'FR', false, 150000000.00, 'professional', '3 years', 'semi-annually', 'asset-by-asset', 150.00, 'active');
    """,
    """
    INSERT INTO ucits_fund (id, fund_name, management_company, registration_date, home_member_state, cross_border_passport, total_aum_eur, depositary_id, krid_url, investment_strategy, risk_profile, status)
    VALUES
        (1, 'Euro Green Bond Fund', 'Global Asset Management SA', '2018-01-10', 'LU', true, 1200000000.00, 601, 'https://esap.eu/euro-green-krid.pdf', 'Euro-denominated green bonds', '4/7', 'active'),
        (2, 'Iberian Equity Income', 'Iberian Capital Management', '2015-05-20', 'ES', true, 450000000.00, 602, 'https://esap.eu/iberian-equity-krid.pdf', 'Iberian dividend-paying equities', '5/7', 'active'),
        (3, 'Global Tech Leaders UCITS', 'European Wealth Partners', '2020-09-01', 'IE', true, 2800000000.00, 603, 'https://esap.eu/global-tech-krid.pdf', 'Global technology sector equities', '6/7', 'active');
    """,
    """
    INSERT INTO aifmd_regulatory_report (id, fund_id, report_type, reporting_period, url, filed_date, status)
    VALUES
        (1, 1, 'annual', '2024', 'https://esap.eu/iberian-ref-2024.pdf', '2025-03-31', 'filed'),
        (2, 2, 'annual', '2024', 'https://esap.eu/growth-cap-2024.pdf', '2025-04-15', 'filed'),
        (3, 1, 'semi-annual', '2024-H1', 'https://esap.eu/iberian-ref-2024-h1.pdf', '2024-07-31', 'filed');
    """,
    """
    INSERT INTO ucits_regulatory_report (id, fund_id, report_type, reporting_period, url, filed_date, status)
    VALUES
        (1, 1, 'annual', '2024', 'https://esap.eu/euro-green-bond-2024.pdf', '2025-03-31', 'filed'),
        (2, 2, 'annual', '2024', 'https://esap.eu/iberian-equity-2024.pdf', '2025-04-30', 'filed'),
        (3, 3, 'annual', '2024', 'https://esap.eu/global-tech-2024.pdf', '2025-03-15', 'filed');
    """,
    """
    INSERT INTO aifmd_liquidity_management (id, fund_id, redemption_suspended, suspension_date, gating_applied, swing_price_applied, side_pocket_applied, stress_test_result, valuation_frequency)
    VALUES
        (1, 1, false, NULL, false, false, false, 'pass', 'quarterly'),
        (2, 2, false, NULL, true, false, true, 'pass_with_conditions', 'annually'),
        (3, 3, true, '2024-08-15', true, true, false, 'fail', 'semi-annually');
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_aifmd_ucits():
    """Semilla basica de datos AIFMD/UCITS para tests del router."""
    from db import engine

    with engine.begin() as conn:
        for sql in AIFMD_UCITS_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM aifmd_liquidity_management"))
        conn.execute(text("DELETE FROM ucits_regulatory_report"))
        conn.execute(text("DELETE FROM aifmd_regulatory_report"))
        conn.execute(text("DELETE FROM ucits_fund"))
        conn.execute(text("DELETE FROM aifmd_fund"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ===========================================================================
# AIFMD Funds
# ===========================================================================


class TestAifmdFunds:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/aifmd/funds")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/aifmd/funds")
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_campo_fund_name(self, client):
        resp = await client.get("/v1/aifmd/funds")
        data = resp.json()
        names = [i["fund_name"] for i in data["items"]]
        assert "Iberian Real Estate Fund" in names

    @pytest.mark.asyncio
    async def test_campo_fund_type(self, client):
        resp = await client.get("/v1/aifmd/funds")
        data = resp.json()
        types = set(i["fund_type"] for i in data["items"])
        assert "real-estate" in types or "alternative" in types

    @pytest.mark.asyncio
    async def test_filtro_fund_type(self, client):
        resp = await client.get("/v1/aifmd/funds", params={"fund_type": "real-estate"})
        data = resp.json()
        assert len(data["items"]) >= 1
        types = [i["fund_type"] for i in data["items"]]
        assert all(t == "real-estate" for t in types)

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/aifmd/funds/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["fund_name"] == "Iberian Real Estate Fund"
        assert data["fund_type"] == "real-estate"
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_no_encontrado(self, client):
        resp = await client.get("/v1/aifmd/funds/9999")
        assert resp.status_code == 404


# ===========================================================================
# AIFMD Regulatory Reports
# ===========================================================================


class TestAifmdRegulatoryReports:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/aifmd/regulatory-reports")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/aifmd/regulatory-reports")
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_campo_fund_id(self, client):
        resp = await client.get("/v1/aifmd/regulatory-reports")
        data = resp.json()
        fund_ids = [i["fund_id"] for i in data["items"]]
        assert 1 in fund_ids or 2 in fund_ids

    @pytest.mark.asyncio
    async def test_filtro_fund_id(self, client):
        resp = await client.get("/v1/aifmd/regulatory-reports", params={"fund_id": 1})
        data = resp.json()
        assert len(data["items"]) >= 2
        fund_ids = [i["fund_id"] for i in data["items"]]
        assert all(f == 1 for f in fund_ids)

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/aifmd/regulatory-reports/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["fund_id"] == 1
        assert data["report_type"] == "annual"
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_no_encontrado(self, client):
        resp = await client.get("/v1/aifmd/regulatory-reports/9999")
        assert resp.status_code == 404


# ===========================================================================
# AIFMD Liquidity Management
# ===========================================================================


class TestAifmdLiquidityManagement:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/aifmd/liquidity-management")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/aifmd/liquidity-management")
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_campo_fund_id(self, client):
        resp = await client.get("/v1/aifmd/liquidity-management")
        data = resp.json()
        fund_ids = [i["fund_id"] for i in data["items"]]
        assert 1 in fund_ids or 2 in fund_ids or 3 in fund_ids

    @pytest.mark.asyncio
    async def test_campo_redemption_suspended(self, client):
        resp = await client.get("/v1/aifmd/liquidity-management")
        data = resp.json()
        for r in data["items"]:
            assert r["redemption_suspended"] in (True, False)

    @pytest.mark.asyncio
    async def test_filtro_fund_id(self, client):
        resp = await client.get("/v1/aifmd/liquidity-management", params={"fund_id": 3})
        data = resp.json()
        assert len(data["items"]) >= 1
        fund_ids = [i["fund_id"] for i in data["items"]]
        assert all(f == 3 for f in fund_ids)

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/aifmd/liquidity-management/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["fund_id"] == 1
        assert data["redemption_suspended"] is False
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_no_encontrado(self, client):
        resp = await client.get("/v1/aifmd/liquidity-management/9999")
        assert resp.status_code == 404


# ===========================================================================
# UCITS Funds
# ===========================================================================


class TestUcitsFunds:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/ucits/funds")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/ucits/funds")
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_campo_fund_name(self, client):
        resp = await client.get("/v1/ucits/funds")
        data = resp.json()
        names = [i["fund_name"] for i in data["items"]]
        assert "Euro Green Bond Fund" in names

    @pytest.mark.asyncio
    async def test_campo_management_company(self, client):
        resp = await client.get("/v1/ucits/funds")
        data = resp.json()
        companies = [i["management_company"] for i in data["items"]]
        assert any(c for c in companies if c)

    @pytest.mark.asyncio
    async def test_filtro_home_member_state(self, client):
        resp = await client.get("/v1/ucits/funds", params={"home_member_state": "LU"})
        data = resp.json()
        assert len(data["items"]) >= 1
        states = [i["home_member_state"] for i in data["items"]]
        assert all(s == "LU" for s in states)

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/ucits/funds/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["fund_name"] == "Euro Green Bond Fund"
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_no_encontrado(self, client):
        resp = await client.get("/v1/ucits/funds/9999")
        assert resp.status_code == 404


# ===========================================================================
# UCITS Regulatory Reports
# ===========================================================================


class TestUcitsRegulatoryReports:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/ucits/regulatory-reports")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/ucits/regulatory-reports")
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_campo_fund_id(self, client):
        resp = await client.get("/v1/ucits/regulatory-reports")
        data = resp.json()
        fund_ids = [i["fund_id"] for i in data["items"]]
        assert 1 in fund_ids or 2 in fund_ids or 3 in fund_ids

    @pytest.mark.asyncio
    async def test_filtro_fund_id(self, client):
        resp = await client.get("/v1/ucits/regulatory-reports", params={"fund_id": 1})
        data = resp.json()
        assert len(data["items"]) >= 1
        fund_ids = [i["fund_id"] for i in data["items"]]
        assert all(f == 1 for f in fund_ids)

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/ucits/regulatory-reports/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["fund_id"] == 1
        assert data["report_type"] == "annual"
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_no_encontrado(self, client):
        resp = await client.get("/v1/ucits/regulatory-reports/9999")
        assert resp.status_code == 404
