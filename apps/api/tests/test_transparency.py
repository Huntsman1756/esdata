"""Tests para el router de Transparencia.

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

TRANSPARENCY_SEED_SQL = [
    """
    INSERT INTO transparency_issuer (issuer_id, listing_market, ticker, reporting_frequency, home_member_state, status)
    VALUES (1, 'BME', 'IBE.MC', 'anual', 'ES', 'active')
    """,
    """
    INSERT INTO transparency_issuer (issuer_id, listing_market, ticker, reporting_frequency, home_member_state, status)
    VALUES (2, 'BME', 'SAN.MC', 'anual', 'ES', 'active')
    """,
    """
    INSERT INTO transparency_issuer (issuer_id, listing_market, ticker, reporting_frequency, home_member_state, status)
    VALUES (3, 'BME', 'TEF.MC', 'semestral', 'ES', 'active')
    """,
    """
    INSERT INTO transparency_regulated_information (issuer_id, info_type, publication_date, content_url, filing_reference, status)
    VALUES (1, 'financial-report', '2024-03-15', 'https://www.iberdrola.com/inversores/resultados', 'IR-IBE-2024-Q4', 'published')
    """,
    """
    INSERT INTO transparency_regulated_information (issuer_id, info_type, publication_date, content_url, filing_reference, status)
    VALUES (2, 'share-capital-change', '2024-02-28', 'https://www.bbvapaper.com/inversores', 'IR-BBVA-2024-CAP', 'published')
    """,
    """
    INSERT INTO transparency_regulated_information (issuer_id, info_type, publication_date, content_url, filing_reference, status)
    VALUES (3, 'insider-info', '2024-03-10', 'https://www.telefonica.com/inversores', 'IR-TEF-2024-INSIDER', 'published')
    """,
    """
    INSERT INTO transparency_voting_rights (issuer_id, shareholder_id, voting_rights_pct, date_acquired, date_reported, status)
    VALUES (1, 10, 0.0523, '2024-01-15', '2024-01-20', 'active')
    """,
    """
    INSERT INTO transparency_voting_rights (issuer_id, shareholder_id, voting_rights_pct, date_acquired, date_reported, status)
    VALUES (1, 11, 0.0301, '2024-02-01', '2024-02-05', 'active')
    """,
    """
    INSERT INTO transparency_voting_rights (issuer_id, shareholder_id, voting_rights_pct, date_acquired, date_reported, status)
    VALUES (2, 10, 0.0750, '2024-01-20', '2024-01-25', 'active')
    """,
    """
    INSERT INTO transparency_internal_rule (entity_id, designated_persons, internal_procedure, retention_period, status)
    VALUES (1, '["ceo", "cfo", "secretario_consejo"]', 'notificacion_inmediata_comite_emergente', '10_anos', 'active')
    """,
    """
    INSERT INTO transparency_internal_rule (entity_id, designated_persons, internal_procedure, retention_period, status)
    VALUES (2, '["ceo", "cfo", "compliance_officer"]', 'notificacion_24h_desde_deteccion', '10_anos', 'active')
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_transparency():
    """Semilla basica de datos Transparencia para tests del router."""
    from db import engine

    with engine.begin() as conn:
        for sql in TRANSPARENCY_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM transparency_internal_rule"))
        conn.execute(text("DELETE FROM transparency_voting_rights"))
        conn.execute(text("DELETE FROM transparency_regulated_information"))
        conn.execute(text("DELETE FROM transparency_issuer"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestTransparencyIssuers:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/transparency/issuers")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/transparency/issuers")
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_campo_ticker(self, client):
        resp = await client.get("/v1/transparency/issuers")
        data = resp.json()
        tickers = [i["ticker"] for i in data["items"]]
        assert "IBE.MC" in tickers
        assert "SAN.MC" in tickers
        assert "TEF.MC" in tickers

    @pytest.mark.asyncio
    async def test_campo_listing_market(self, client):
        resp = await client.get("/v1/transparency/issuers")
        data = resp.json()
        for i in data["items"]:
            assert i["listing_market"] == "BME"

    @pytest.mark.asyncio
    async def test_filtro_listing_market(self, client):
        resp = await client.get("/v1/transparency/issuers", params={"listing_market": "BME"})
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_filtro_search(self, client):
        resp = await client.get("/v1/transparency/issuers", params={"search": "IBE"})
        data = resp.json()
        assert len(data["items"]) >= 1
        tickers = [i["ticker"] for i in data["items"]]
        assert "IBE.MC" in tickers


class TestTransparencyRegulatedInfo:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/transparency/regulated-info")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/transparency/regulated-info")
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_campo_info_type(self, client):
        resp = await client.get("/v1/transparency/regulated-info")
        data = resp.json()
        types = [r["info_type"] for r in data["items"]]
        assert "financial-report" in types
        assert "share-capital-change" in types
        assert "insider-info" in types

    @pytest.mark.asyncio
    async def test_campo_filing_reference(self, client):
        resp = await client.get("/v1/transparency/regulated-info")
        data = resp.json()
        refs = [r["filing_reference"] for r in data["items"]]
        assert "IR-IBE-2024-Q4" in refs

    @pytest.mark.asyncio
    async def test_campo_status(self, client):
        resp = await client.get("/v1/transparency/regulated-info")
        data = resp.json()
        for r in data["items"]:
            assert r["status"] == "published"


class TestTransparencyVotingRights:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/transparency/voting-rights")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/transparency/voting-rights")
        data = resp.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_campo_voting_rights_pct(self, client):
        resp = await client.get("/v1/transparency/voting-rights")
        data = resp.json()
        pcts = [r["voting_rights_pct"] for r in data["items"]]
        assert 0.0523 in pcts
        assert 0.0750 in pcts

    @pytest.mark.asyncio
    async def test_campo_shareholder_id(self, client):
        resp = await client.get("/v1/transparency/voting-rights")
        data = resp.json()
        ids = [r["shareholder_id"] for r in data["items"]]
        assert 10 in ids
        assert 11 in ids


class TestTransparencyInternalRules:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/transparency/internal-rules")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/transparency/internal-rules")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_internal_procedure(self, client):
        resp = await client.get("/v1/transparency/internal-rules")
        data = resp.json()
        procedures = [r["internal_procedure"] for r in data["items"]]
        assert "notificacion_inmediata_comite_emergente" in procedures
        assert "notificacion_24h_desde_deteccion" in procedures

    @pytest.mark.asyncio
    async def test_campo_retention_period(self, client):
        resp = await client.get("/v1/transparency/internal-rules")
        data = resp.json()
        for r in data["items"]:
            assert r["retention_period"] == "10_anos"
