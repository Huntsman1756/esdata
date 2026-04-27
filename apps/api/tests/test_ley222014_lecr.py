"""Tests para el router de Ley 22/2014 de Entidades de Capital Riesgo (LECR).

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

# --- Seed de norma LECR + articulos + versiones ---

LECR_NORMA_SEED = """
INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde)
VALUES (
    'LECR_222014',
    'Ley 22/2014, de 12 de noviembre, de Entidades de Capital Riesgo',
    'BOE-A-2014-11230',
    'https://www.boe.es/eli/es/ley/2014/11/12/22',
    'es', 'boe', 'ley', 'capital_riesgo', 'ingestada', '2014-11-13'
)
"""

LECR_ARTICULOS = [
    ("1", "Objeto", "articulo"),
    ("2", "Definiciones", "articulo"),
    ("14", "Coinversiones", "articulo"),
    ("26", "SCR autogestionable", "articulo"),
    ("77", "Normas de conducta", "articulo"),
]

LECR_SEED_SQL = [LECR_NORMA_SEED]

for numero, titulo, tipo in LECR_ARTICULOS:
    LECR_SEED_SQL.append(
        f"""
        INSERT INTO articulo (norma_id, numero, titulo, tipo)
        SELECT id, '{numero}', '{titulo}', '{tipo}' FROM norma WHERE codigo = 'LECR_222014'
        """
    )

LECR_SEED_SQL.append(
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT id, 'Articulo 1. Esta Ley regula las Entidades de Capital Riesgo.',
           '2014-11-13', NULL, 'lecr-1'
    FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'LECR_222014') AND numero = '1'
    """
)

LECR_SEED_SQL.append(
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT id, 'Articulo 26. El SCR podra ser autogestionable.',
           '2014-11-13', NULL, 'lecr-26'
    FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'LECR_222014') AND numero = '26'
    """
)


@pytest_asyncio.fixture(autouse=True)
async def _seed_lecr():
    """Semilla basica de norma LECR para tests del router."""
    from db import engine

    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) VALUES ('LECR_222014', 'Ley 22/2014 de Entidades de Capital Riesgo', 'BOE-A-2014-11230', 'https://www.boe.es/eli/es/ley/2014/11/12/22', 'es', 'boe', 'ley', 'capital_riesgo', 'ingestada', '2014-11-13')"
        ))
        conn.execute(text(
            "INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) VALUES ('LECR_TEST', 'Test norma LECR', 'BOE-A-2014-11230_TEST', 'https://www.boe.es/eli/es/ley/2014/11/12/test', 'es', 'boe', 'ley', 'capital_riesgo', 'ingestada', '2014-11-13')"
        ))

        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '1', 'Objeto', 'articulo' FROM norma WHERE codigo = 'LECR_TEST'"
        ))
        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '26', 'SCR autogestionable', 'articulo' FROM norma WHERE codigo = 'LECR_TEST'"
        ))
        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '77', 'Normas de conducta', 'articulo' FROM norma WHERE codigo = 'LECR_TEST'"
        ))

        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 1. Esta Ley regula las Entidades de Capital Riesgo.', '2014-11-13', NULL, 'lecr-test-1'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'LECR_TEST') AND numero = '1'
            """
        ))
        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 26. El SCR podra ser autogestionable.', '2014-11-13', NULL, 'lecr-test-26'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'LECR_TEST') AND numero = '26'
            """
        ))
        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 77. Normas de conducta y prevencion de conflictos.', '2014-11-13', NULL, 'lecr-test-77'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'LECR_TEST') AND numero = '77'
            """
        ))

    yield

    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LECR_TEST'))"
        ))
        conn.execute(text(
            "DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LECR_TEST')"
        ))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'LECR_TEST'"))
        conn.execute(text(
            "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LECR_222014'))"
        ))
        conn.execute(text(
            "DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LECR_222014')"
        ))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'LECR_222014'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ====================================================================
# Test: GET /v1/lecr (lista normas)
# ====================================================================

class TestLecrListaNormas:
    @pytest.mark.asyncio
    async def test_lecr_lista_status_200(self, client):
        resp = await client.get("/v1/lecr")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_lecr_lista_response_contiene_normas(self, client):
        resp = await client.get("/v1/lecr")
        data = resp.json()
        assert "normas" in data
        assert isinstance(data["normas"], list)

    @pytest.mark.asyncio
    async def test_lecr_lista_norma_presente(self, client):
        resp = await client.get("/v1/lecr")
        codigos = [n["codigo"] for n in resp.json()["normas"]]
        assert "LECR_222014" in codigos


# ====================================================================
# Test: GET /v1/lecr/{codigo} (detalle norma)
# ====================================================================

class TestLecrDetalleNorma:
    @pytest.mark.asyncio
    async def test_lecr_norma_detalle_status_200(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_lecr_norma_detalle_codigo(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST")
        data = resp.json()
        assert data["codigo"] == "LECR_TEST"

    @pytest.mark.asyncio
    async def test_lecr_norma_detalle_titulo(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST")
        data = resp.json()
        assert "Test norma" in data["titulo"]

    @pytest.mark.asyncio
    async def test_lecr_norma_detalle_boe_id(self, client):
        resp = await client.get("/v1/lecr/LECR_222014")
        data = resp.json()
        assert data["boe_id"] == "BOE-A-2014-11230"

    @pytest.mark.asyncio
    async def test_lecr_norma_detalle_jurisdiccion(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST")
        data = resp.json()
        assert data["jurisdiccion"] == "es"

    @pytest.mark.asyncio
    async def test_lecr_norma_detalle_tipo_documento(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST")
        data = resp.json()
        assert data["tipo_documento"] == "ley"

    @pytest.mark.asyncio
    async def test_lecr_norma_detalle_404(self, client):
        resp = await client.get("/v1/lecr/ZZZZZZZ")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/lecr/{codigo}/articulos (lista articulos)
# ====================================================================

class TestLecrListaArticulos:
    @pytest.mark.asyncio
    async def test_lecr_articulos_status_200(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_lecr_articulos_response_model(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos")
        data = resp.json()
        assert "norma" in data
        assert "articulos" in data
        assert data["norma"] == "LECR_TEST"

    @pytest.mark.asyncio
    async def test_lecr_articulos_contiene_articulos(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos")
        data = resp.json()
        articulo_nums = [a["numero"] for a in data["articulos"]]
        assert "1" in articulo_nums
        assert "26" in articulo_nums
        assert "77" in articulo_nums

    @pytest.mark.asyncio
    async def test_lecr_articulos_campo_numero(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos")
        for a in resp.json()["articulos"]:
            assert "numero" in a
            assert "titulo" in a
            assert "tipo" in a

    @pytest.mark.asyncio
    async def test_lecr_articulos_filtro_tipo(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos", params={"tipo": "articulo"})
        data = resp.json()
        for a in data["articulos"]:
            assert a["tipo"] == "articulo"

    @pytest.mark.asyncio
    async def test_lecr_articulos_404_norma_no_existente(self, client):
        resp = await client.get("/v1/lecr/ZZZZZZZ/articulos")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/lecr/{codigo}/articulos/{numero} (detalle articulo)
# ====================================================================

class TestLecrDetalleArticulo:
    @pytest.mark.asyncio
    async def test_lecr_articulo_detalle_status_200(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_lecr_articulo_detalle_campos(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos/1")
        data = resp.json()
        assert data["norma"] == "LECR_TEST"
        assert data["numero"] == "1"
        assert "texto" in data
        assert "vigente_desde" in data
        assert "confianza" in data

    @pytest.mark.asyncio
    async def test_lecr_articulo_detalle_texto_contenido(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos/1")
        data = resp.json()
        assert "Ley" in data["texto"] or "Capital" in data["texto"]

    @pytest.mark.asyncio
    async def test_lecr_articulo_detalle_confianza_nivel(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos/1")
        data = resp.json()
        assert data["confianza"]["nivel"] == 1
        assert isinstance(data["confianza"]["fuentes"], list)

    @pytest.mark.asyncio
    async def test_lecr_articulo_detalle_404(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_lecr_articulo_detalle_vigente_en(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos/1", params={"vigente_en": "2024-01-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "LECR_TEST"


# ====================================================================
# Test: GET /v1/lecr/{codigo}/articulos/{numero}/historial
# ====================================================================

class TestLecrHistorialArticulo:
    @pytest.mark.asyncio
    async def test_lecr_historial_status_200(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos/1/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_lecr_historial_response_model(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos/1/historial")
        data = resp.json()
        assert "norma" in data
        assert "numero" in data
        assert "historial" in data
        assert isinstance(data["historial"], list)

    @pytest.mark.asyncio
    async def test_lecr_historial_version_campos(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos/1/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_lecr_historial_404(self, client):
        resp = await client.get("/v1/lecr/LECR_TEST/articulos/9999/historial")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/lecr/micro-obligaciones
# ====================================================================

class TestLecrMicroObligaciones:
    @pytest.mark.asyncio
    async def test_lecr_micro_obligaciones_status_200(self, client):
        resp = await client.get("/v1/lecr/micro-obligaciones")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_lecr_micro_obligaciones_response_model(self, client):
        resp = await client.get("/v1/lecr/micro-obligaciones")
        data = resp.json()
        assert "micro_obligaciones" in data
        assert "total" in data
        assert isinstance(data["micro_obligaciones"], list)
