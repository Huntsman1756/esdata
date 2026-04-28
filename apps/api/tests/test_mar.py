"""Tests para el router de MAR (Market Abuse Regulation).

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

MAR_SEED_SQL = [
    """
    INSERT INTO mar_insider_transaction (id, ppi_name, ppi_role, instrument, transaction_type, quantity, value_eur, price, date_time, country, status)
    VALUES (1, 'Ana Martinez', 'director_general', 'Telefonia.SA', 'buy', 5000, 25000.0, 5.0, '2024-03-01 09:00:00+01', 'ES', 'reported')
    """,
    """
    INSERT INTO mar_insider_transaction (id, ppi_name, ppi_role, instrument, transaction_type, quantity, value_eur, price, date_time, country, status)
    VALUES (2, 'Pedro Sanchez', 'consejero', 'Iberdrola.SA', 'sell', 2000, 38000.0, 19.0, '2024-03-02 14:30:00+01', 'ES', 'reported')
    """,
    """
    INSERT INTO mar_suspicious_transaction_report (id, entity_id, instrument, pattern_description, detection_method, severity, submitted_to_cnmv, cnmv_reference, status)
    VALUES (1, 1, 'BBVA.MC', 'Operacion en cascada con volumen 3x promedio diario', 'monitorizacion_situacion_mercado', 'high', true, 'STR-2024-001', 'under_review')
    """,
    """
    INSERT INTO mar_suspicious_transaction_report (id, entity_id, instrument, pattern_description, detection_method, severity, submitted_to_cnmv, cnmv_reference, status)
    VALUES (2, 2, 'Inditex.MC', 'Operacion cruzada entre cuentas controladas', 'analisis_comportamiento_transaccional', 'critical', true, 'STR-2024-002', 'submitted')
    """,
    """
    INSERT INTO mar_market_manipulation_indicator (id, pattern_type, instrument, time_window, volume_anomaly_pct, price_anomaly_pct, confidence_score, status)
    VALUES (1, 'spoofing', 'REPSOL.MC', '2024-02-28 09:00-16:00', 250.0, 5.2, 0.78, 'active')
    """,
    """
    INSERT INTO mar_market_manipulation_indicator (id, pattern_type, instrument, time_window, volume_anomaly_pct, price_anomaly_pct, confidence_score, status)
    VALUES (2, 'wash_trade', 'AMADEI.MC', '2024-03-01 10:00-12:00', 180.0, 2.1, 0.65, 'active')
    """,
    """
    INSERT INTO mar_insider_communication (id, sender_id, receiver_id, content_summary, timestamp, channel, inside_info_reference)
    VALUES (1, 1, 2, 'Comunicacion sobre resultados trimestrales no publicados', '2024-03-01 08:30:00+01', 'email_interno', 'INFO-2024-Q1-RESULTADOS')
    """,
    """
    INSERT INTO mar_insider_communication (id, sender_id, receiver_id, content_summary, timestamp, channel, inside_info_reference)
    VALUES (2, 3, 1, 'Consulta sobre plan de recompra de acciones', '2024-03-02 11:00:00+01', 'intranet_seguira', 'INFO-2024-BUYBACK_PLAN')
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_mar():
    """Semilla basica de datos MAR para tests del router."""
    from db import engine

    with engine.begin() as conn:
        for sql in MAR_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mar_insider_communication"))
        conn.execute(text("DELETE FROM mar_market_manipulation_indicator"))
        conn.execute(text("DELETE FROM mar_suspicious_transaction_report"))
        conn.execute(text("DELETE FROM mar_insider_transaction"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestMarInsiderTransactions:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mar/insider-transactions")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mar/insider-transactions")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_ppi_name(self, client):
        resp = await client.get("/v1/mar/insider-transactions")
        data = resp.json()
        names = [t["ppi_name"] for t in data["items"]]
        assert "Ana Martinez" in names

    @pytest.mark.asyncio
    async def test_campo_instrument(self, client):
        resp = await client.get("/v1/mar/insider-transactions")
        data = resp.json()
        instruments = [t["instrument"] for t in data["items"]]
        assert "Telefonia.SA" in instruments

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        resp = await client.get("/v1/mar/insider-transactions/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ppi_name"] == "Ana Martinez"

    @pytest.mark.asyncio
    async def test_filtro_status(self, client):
        resp = await client.get("/v1/mar/insider-transactions", params={"status": "reported"})
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_filtro_search(self, client):
        resp = await client.get("/v1/mar/insider-transactions", params={"search": "Ana"})
        data = resp.json()
        assert len(data["items"]) >= 1
        names = [t["ppi_name"] for t in data["items"]]
        assert "Ana Martinez" in names


class TestMarSuspiciousTransactionReports:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mar/suspicious-reports")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mar/suspicious-reports")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_severity(self, client):
        resp = await client.get("/v1/mar/suspicious-reports")
        data = resp.json()
        severities = [r["severity"] for r in data["items"]]
        assert "high" in severities
        assert "critical" in severities

    @pytest.mark.asyncio
    async def test_campo_cnmv_reference(self, client):
        resp = await client.get("/v1/mar/suspicious-reports")
        data = resp.json()
        refs = [r["cnmv_reference"] for r in data["items"]]
        assert "STR-2024-001" in refs


class TestMarMarketManipulationIndicators:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mar/manipulation-indicators")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mar/manipulation-indicators")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_pattern_type(self, client):
        resp = await client.get("/v1/mar/manipulation-indicators")
        data = resp.json()
        types = [m["pattern_type"] for m in data["items"]]
        assert "spoofing" in types
        assert "wash_trade" in types

    @pytest.mark.asyncio
    async def test_campo_confidence_score(self, client):
        resp = await client.get("/v1/mar/manipulation-indicators")
        data = resp.json()
        scores = [m["confidence_score"] for m in data["items"]]
        assert 0.78 in scores


class TestMarInsiderCommunications:
    @pytest.mark.asyncio
    async def test_status_200(self, client):
        resp = await client.get("/v1/mar/insider-communications")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contiene_registros(self, client):
        resp = await client.get("/v1/mar/insider-communications")
        data = resp.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_campo_channel(self, client):
        resp = await client.get("/v1/mar/insider-communications")
        data = resp.json()
        channels = [c["channel"] for c in data["items"]]
        assert "email_interno" in channels

    @pytest.mark.asyncio
    async def test_campo_content_summary(self, client):
        resp = await client.get("/v1/mar/insider-communications")
        data = resp.json()
        summaries = [c["content_summary"] for c in data["items"]]
        combined = " ".join(summaries)
        assert "resultados trimestrales" in combined
