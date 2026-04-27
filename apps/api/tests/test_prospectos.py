"""Tests para el router de Prospectos ETI (Reglamento 2017/1129).

Cubre: lista de normas, detalle de norma, articulos, detalle de articulo,
historial de versiones de articulos.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy import text

# --- Seed de norma Prospectos + articulos + versiones ---

PROSPECTOS_NORMA_SEED = """
INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde)
VALUES (
    'PROSPECTOS_2017_1129',
    'Reglamento (UE) 2017/1129 sobre el prospecto de informacion',
    'EUR-CELEX-32017R1129',
    'https://eur-lex.europa.eu/eli/reg/2017/1129/oj',
    'ue', 'eurlex', 'reglamento', 'mercados_financieros_ue', 'ingestada', '2017-06-07'
)
"""

PROSPECTOS_ARTICULOS = [
    ("1", "Objeto y ambito de aplicacion", "articulo"),
    ("2", "Definiciones", "articulo"),
    ("3", "Contenido del prospecto", "articulo"),
    ("4", "Resumen informativo", "articulo"),
    ("5", "Formulario unico del prospecto", "articulo"),
    ("10", "Resumen", "articulo"),
    ("14", "Informacion sobre emisores de valores con garantia real", "articulo"),
]

PROSPECTOS_SEED_SQL = [PROSPECTOS_NORMA_SEED]

for numero, titulo, tipo in PROSPECTOS_ARTICULOS:
    PROSPECTOS_SEED_SQL.append(
        f"""
        INSERT INTO articulo (norma_id, numero, titulo, tipo)
        SELECT id, '{numero}', '{titulo}', '{tipo}' FROM norma WHERE codigo = 'PROSPECTOS_2017_1129'
        """
    )

PROSPECTOS_SEED_SQL.append(
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT id, 'Articulo 1. El presente Reglamento establece un procedimiento armonizado para la elaboracion, verificacion y distribucion del prospecto.',
           '2017-06-07', NULL, 'prospectos-1'
    FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_2017_1129') AND numero = '1'
    """
)

PROSPECTOS_SEED_SQL.append(
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT id, 'Articulo 3. El prospecto contiene la informacion necesaria para que los inversores puedan tomar una decision informada sobre los valores.',
           '2017-06-07', NULL, 'prospectos-3'
    FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_2017_1129') AND numero = '3'
    """
)

PROSPECTOS_SEED_SQL.append(
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT id, 'Articulo 10. El resumen debe contener la informacion clave sobre el emisor y los valores que se ofrecen.',
           '2017-06-07', NULL, 'prospectos-10'
    FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_2017_1129') AND numero = '10'
    """
)


@pytest_asyncio.fixture(autouse=True)
async def _seed_prospectos():
    """Semilla basica de norma Prospectos ETI para tests del router."""
    from db import engine

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) VALUES ('PROSPECTOS_2017_1129', 'Reglamento (UE) 2017/1129 sobre el prospecto de informacion', 'EUR-CELEX-32017R1129', 'https://eur-lex.europa.eu/eli/reg/2017/1129/oj', 'ue', 'eurlex', 'reglamento', 'mercados_financieros_ue', 'ingestada', '2017-06-07')"))
        conn.execute(text("INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) VALUES ('PROSPECTOS_TEST', 'Test norma Prospectos ETI', 'EUR-CELEX-32017R1129_TEST', 'https://eur-lex.europa.eu/eli/reg/2017/1129/test', 'ue', 'eurlex', 'reglamento', 'mercados_financieros_ue', 'ingestada', '2017-06-07')"))

        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '1', 'Objeto y ambito', 'articulo' FROM norma WHERE codigo = 'PROSPECTOS_TEST'"
        ))
        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '3', 'Contenido del prospecto', 'articulo' FROM norma WHERE codigo = 'PROSPECTOS_TEST'"
        ))
        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '10', 'Resumen', 'articulo' FROM norma WHERE codigo = 'PROSPECTOS_TEST'"
        ))

        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 1. El presente Reglamento establece un procedimiento armonizado para el prospecto.', '2017-06-07', NULL, 'prospectos-test-1'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_TEST') AND numero = '1'
            """
        ))
        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 3. El prospecto contiene la informacion necesaria para los inversores.', '2017-06-07', NULL, 'prospectos-test-3'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_TEST') AND numero = '3'
            """
        ))
        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 10. El resumen debe contener la informacion clave sobre el emisor.', '2017-06-07', NULL, 'prospectos-test-10'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_TEST') AND numero = '10'
            """
        ))

    yield

    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_TEST'))"
        ))
        conn.execute(text(
            "DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_TEST')"
        ))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'PROSPECTOS_TEST'"))
        conn.execute(text(
            "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_2017_1129'))"
        ))
        conn.execute(text(
            "DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_2017_1129')"
        ))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'PROSPECTOS_2017_1129'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ====================================================================
# Test: GET /v1/prospectos (lista normas)
# ====================================================================

class TestProspectosListaNormas:
    @pytest.mark.asyncio
    async def test_prospectos_lista_status_200(self, client):
        resp = await client.get("/v1/prospectos")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_prospectos_lista_response_contiene_normas(self, client):
        resp = await client.get("/v1/prospectos")
        data = resp.json()
        assert "normas" in data
        assert isinstance(data["normas"], list)

    @pytest.mark.asyncio
    async def test_prospectos_lista_norma_presente(self, client):
        resp = await client.get("/v1/prospectos")
        codigos = [n["codigo"] for n in resp.json()["normas"]]
        assert "PROSPECTOS_2017_1129" in codigos


# ====================================================================
# Test: GET /v1/prospectos/{codigo} (detalle norma)
# ====================================================================

class TestProspectosDetalleNorma:
    @pytest.mark.asyncio
    async def test_prospectos_norma_detalle_status_200(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_prospectos_norma_detalle_codigo(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST")
        data = resp.json()
        assert data["codigo"] == "PROSPECTOS_TEST"

    @pytest.mark.asyncio
    async def test_prospectos_norma_detalle_titulo(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST")
        data = resp.json()
        assert "Reglamento" in data["titulo"] or "Test norma" in data["titulo"]

    @pytest.mark.asyncio
    async def test_prospectos_norma_detalle_boe_id(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_2017_1129")
        data = resp.json()
        assert data["boe_id"] == "EUR-CELEX-32017R1129"

    @pytest.mark.asyncio
    async def test_prospectos_norma_detalle_jurisdiccion(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST")
        data = resp.json()
        assert data["jurisdiccion"] == "ue"

    @pytest.mark.asyncio
    async def test_prospectos_norma_detalle_404(self, client):
        resp = await client.get("/v1/prospectos/ZZZZZZZ")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/prospectos/{codigo}/articulos (lista articulos)
# ====================================================================

class TestProspectosListaArticulos:
    @pytest.mark.asyncio
    async def test_prospectos_articulos_status_200(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_prospectos_articulos_response_model(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos")
        data = resp.json()
        assert "norma" in data
        assert "articulos" in data
        assert data["norma"] == "PROSPECTOS_TEST"

    @pytest.mark.asyncio
    async def test_prospectos_articulos_contiene_articulos(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos")
        data = resp.json()
        articulo_nums = [a["numero"] for a in data["articulos"]]
        assert "1" in articulo_nums
        assert "3" in articulo_nums
        assert "10" in articulo_nums

    @pytest.mark.asyncio
    async def test_prospectos_articulos_campo_numero(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos")
        for a in resp.json()["articulos"]:
            assert "numero" in a
            assert "titulo" in a
            assert "tipo" in a

    @pytest.mark.asyncio
    async def test_prospectos_articulos_filtro_tipo(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos", params={"tipo": "articulo"})
        data = resp.json()
        for a in data["articulos"]:
            assert a["tipo"] == "articulo"

    @pytest.mark.asyncio
    async def test_prospectos_articulos_404_norma_no_existente(self, client):
        resp = await client.get("/v1/prospectos/ZZZZZZZ/articulos")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/prospectos/{codigo}/articulos/{numero} (detalle articulo)
# ====================================================================

class TestProspectosDetalleArticulo:
    @pytest.mark.asyncio
    async def test_prospectos_articulo_detalle_status_200(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_prospectos_articulo_detalle_campos(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos/1")
        data = resp.json()
        assert data["norma"] == "PROSPECTOS_TEST"
        assert data["numero"] == "1"
        assert "texto" in data
        assert "vigente_desde" in data
        assert "confianza" in data

    @pytest.mark.asyncio
    async def test_prospectos_articulo_detalle_texto_contenido(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos/1")
        data = resp.json()
        assert "Reglamento" in data["texto"] or "prospecto" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_prospectos_articulo_detalle_confianza_nivel(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos/1")
        data = resp.json()
        assert data["confianza"]["nivel"] == 1
        assert isinstance(data["confianza"]["fuentes"], list)

    @pytest.mark.asyncio
    async def test_prospectos_articulo_detalle_404(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_prospectos_articulo_detalle_vigente_en(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos/1", params={"vigente_en": "2024-01-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "PROSPECTOS_TEST"


# ====================================================================
# Test: GET /v1/prospectos/{codigo}/articulos/{numero}/historial
# ====================================================================

class TestProspectosHistorialArticulo:
    @pytest.mark.asyncio
    async def test_prospectos_historial_status_200(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos/1/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_prospectos_historial_response_model(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos/1/historial")
        data = resp.json()
        assert "norma" in data
        assert "numero" in data
        assert "historial" in data
        assert isinstance(data["historial"], list)

    @pytest.mark.asyncio
    async def test_prospectos_historial_version_campos(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos/1/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_prospectos_historial_404(self, client):
        resp = await client.get("/v1/prospectos/PROSPECTOS_TEST/articulos/9999/historial")
        assert resp.status_code == 404
