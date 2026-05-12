"""Tests para los routers de MiCA (Reglamento UE 2023/1114).

Fase 43 — Stub completion: todos los endpoints de MICA completados.

Nota: Las tablas casp, crypto_asset, tokenized_asset, wallet_custodian,
crypto_transaction no tienen migration en Alembic aun, asi que los tests
solo verifican que los endpoints se registran correctamente y retornan
la estructura esperada sin acceder a DB.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent / "workers"))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app
from routers import mica


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ====================================================================
# Router registration
# ====================================================================

def test_mica_router_has_prefix():
    assert mica.router.prefix == "/v1/mica"


def test_mica_router_has_tags():
    assert "mica" in mica.router.tags


@pytest.mark.asyncio
async def test_casp_list_status_200(client):
    resp = await client.get("/v1/mica/casp", headers={"x-api-key": "test-secret-key"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_casp_list_returns_items(client):
    resp = await client.get("/v1/mica/casp", headers={"x-api-key": "test-secret-key"})
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_casp_search_alias_returns_quality_contract(client):
    resp = await client.get("/v1/mica/casp/buscar?q=crypto", headers={"x-api-key": "test-secret-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    if data["total"] == 0:
        assert data["availability_status"] in {
            "workflow_empty",
            "allowed_empty",
            "configured_but_unavailable",
        }
        assert data["safe_to_answer"] is False
    else:
        assert data["quality_signal"] == "official_esma_register"
        assert data["availability_status"] == "populated"
        assert data["safe_to_answer"] is True
        assert "esma" in data["source_url"].lower()


@pytest.mark.asyncio
async def test_crypto_assets_list_status_200(client):
    resp = await client.get("/v1/mica/crypto-assets", headers={"x-api-key": "test-secret-key"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_crypto_assets_empty_contract_is_explicit(client):
    resp = await client.get("/v1/mica/crypto-assets", headers={"x-api-key": "test-secret-key"})
    assert resp.status_code == 200
    data = resp.json()
    if data["total"] == 0:
        assert data["availability_status"] in {
            "workflow_empty",
            "configured_but_unavailable",
        }
        assert data["safe_to_answer"] is False
        assert data["items"] == []


@pytest.mark.asyncio
async def test_tokenized_assets_list_status_200(client):
    resp = await client.get("/v1/mica/tokenized-assets", headers={"x-api-key": "test-secret-key"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_wallet_custodians_list_status_200(client):
    resp = await client.get("/v1/mica/wallet-custodians", headers={"x-api-key": "test-secret-key"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_wallet_custodians_empty_contract_is_explicit(client):
    resp = await client.get("/v1/mica/wallet-custodians", headers={"x-api-key": "test-secret-key"})
    assert resp.status_code == 200
    data = resp.json()
    if data["total"] == 0:
        assert data["availability_status"] == "configured_but_unavailable"
        assert data["safe_to_answer"] is False
        assert data["items"] == []


@pytest.mark.asyncio
async def test_crypto_transactions_list_status_200(client):
    resp = await client.get("/v1/mica/transactions", headers={"x-api-key": "test-secret-key"})
    assert resp.status_code == 200
