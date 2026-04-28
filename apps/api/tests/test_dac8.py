"""Tests para el router de DAC8 / DAC9 crypto-asset information exchange.

Cubre: reporting entities, crypto reports, wallet holders.
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

# --- Seed de datos DAC8/DAC9 ---


DAC8_SEED_SQL = [
    """
    INSERT INTO dac_reporting_entity (tin, entity_type, member_state, dac8_registered, dac9_registered, status)
    VALUES ('ESA12345678', 'crypto-asset service provider', 'Spain', true, true, 'active')
    """,
    """
    INSERT INTO dac_reporting_entity (tin, entity_type, member_state, dac8_registered, dac9_registered, status)
    VALUES ('PTA87654321', 'exchange', 'Portugal', true, false, 'active')
    """,
    """
    INSERT INTO dac_reporting_entity (tin, entity_type, member_state, dac8_registered, dac9_registered, status)
    VALUES ('TESTA00000000', 'custodian', 'Spain', false, false, 'inactive')
    """,
    """
    INSERT INTO dac_crypto_report (entity_id, reporting_period, status, crypto_transactions_count, wallet_holders_count)
    VALUES (1, '2025-Q1', 'submitted', 150, 80)
    """,
    """
    INSERT INTO dac_crypto_report (entity_id, reporting_period, status, crypto_transactions_count, wallet_holders_count)
    VALUES (1, '2025-Q2', 'submitted', 200, 95)
    """,
    """
    INSERT INTO dac_crypto_report (entity_id, reporting_period, status, crypto_transactions_count, wallet_holders_count)
    VALUES (2, '2025-Q1', 'draft', 50, 30)
    """,
    """
    INSERT INTO dac_wallet_holder (report_id, wallet_address, holder_tin, holder_member_state, holder_type, total_value_eur, verification_status)
    VALUES (1, '0xABC123DEF456...', 'ESA1111111A', 'Spain', 'individual', 15000.00, 'verified')
    """,
    """
    INSERT INTO dac_wallet_holder (report_id, wallet_address, holder_tin, holder_member_state, holder_type, total_value_eur, verification_status)
    VALUES (1, '0xGHI789JKL012...', 'PTA2222222B', 'Portugal', 'entity', 45000.00, 'pending')
    """,
    """
    INSERT INTO dac_wallet_holder (report_id, wallet_address, holder_tin, holder_member_state, holder_type, total_value_eur, verification_status)
    VALUES (2, '0xMNO345PQR678...', 'ESA3333333C', 'Spain', 'individual', 8000.00, 'verified')
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_dac8():
    """Semilla basica de datos DAC8/DAC9 para tests del router."""
    from db import engine

    with engine.begin() as conn:
        for sql in DAC8_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dac_wallet_holder"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='dac_wallet_holder'"))
        conn.execute(text("DELETE FROM dac_crypto_report"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='dac_crypto_report'"))
        conn.execute(text("DELETE FROM dac_reporting_entity"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='dac_reporting_entity'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ====================================================================
# Test: GET /v1/dac8/reporting-entities (lista)
# ====================================================================


class TestDac8ListReportingEntities:
    @pytest.mark.asyncio
    async def test_reporting_entities_lista_status_200(self, client):
        resp = await client.get("/v1/dac8/reporting-entities")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_reporting_entities_lista_response_model(self, client):
        resp = await client.get("/v1/dac8/reporting-entities")
        data = resp.json()
        assert "entities" in data
        assert isinstance(data["entities"], list)

    @pytest.mark.asyncio
    async def test_reporting_entities_lista_contiene_registros(self, client):
        resp = await client.get("/v1/dac8/reporting-entities")
        data = resp.json()
        assert len(data["entities"]) >= 3

    @pytest.mark.asyncio
    async def test_reporting_entities_campos(self, client):
        resp = await client.get("/v1/dac8/reporting-entities")
        data = resp.json()
        for e in data["entities"]:
            assert "id" in e
            assert "tin" in e
            assert "entity_type" in e
            assert "member_state" in e
            assert "dac8_registered" in e
            assert "dac9_registered" in e
            assert "status" in e

    @pytest.mark.asyncio
    async def test_reporting_entities_filtro_member_state(self, client):
        resp = await client.get("/v1/dac8/reporting-entities", params={"member_state": "Spain"})
        data = resp.json()
        assert len(data["entities"]) >= 2
        for e in data["entities"]:
            assert e["member_state"] == "Spain"

    @pytest.mark.asyncio
    async def test_reporting_entities_filtro_entity_type(self, client):
        resp = await client.get("/v1/dac8/reporting-entities", params={"entity_type": "exchange"})
        data = resp.json()
        assert len(data["entities"]) >= 1
        for e in data["entities"]:
            assert e["entity_type"] == "exchange"

    @pytest.mark.asyncio
    async def test_reporting_entities_filtro_dac8_registered(self, client):
        resp = await client.get("/v1/dac8/reporting-entities", params={"dac8_registered": "true"})
        data = resp.json()
        assert len(data["entities"]) >= 2
        for e in data["entities"]:
            assert e["dac8_registered"] is True

    @pytest.mark.asyncio
    async def test_reporting_entities_filtro_search(self, client):
        resp = await client.get("/v1/dac8/reporting-entities", params={"search": "ESA123"})
        data = resp.json()
        assert len(data["entities"]) >= 1


# ====================================================================
# Test: GET /v1/dac8/reporting-entities/{id} (detalle)
# ====================================================================


class TestDac8GetReportingEntity:
    @pytest.mark.asyncio
    async def test_reporting_entity_detalle_status_200(self, client):
        resp = await client.get("/v1/dac8/reporting-entities/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_reporting_entity_detalle_tin(self, client):
        resp = await client.get("/v1/dac8/reporting-entities/1")
        data = resp.json()
        assert data["tin"] == "ESA12345678"

    @pytest.mark.asyncio
    async def test_reporting_entity_detalle_404(self, client):
        resp = await client.get("/v1/dac8/reporting-entities/9999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/dac8/crypto-reports (lista)
# ====================================================================


class TestDac8ListCryptoReports:
    @pytest.mark.asyncio
    async def test_crypto_reports_lista_status_200(self, client):
        resp = await client.get("/v1/dac8/crypto-reports")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_crypto_reports_lista_response_model(self, client):
        resp = await client.get("/v1/dac8/crypto-reports")
        data = resp.json()
        assert "reports" in data
        assert len(data["reports"]) >= 3

    @pytest.mark.asyncio
    async def test_crypto_reports_campos(self, client):
        resp = await client.get("/v1/dac8/crypto-reports")
        data = resp.json()
        for r in data["reports"]:
            assert "id" in r
            assert "entity_id" in r
            assert "reporting_period" in r
            assert "status" in r
            assert "crypto_transactions_count" in r

    @pytest.mark.asyncio
    async def test_crypto_reports_filtro_status(self, client):
        resp = await client.get("/v1/dac8/crypto-reports", params={"status": "submitted"})
        data = resp.json()
        assert len(data["reports"]) >= 2
        for r in data["reports"]:
            assert r["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_crypto_reports_filtro_reporting_period(self, client):
        resp = await client.get("/v1/dac8/crypto-reports", params={"reporting_period": "2025-Q1"})
        data = resp.json()
        assert len(data["reports"]) >= 2

    @pytest.mark.asyncio
    async def test_crypto_reports_filtro_entity_id(self, client):
        resp = await client.get("/v1/dac8/crypto-reports", params={"entity_id": "1"})
        data = resp.json()
        assert len(data["reports"]) >= 2


# ====================================================================
# Test: GET /v1/dac8/crypto-reports/{id} (detalle)
# ====================================================================


class TestDac8GetCryptoReport:
    @pytest.mark.asyncio
    async def test_crypto_report_detalle_status_200(self, client):
        resp = await client.get("/v1/dac8/crypto-reports/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_crypto_report_detalle_status_value(self, client):
        resp = await client.get("/v1/dac8/crypto-reports/1")
        data = resp.json()
        assert data["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_crypto_report_detalle_404(self, client):
        resp = await client.get("/v1/dac8/crypto-reports/9999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/dac8/wallet-holders (lista)
# ====================================================================


class TestDac8ListWalletHolders:
    @pytest.mark.asyncio
    async def test_wallet_holders_lista_status_200(self, client):
        resp = await client.get("/v1/dac8/wallet-holders")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_wallet_holders_lista_response_model(self, client):
        resp = await client.get("/v1/dac8/wallet-holders")
        data = resp.json()
        assert "holders" in data
        assert len(data["holders"]) >= 3

    @pytest.mark.asyncio
    async def test_wallet_holders_campos(self, client):
        resp = await client.get("/v1/dac8/wallet-holders")
        data = resp.json()
        for h in data["holders"]:
            assert "id" in h
            assert "report_id" in h
            assert "wallet_address" in h
            assert "holder_type" in h
            assert "total_value_eur" in h
            assert "verification_status" in h

    @pytest.mark.asyncio
    async def test_wallet_holders_filtro_holder_type(self, client):
        resp = await client.get("/v1/dac8/wallet-holders", params={"holder_type": "individual"})
        data = resp.json()
        assert len(data["holders"]) >= 2
        for h in data["holders"]:
            assert h["holder_type"] == "individual"

    @pytest.mark.asyncio
    async def test_wallet_holders_filtro_verification_status(self, client):
        resp = await client.get("/v1/dac8/wallet-holders", params={"verification_status": "verified"})
        data = resp.json()
        assert len(data["holders"]) >= 2

    @pytest.mark.asyncio
    async def test_wallet_holders_filtro_report_id(self, client):
        resp = await client.get("/v1/dac8/wallet-holders", params={"report_id": "1"})
        data = resp.json()
        assert len(data["holders"]) >= 2


# ====================================================================
# Test: GET /v1/dac8/wallet-holders/{id} (detalle)
# ====================================================================


class TestDac8GetWalletHolder:
    @pytest.mark.asyncio
    async def test_wallet_holder_detalle_status_200(self, client):
        resp = await client.get("/v1/dac8/wallet-holders/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_wallet_holder_detalle_404(self, client):
        resp = await client.get("/v1/dac8/wallet-holders/9999")
        assert resp.status_code == 404
