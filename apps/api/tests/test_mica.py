"""Tests para el router de MiCA / crypto-asset services.

Cubre: CASP, crypto-assets, tokenized assets, wallet custodians, crypto transactions.
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

# --- Seed de datos MiCA ---


MICA_SEED_SQL = [
    """
    INSERT INTO casp (name, registration_number, home_member_state, passport_active, services_offered, status)
    VALUES ('Bitso', 'CASP-ES-001', 'Spain', true, '{"exchange": true, "custody": true}', 'active')
    """,
    """
    INSERT INTO casp (name, registration_number, home_member_state, passport_active, services_offered, status)
    VALUES ('Bitstamp', 'CASP-ES-002', 'Lithuania', true, '{"exchange": true, "wallet": true}', 'active')
    """,
    """
    INSERT INTO casp (name, registration_number, home_member_state, passport_active, services_offered, status)
    VALUES ('Test CASP', 'CASP-TEST-001', 'Spain', false, '{"custody": true}', 'suspended')
    """,
    """
    INSERT INTO crypto_asset (asset_type, reference_uid, issuer_jurisdiction, is_sha, market_value_eur, holders_count, status)
    VALUES ('asset_referenced_token', 'ART-001', 'Spain', false, 50000000.00, 100000, 'active')
    """,
    """
    INSERT INTO crypto_asset (asset_type, reference_uid, issuer_jurisdiction, is_sha, market_value_eur, holders_count, status)
    VALUES ('utility_token', 'UT-001', 'Portugal', true, 200000000.00, 500000, 'active')
    """,
    """
    INSERT INTO crypto_asset (asset_type, reference_uid, issuer_jurisdiction, is_sha, market_value_eur, holders_count, status)
    VALUES ('e-money_token', 'EMT-TEST-001', 'Spain', false, 10000000.00, 50000, 'inactive')
    """,
    """
    INSERT INTO tokenized_asset (underlying_type, face_value, total_amount, listing_date, regulated_market, status)
    VALUES ('real_estate', 1000.00, 10000000.00, '2025-01-15', 'ES-TA', 'active')
    """,
    """
    INSERT INTO tokenized_asset (underlying_type, face_value, total_amount, listing_date, regulated_market, status)
    VALUES ('securities', 50.00, 5000000.00, '2025-03-01', 'ES-MC', 'active')
    """,
    """
    INSERT INTO wallet_custodian (entity_id, wallet_type, custody_mechanism, insurance_coverage, audit_frequency, status)
    VALUES (1, 'hot', 'multi_sig', 1000000.00, 'quarterly', 'active')
    """,
    """
    INSERT INTO wallet_custodian (entity_id, wallet_type, custody_mechanism, insurance_coverage, audit_frequency, status)
    VALUES (2, 'cold', 'hardware_wallet', 5000000.00, 'annual', 'active')
    """,
    """
    INSERT INTO crypto_transaction (sender_wallet, receiver_wallet, sender_jurisdiction, receiver_jurisdiction, asset_type, amount, value_eur, timestamp, reporting_period)
    VALUES ('0xABC123...', '0xDEF456...', 'Spain', 'France', 'utility_token', 100.000000, 5000.00, '2025-06-15 12:00:00+00', '2025-06')
    """,
    """
    INSERT INTO crypto_transaction (sender_wallet, receiver_wallet, sender_jurisdiction, receiver_jurisdiction, asset_type, amount, value_eur, timestamp, reporting_period)
    VALUES ('0xGHI789...', '0xJKL012...', 'Spain', 'Germany', 'asset_referenced_token', 50.000000, 2500.00, '2025-07-20 14:30:00+00', '2025-07')
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_mica():
    """Semilla basica de datos MiCA para tests del router."""
    from db import engine

    with engine.begin() as conn:
        for sql in MICA_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM crypto_transaction"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='crypto_transaction'"))
        conn.execute(text("DELETE FROM wallet_custodian"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='wallet_custodian'"))
        conn.execute(text("DELETE FROM tokenized_asset"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='tokenized_asset'"))
        conn.execute(text("DELETE FROM crypto_asset"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='crypto_asset'"))
        conn.execute(text("DELETE FROM casp"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='casp'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ====================================================================
# Test: GET /v1/mica/casp (lista CASP)
# ====================================================================


class TestMicaListCasp:
    @pytest.mark.asyncio
    async def test_casp_lista_status_200(self, client):
        resp = await client.get("/v1/mica/casp")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_casp_lista_response_model(self, client):
        resp = await client.get("/v1/mica/casp")
        data = resp.json()
        assert "casps" in data
        assert isinstance(data["casps"], list)

    @pytest.mark.asyncio
    async def test_casp_lista_contiene_registros(self, client):
        resp = await client.get("/v1/mica/casp")
        data = resp.json()
        assert len(data["casps"]) >= 3

    @pytest.mark.asyncio
    async def test_casp_lista_campo_nombre(self, client):
        resp = await client.get("/v1/mica/casp")
        data = resp.json()
        nombres = [c["name"] for c in data["casps"]]
        assert "Bitso" in nombres
        assert "Bitstamp" in nombres

    @pytest.mark.asyncio
    async def test_casp_lista_filtro_status_active(self, client):
        resp = await client.get("/v1/mica/casp", params={"status": "active"})
        data = resp.json()
        assert len(data["casps"]) >= 2
        for c in data["casps"]:
            assert c["status"] == "active"

    @pytest.mark.asyncio
    async def test_casp_lista_filtro_home_state(self, client):
        resp = await client.get("/v1/mica/casp", params={"home_state": "Spain"})
        data = resp.json()
        estados = [c["home_member_state"] for c in data["casps"]]
        assert "Spain" in estados

    @pytest.mark.asyncio
    async def test_casp_lista_filtro_search(self, client):
        resp = await client.get("/v1/mica/casp", params={"search": "Bitso"})
        data = resp.json()
        assert len(data["casps"]) >= 1
        nombres = [c["name"] for c in data["casps"]]
        assert "Bitso" in nombres


# ====================================================================
# Test: GET /v1/mica/casp/{id} (detalle CASP)
# ====================================================================


class TestMicaGetCasp:
    @pytest.mark.asyncio
    async def test_casp_detalle_status_200(self, client):
        resp = await client.get("/v1/mica/casp/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_casp_detalle_nombre(self, client):
        resp = await client.get("/v1/mica/casp/1")
        data = resp.json()
        assert data["name"] == "Bitso"

    @pytest.mark.asyncio
    async def test_casp_detalle_campos(self, client):
        resp = await client.get("/v1/mica/casp/1")
        data = resp.json()
        assert "registration_number" in data
        assert "home_member_state" in data
        assert "passport_active" in data
        assert "status" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_casp_detalle_404(self, client):
        resp = await client.get("/v1/mica/casp/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_casp_detalle_services_offered_json(self, client):
        resp = await client.get("/v1/mica/casp/1")
        data = resp.json()
        services = data["services_offered"]
        if isinstance(services, str):
            services = json.loads(services)
        assert isinstance(services, dict)
        assert services["exchange"] is True


# ====================================================================
# Test: GET /v1/mica/crypto-assets (lista)
# ====================================================================


class TestMicaListCryptoAssets:
    @pytest.mark.asyncio
    async def test_crypto_assets_lista_status_200(self, client):
        resp = await client.get("/v1/mica/crypto-assets")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_crypto_assets_lista_response_model(self, client):
        resp = await client.get("/v1/mica/crypto-assets")
        data = resp.json()
        assert "assets" in data
        assert isinstance(data["assets"], list)

    @pytest.mark.asyncio
    async def test_crypto_assets_lista_campos(self, client):
        resp = await client.get("/v1/mica/crypto-assets")
        data = resp.json()
        for a in data["assets"]:
            assert "id" in a
            assert "asset_type" in a
            assert "reference_uid" in a
            assert "status" in a

    @pytest.mark.asyncio
    async def test_crypto_assets_filtro_asset_type(self, client):
        resp = await client.get("/v1/mica/crypto-assets", params={"asset_type": "utility_token"})
        data = resp.json()
        assert len(data["assets"]) >= 1
        tipos = [a["asset_type"] for a in data["assets"]]
        assert "utility_token" in tipos

    @pytest.mark.asyncio
    async def test_crypto_assets_filtro_is_sha(self, client):
        resp = await client.get("/v1/mica/crypto-assets", params={"is_sha": "true"})
        data = resp.json()
        for a in data["assets"]:
            assert a["is_sha"] is True

    @pytest.mark.asyncio
    async def test_crypto_assets_filtro_status(self, client):
        resp = await client.get("/v1/mica/crypto-assets", params={"status": "inactive"})
        data = resp.json()
        assert len(data["assets"]) >= 1
        for a in data["assets"]:
            assert a["status"] == "inactive"


# ====================================================================
# Test: GET /v1/mica/crypto-assets/{id} (detalle)
# ====================================================================


class TestMicaGetCryptoAsset:
    @pytest.mark.asyncio
    async def test_crypto_asset_detalle_status_200(self, client):
        resp = await client.get("/v1/mica/crypto-assets/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_crypto_asset_detalle_tipo(self, client):
        resp = await client.get("/v1/mica/crypto-assets/1")
        data = resp.json()
        assert data["asset_type"] == "asset_referenced_token"

    @pytest.mark.asyncio
    async def test_crypto_asset_detalle_404(self, client):
        resp = await client.get("/v1/mica/crypto-assets/9999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/mica/tokenized-assets (lista)
# ====================================================================


class TestMicaListTokenizedAssets:
    @pytest.mark.asyncio
    async def test_tokenized_assets_lista_status_200(self, client):
        resp = await client.get("/v1/mica/tokenized-assets")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_tokenized_assets_lista_response_model(self, client):
        resp = await client.get("/v1/mica/tokenized-assets")
        data = resp.json()
        assert "assets" in data
        assert len(data["assets"]) >= 2

    @pytest.mark.asyncio
    async def test_tokenized_assets_filtro_underlying_type(self, client):
        resp = await client.get("/v1/mica/tokenized-assets", params={"underlying_type": "real_estate"})
        data = resp.json()
        assert len(data["assets"]) >= 1
        for a in data["assets"]:
            assert a["underlying_type"] == "real_estate"


# ====================================================================
# Test: GET /v1/mica/tokenized-assets/{id} (detalle)
# ====================================================================


class TestMicaGetTokenizedAsset:
    @pytest.mark.asyncio
    async def test_tokenized_asset_detalle_status_200(self, client):
        resp = await client.get("/v1/mica/tokenized-assets/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_tokenized_asset_detalle_404(self, client):
        resp = await client.get("/v1/mica/tokenized-assets/9999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/mica/wallet-custodians (lista)
# ====================================================================


class TestMicaListWalletCustodians:
    @pytest.mark.asyncio
    async def test_wallet_custodians_lista_status_200(self, client):
        resp = await client.get("/v1/mica/wallet-custodians")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_wallet_custodians_lista_response_model(self, client):
        resp = await client.get("/v1/mica/wallet-custodians")
        data = resp.json()
        assert "custodians" in data
        assert len(data["custodians"]) >= 2

    @pytest.mark.asyncio
    async def test_wallet_custodians_filtro_wallet_type(self, client):
        resp = await client.get("/v1/mica/wallet-custodians", params={"wallet_type": "cold"})
        data = resp.json()
        assert len(data["custodians"]) >= 1
        for c in data["custodians"]:
            assert c["wallet_type"] == "cold"


# ====================================================================
# Test: GET /v1/mica/wallet-custodians/{id} (detalle)
# ====================================================================


class TestMicaGetWalletCustodian:
    @pytest.mark.asyncio
    async def test_wallet_custodian_detalle_status_200(self, client):
        resp = await client.get("/v1/mica/wallet-custodians/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_wallet_custodian_detalle_404(self, client):
        resp = await client.get("/v1/mica/wallet-custodians/9999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/mica/crypto-transactions (lista)
# ====================================================================


class TestMicaListCryptoTransactions:
    @pytest.mark.asyncio
    async def test_crypto_transactions_lista_status_200(self, client):
        resp = await client.get("/v1/mica/crypto-transactions")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_crypto_transactions_lista_response_model(self, client):
        resp = await client.get("/v1/mica/crypto-transactions")
        data = resp.json()
        assert "transactions" in data
        assert len(data["transactions"]) >= 2

    @pytest.mark.asyncio
    async def test_crypto_transactions_campos(self, client):
        resp = await client.get("/v1/mica/crypto-transactions")
        data = resp.json()
        for t in data["transactions"]:
            assert "id" in t
            assert "sender_wallet" in t
            assert "receiver_wallet" in t
            assert "asset_type" in t
            assert "value_eur" in t

    @pytest.mark.asyncio
    async def test_crypto_transactions_filtro_asset_type(self, client):
        resp = await client.get("/v1/mica/crypto-transactions", params={"asset_type": "utility_token"})
        data = resp.json()
        assert len(data["transactions"]) >= 1

    @pytest.mark.asyncio
    async def test_crypto_transactions_filtro_reporting_period(self, client):
        resp = await client.get("/v1/mica/crypto-transactions", params={"reporting_period": "2025-06"})
        data = resp.json()
        assert len(data["transactions"]) >= 1

    @pytest.mark.asyncio
    async def test_crypto_transactions_filtro_sender_wallet(self, client):
        resp = await client.get("/v1/mica/crypto-transactions", params={"sender_wallet": "0xABC123"})
        data = resp.json()
        assert len(data["transactions"]) >= 1


# ====================================================================
# Test: GET /v1/mica/crypto-transactions/{id} (detalle)
# ====================================================================


class TestMicaGetCryptoTransaction:
    @pytest.mark.asyncio
    async def test_crypto_transaction_detalle_status_200(self, client):
        resp = await client.get("/v1/mica/crypto-transactions/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_crypto_transaction_detalle_404(self, client):
        resp = await client.get("/v1/mica/crypto-transactions/9999")
        assert resp.status_code == 404
