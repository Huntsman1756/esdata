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

    @pytest.mark.asyncio
    async def test_casp_lista_status_200(self, client):
        resp = await client.get("/v1/mica/casp")
        assert resp.status_code == 200

    @pytest.mark.asyncio
        assert "casps" in data
        assert isinstance(data["casps"], list)

    @pytest.mark.asyncio
        for c in data["casps"]:
            assert c["status"] == "active"

    @pytest.mark.asyncio


# ====================================================================
# Test: GET /v1/mica/casp/{id} (detalle CASP)
# ====================================================================

    @pytest.mark.asyncio
    async def test_crypto_assets_lista_status_200(self, client):
        resp = await client.get("/v1/mica/crypto-assets")
        assert resp.status_code == 200

    @pytest.mark.asyncio
        for a in data["assets"]:
            assert a["is_sha"] is True

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_tokenized_assets_lista_status_200(self, client):
        resp = await client.get("/v1/mica/tokenized-assets")
        assert resp.status_code == 200

    @pytest.mark.asyncio
        assert resp.status_code == 404


# ====================================================================
