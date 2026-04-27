"""Tests para el router de MiCA (Reglamento UE 2023/1114) y crypto-asset services.

Cubre: CASP CRUD, crypto-asset list/detail, tokenized asset list/detail,
wallet custodian list/detail, crypto transaction list/detail/create.
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

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ====================================================================
# Test: GET /v1/mica/casp (lista CASP)
# ====================================================================

class TestListCasp:
    @pytest.mark.asyncio
    async def test_casp_lista_status_200(self, client):
        resp = await client.get("/v1/mica/casp")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_casp_lista_response_format(self, client):
        resp = await client.get("/v1/mica/casp")
        data = resp.json()
        assert "total" in data
        assert "casps" in data
        assert isinstance(data["casps"], list)

    @pytest.mark.asyncio
    async def test_casp_lista_contiene_bit2me(self, client):
        resp = await client.get("/v1/mica/casp")
        names = [c["name"] for c in resp.json()["casps"]]
        assert "Bit2Me S.L." in names

    @pytest.mark.asyncio
    async def test_casp_lista_filtro_status(self, client):
        resp = await client.get("/v1/mica/casp", params={"status": "active"})
        data = resp.json()
        assert data["total"] > 0
        for c in data["casps"]:
            assert c["status"] == "active"

    @pytest.mark.asyncio
    async def test_casp_lista_filtro_pais(self, client):
        resp = await client.get("/v1/mica/casp", params={"home_member_state": "ES"})
        data = resp.json()
        assert data["total"] >= 1
        for c in data["casps"]:
            assert c["home_member_state"] == "ES"

    @pytest.mark.asyncio
    async def test_casp_lista_filtro_busqueda(self, client):
        resp = await client.get("/v1/mica/casp", params={"search": "kraken"})
        data = resp.json()
        assert data["total"] >= 1
        names = [c["name"].lower() for c in data["casps"]]
        assert any("kraken" in n for n in names)

    @pytest.mark.asyncio
    async def test_casp_lista_paginacion(self, client):
        resp = await client.get("/v1/mica/casp", params={"limit": 2, "offset": 0})
        data = resp.json()
        assert len(data["casps"]) <= 2


# ====================================================================
# Test: GET /v1/mica/casp/{id} (detalle CASP)
# ====================================================================

class TestGetCasp:
    @pytest.mark.asyncio
    async def test_casp_detalle_bit2me(self, client):
        resp = await client.get("/v1/mica/casp/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Bit2Me S.L."
        assert data["registration_number"] == "ES-CASP-2024-001"
        assert data["home_member_state"] == "ES"

    @pytest.mark.asyncio
    async def test_casp_detalle_no_encontrado(self, client):
        resp = await client.get("/v1/mica/casp/99999")
        assert resp.status_code == 404


# ====================================================================
# Test: POST /v1/mica/casp (crear CASP)
# ====================================================================

class TestCreateCasp:
    @pytest.mark.asyncio
    async def test_casp_creacion_exitosa(self, client):
        resp = await client.post("/v1/mica/casp", json={
            "name": "Test CASP S.L.",
            "registration_number": "ES-CASP-TEST-001",
            "home_member_state": "ES",
            "passport_active": False,
            "services_offered": ["exchange", "custody"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test CASP S.L."
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_casp_creacion_sin_servicios(self, client):
        resp = await client.post("/v1/mica/casp", json={
            "name": "Test CASP sin servicios",
            "registration_number": "ES-CASP-TEST-002",
            "home_member_state": "PT",
        })
        assert resp.status_code == 201


# ====================================================================
# Test: PATCH /v1/mica/casp/{id} (actualizar CASP)
# ====================================================================

class TestUpdateCasp:
    @pytest.mark.asyncio
    async def test_casp_actualizar_passport(self, client):
        resp = await client.patch("/v1/mica/casp/1", json={"passport_active": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["passport_active"] is True

    @pytest.mark.asyncio
    async def test_casp_actualizar_status(self, client):
        resp = await client.patch("/v1/mica/casp/1", json={"status": "suspended"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "suspended"

    @pytest.mark.asyncio
    async def test_casp_actualizar_no_existente(self, client):
        resp = await client.patch("/v1/mica/casp/99999", json={"status": "active"})
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/mica/crypto-assets (lista criptoactivos)
# ====================================================================

class TestListCryptoAssets:
    @pytest.mark.asyncio
    async def test_crypto_assets_lista_status_200(self, client):
        resp = await client.get("/v1/mica/crypto-assets")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_crypto_assets_lista_response_format(self, client):
        resp = await client.get("/v1/mica/crypto-assets")
        data = resp.json()
        assert "total" in data
        assert "assets" in data

    @pytest.mark.asyncio
    async def test_crypto_assets_filtro_tipo(self, client):
        resp = await client.get("/v1/mica/crypto-assets", params={"asset_type": "asset-referenced"})
        data = resp.json()
        assert data["total"] >= 1
        for a in data["assets"]:
            assert a["asset_type"] == "asset-referenced"

    @pytest.mark.asyncio
    async def test_crypto_assets_filtro_sha(self, client):
        resp = await client.get("/v1/mica/crypto-assets", params={"is_sha": True})
        data = resp.json()
        assert data["total"] >= 1
        for a in data["assets"]:
            assert a["is_sha"] is True

    @pytest.mark.asyncio
    async def test_crypto_assets_detalle_usdc(self, client):
        resp = await client.get("/v1/mica/crypto-assets/2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reference_uid"] == "USDC-Ethereum"
        assert data["is_sha"] is True


# ====================================================================
# Test: POST /v1/mica/crypto-assets (crear criptoactivo)
# ====================================================================

class TestCreateCryptoAsset:
    @pytest.mark.asyncio
    async def test_crypto_asset_creacion_exitosa(self, client):
        resp = await client.post("/v1/mica/crypto-assets", json={
            "asset_type": "utility",
            "reference_uid": "TEST-TOKEN",
            "issuer_jurisdiction": "ES",
            "is_sha": False,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["asset_type"] == "utility"
        assert data["reference_uid"] == "TEST-TOKEN"


# ====================================================================
# Test: GET /v1/mica/tokenized-assets (lista activos tokenizados)
# ====================================================================

class TestListTokenizedAssets:
    @pytest.mark.asyncio
    async def test_tokenized_assets_lista_status_200(self, client):
        resp = await client.get("/v1/mica/tokenized-assets")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_tokenized_assets_filtro_tipo(self, client):
        resp = await client.get("/v1/mica/tokenized-assets", params={"underlying_type": "bond"})
        data = resp.json()
        assert data["total"] >= 1
        for a in data["assets"]:
            assert a["underlying_type"] == "bond"

    @pytest.mark.asyncio
    async def test_tokenized_assets_detalle_bond(self, client):
        resp = await client.get("/v1/mica/tokenized-assets/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["underlying_type"] == "bond"


# ====================================================================
# Test: GET /v1/mica/wallet-custodians (lista custodios)
# ====================================================================

class TestListWalletCustodians:
    @pytest.mark.asyncio
    async def test_custodios_lista_status_200(self, client):
        resp = await client.get("/v1/mica/wallet-custodians")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_custodios_filtro_tipo(self, client):
        resp = await client.get("/v1/mica/wallet-custodians", params={"wallet_type": "cold"})
        data = resp.json()
        assert data["total"] >= 1
        for c in data["custodians"]:
            assert c["wallet_type"] == "cold"

    @pytest.mark.asyncio
    async def test_custodios_detalle_cold(self, client):
        resp = await client.get("/v1/mica/wallet-custodians/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["wallet_type"] == "cold"


# ====================================================================
# Test: GET /v1/mica/transactions (lista transacciones crypto)
# ====================================================================

class TestListCryptoTransactions:
    @pytest.mark.asyncio
    async def test_transactions_lista_status_200(self, client):
        resp = await client.get("/v1/mica/transactions")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_transactions_lista_response_format(self, client):
        resp = await client.get("/v1/mica/transactions")
        data = resp.json()
        assert "total" in data
        assert "transactions" in data

    @pytest.mark.asyncio
    async def test_transactions_filtro_tipo(self, client):
        resp = await client.get("/v1/mica/transactions", params={"asset_type": "utility"})
        data = resp.json()
        assert data["total"] >= 1
        for t in data["transactions"]:
            assert t["asset_type"] == "utility"

    @pytest.mark.asyncio
    async def test_transactions_filtro_periodo(self, client):
        resp = await client.get("/v1/mica/transactions", params={"reporting_period": "2025-10"})
        data = resp.json()
        assert data["total"] >= 1
        for t in data["transactions"]:
            assert t["reporting_period"] == "2025-10"

    @pytest.mark.asyncio
    async def test_transactions_detalle(self, client):
        resp = await client.get("/v1/mica/transactions/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_type"] == "utility"
        assert data["amount"] == 1500.00

    @pytest.mark.asyncio
    async def test_transactions_no_encontrada(self, client):
        resp = await client.get("/v1/mica/transactions/99999")
        assert resp.status_code == 404


# ====================================================================
# Test: POST /v1/mica/transactions (crear transaccion)
# ====================================================================

class TestCreateCryptoTransaction:
    @pytest.mark.asyncio
    async def test_transaction_creacion_exitosa(self, client):
        resp = await client.post("/v1/mica/transactions", json={
            "sender_wallet": "0xabcdef1234567890abcdef1234567890abcdef12",
            "receiver_wallet": "0x0987654321fedcba0987654321fedcba09876543",
            "sender_jurisdiction": "ES",
            "receiver_jurisdiction": "FR",
            "asset_type": "utility",
            "amount": 500.00,
            "value_eur": 4250.00,
            "timestamp": "2025-12-01T10:00:00+00",
            "reporting_period": "2025-12",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["asset_type"] == "utility"
        assert data["amount"] == 500.00
        assert data["status"] == "reported"
