"""Tests para el router de CSDR (Reglamento UE 909/2014).

Cubre: lista de normas, detalle de norma, articulos, detalle de articulo,
historial de versiones de articulos, micro-obligaciones.
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

# --- Seed de norma CSDR + articulos + versiones ---

CSDR_ARTICULOS = [
    ("4", "Depositarias centrales", "articulo"),
    ("5", "Segregacion de valores", "articulo"),
    ("7", "Settlement finalidad", "articulo"),
    ("10", "Obligaciones de settlement", "articulo"),
    ("20", "Buy-in", "articulo"),
]

CSDR_SEED_SQL = []

for numero, titulo, tipo in CSDR_ARTICULOS:
    CSDR_SEED_SQL.append(
        f"""
        INSERT INTO articulo (norma_id, numero, titulo, tipo)
        SELECT id, '{numero}', '{titulo}', '{tipo}' FROM norma WHERE codigo = 'CSDR_9092014'
        """
    )


@pytest_asyncio.fixture(autouse=True)
async def _seed_csdr():
    """Semilla basica de norma CSDR para tests del router."""
    from db import engine

    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) VALUES ('CSDR_9092014', 'Reglamento (UE) 909/2014 sobre depositarias centrales de valores', 'EUR-CELEX-32014R0909', 'https://eur-lex.europa.eu/eli/reg/2014/909/oj', 'ue', 'eurlex', 'reglamento', 'infraestructura_mercados_financieros', 'ingestada', '2014-09-12')"
        ))
        conn.execute(text(
            "INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) VALUES ('CSDR_TEST', 'Test norma CSDR', 'EUR-CELEX-32014R0909_TEST', 'https://eur-lex.europa.eu/eli/reg/2014/909/test', 'ue', 'eurlex', 'reglamento', 'infraestructura_mercados_financieros', 'ingestada', '2014-09-12')"
        ))

        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '4', 'Depositarias centrales', 'articulo' FROM norma WHERE codigo = 'CSDR_TEST'"
        ))
        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '7', 'Settlement finalidad', 'articulo' FROM norma WHERE codigo = 'CSDR_TEST'"
        ))
        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '20', 'Buy-in', 'articulo' FROM norma WHERE codigo = 'CSDR_TEST'"
        ))

        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 4. Las depositarias centrales proporcionaran servicios de depositario central.', '2014-09-12', NULL, 'csdr-test-4'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'CSDR_TEST') AND numero = '4'
            """
        ))
        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 7. La liquidacion de las operaciones sera firme al finalizar el dia.', '2014-09-12', NULL, 'csdr-test-7'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'CSDR_TEST') AND numero = '7'
            """
        ))
        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 20. Las reglas de buy-in se aplicaran en caso de incumplimiento de settlement.', '2014-09-12', NULL, 'csdr-test-20'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'CSDR_TEST') AND numero = '20'
            """
        ))

    yield

    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'CSDR_TEST'))"
        ))
        conn.execute(text(
            "DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'CSDR_TEST')"
        ))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'CSDR_TEST'"))
        conn.execute(text(
            "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'CSDR_9092014'))"
        ))
        conn.execute(text(
            "DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'CSDR_9092014')"
        ))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'CSDR_9092014'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ====================================================================
# Test: GET /v1/csdr (lista normas)
# ====================================================================

class TestCsdrListaNormas:
    @pytest.mark.asyncio
    async def test_csdr_lista_status_200(self, client):
        resp = await client.get("/v1/csdr")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_csdr_lista_response_contiene_normas(self, client):
        resp = await client.get("/v1/csdr")
        data = resp.json()
        assert "normas" in data
        assert isinstance(data["normas"], list)

    @pytest.mark.asyncio
    async def test_csdr_lista_norma_presente(self, client):
        resp = await client.get("/v1/csdr")
        codigos = [n["codigo"] for n in resp.json()["normas"]]
        assert "CSDR_9092014" in codigos


# ====================================================================
# Test: GET /v1/csdr/{codigo} (detalle norma)
# ====================================================================

class TestCsdrDetalleNorma:
    @pytest.mark.asyncio
    async def test_csdr_norma_detalle_status_200(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_csdr_norma_detalle_codigo(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST")
        data = resp.json()
        assert data["codigo"] == "CSDR_TEST"

    @pytest.mark.asyncio
    async def test_csdr_norma_detalle_titulo(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST")
        data = resp.json()
        assert "Test norma" in data["titulo"]

    @pytest.mark.asyncio
    async def test_csdr_norma_detalle_boe_id(self, client):
        resp = await client.get("/v1/csdr/CSDR_9092014")
        data = resp.json()
        assert data["boe_id"] == "EUR-CELEX-32014R0909"

    @pytest.mark.asyncio
    async def test_csdr_norma_detalle_jurisdiccion(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST")
        data = resp.json()
        assert data["jurisdiccion"] == "ue"

    @pytest.mark.asyncio
    async def test_csdr_norma_detalle_tipo_documento(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST")
        data = resp.json()
        assert data["tipo_documento"] == "reglamento"

    @pytest.mark.asyncio
    async def test_csdr_norma_detalle_404(self, client):
        resp = await client.get("/v1/csdr/ZZZZZZZ")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/csdr/{codigo}/articulos (lista articulos)
# ====================================================================

class TestCsdrListaArticulos:
    @pytest.mark.asyncio
    async def test_csdr_articulos_status_200(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_csdr_articulos_response_model(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos")
        data = resp.json()
        assert "norma" in data
        assert "articulos" in data
        assert data["norma"] == "CSDR_TEST"

    @pytest.mark.asyncio
    async def test_csdr_articulos_contiene_articulos(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos")
        data = resp.json()
        articulo_nums = [a["numero"] for a in data["articulos"]]
        assert "4" in articulo_nums
        assert "7" in articulo_nums
        assert "20" in articulo_nums

    @pytest.mark.asyncio
    async def test_csdr_articulos_campo_numero(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos")
        for a in resp.json()["articulos"]:
            assert "numero" in a
            assert "titulo" in a
            assert "tipo" in a

    @pytest.mark.asyncio
    async def test_csdr_articulos_filtro_tipo(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos", params={"tipo": "articulo"})
        data = resp.json()
        for a in data["articulos"]:
            assert a["tipo"] == "articulo"

    @pytest.mark.asyncio
    async def test_csdr_articulos_404_norma_no_existente(self, client):
        resp = await client.get("/v1/csdr/ZZZZZZZ/articulos")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/csdr/{codigo}/articulos/{numero} (detalle articulo)
# ====================================================================

class TestCsdrDetalleArticulo:
    @pytest.mark.asyncio
    async def test_csdr_articulo_detalle_status_200(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos/4")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_csdr_articulo_detalle_campos(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos/4")
        data = resp.json()
        assert data["norma"] == "CSDR_TEST"
        assert data["numero"] == "4"
        assert "texto" in data
        assert "vigente_desde" in data
        assert "confianza" in data

    @pytest.mark.asyncio
    async def test_csdr_articulo_detalle_texto_contenido(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos/4")
        data = resp.json()
        assert "depositaria" in data["texto"].lower() or "central" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_csdr_articulo_detalle_confianza_nivel(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos/4")
        data = resp.json()
        assert data["confianza"]["nivel"] == 1
        assert isinstance(data["confianza"]["fuentes"], list)

    @pytest.mark.asyncio
    async def test_csdr_articulo_detalle_404(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_csdr_articulo_detalle_vigente_en(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos/4", params={"vigente_en": "2024-01-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "CSDR_TEST"


# ====================================================================
# Test: GET /v1/csdr/{codigo}/articulos/{numero}/historial
# ====================================================================

class TestCsdrHistorialArticulo:
    @pytest.mark.asyncio
    async def test_csdr_historial_status_200(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos/4/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_csdr_historial_response_model(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos/4/historial")
        data = resp.json()
        assert "norma" in data
        assert "numero" in data
        assert "historial" in data
        assert isinstance(data["historial"], list)

    @pytest.mark.asyncio
    async def test_csdr_historial_version_campos(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos/4/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_csdr_historial_404(self, client):
        resp = await client.get("/v1/csdr/CSDR_TEST/articulos/9999/historial")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/csdr/micro-obligaciones
# ====================================================================

class TestCsdrMicroObligaciones:
    @pytest.mark.asyncio
    async def test_csdr_micro_obligaciones_status_200(self, client):
        resp = await client.get("/v1/csdr/micro-obligaciones")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_csdr_micro_obligaciones_response_model(self, client):
        resp = await client.get("/v1/csdr/micro-obligaciones")
        data = resp.json()
        assert "micro_obligaciones" in data
        assert "total" in data
        assert isinstance(data["micro_obligaciones"], list)
