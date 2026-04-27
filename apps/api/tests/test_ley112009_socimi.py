"""Tests para el router de Ley 11/2009 de SOCIMI.

Cubre: lista de normas, detalle de norma, articulos, detalle de articulo,
historial de versiones y micro-obligaciones SOCIMI.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy import text

TEST_DB_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "xbrl" / f"socimi_test_{__name__}.db"

# --- Seed de norma SOCIMI + articulos + versiones ---

SOCIMI_NORMA_SEED = """
INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde)
VALUES (
    'SOCIMI',
    'Ley 11/2009, de 22 de abril, de Sociedades de Inversion en el Mercado Inmobiliario',
    'BOE-A-2009-11218',
    'https://www.boe.es/diario_boe/txt.php?id=BOE-A-2009-11218',
    'es', 'boe', 'ley', 'societario_fiscal', 'ingestada', '2009-04-23'
)
"""

SOCIMI_ARTICULOS = [
    ("1", "Hecho imponible", "articulo"),
    ("2", "Sujetos", "articulo"),
    ("3", "Requisitos objetivos", "articulo"),
    ("4", "Requisitos formales", "articulo"),
    ("5", "Administracion y gobierno", "articulo"),
    ("12", "Distribucion de resultados", "articulo"),
    ("23", "Regimen fiscal", "articulo"),
    ("24", "Gravamen sobre beneficios no distribuidos", "articulo"),
]

SOCIMI_SEED_SQL = [SOCIMI_NORMA_SEED]

for numero, titulo, tipo in SOCIMI_ARTICULOS:
    SOCIMI_SEED_SQL.append(
        f"""
        INSERT INTO articulo (norma_id, numero, titulo, tipo)
        SELECT id, '{numero}', '{titulo}', '{tipo}' FROM norma WHERE codigo = 'SOCIMI'
        """
    )

SOCIMI_SEED_SQL.append(
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT id, 'Articulo 1. Las SOCIMI estan sujetas al Impuesto sobre Sociedades conforme a esta ley.',
           '2009-04-23', NULL, 'socimi-1'
    FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'SOCIMI') AND numero = '1'
    """
)

SOCIMI_SEED_SQL.append(
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT id, 'Articulo 12. Las SOCIMI distribuiran al menos el 80% de sus resultados imponibles.',
           '2009-04-23', NULL, 'socimi-12'
    FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'SOCIMI') AND numero = '12'
    """
)

SOCIMI_SEED_SQL.append(
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT id, 'Articulo 3. Para aplicar el regimen SOCIMI se requiere que el 80% del valor del activo sean inmuebles arrendados.',
           '2009-04-23', NULL, 'socimi-3'
    FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'SOCIMI') AND numero = '3'
    """
)


@pytest_asyncio.fixture(autouse=True)
async def _seed_socimi():
    """Semilla basica de norma SOCIMI para tests del router."""
    from db import engine

    with engine.begin() as conn:
        conn.execute(text("INSERT OR IGNORE INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde, regulacion_relacionada) VALUES ('SOCIMI', 'Ley 11/2009, de 22 de abril, de Sociedades de Inversion en el Mercado Inmobiliario', 'BOE-A-2009-11218', 'https://www.boe.es/diario_boe/txt.php?id=BOE-A-2009-11218', 'es', 'boe', 'ley', 'societario_fiscal', 'ingestada', '2009-04-23', 'socimi')"))
        conn.execute(text("INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) VALUES ('SOCIMI_TEST', 'Test norma SOCIMI', 'BOE-A-2009-11218-TEST', 'https://www.boe.es/eli/es/l/2009/04/22/11', 'es', 'boe', 'ley', 'societario_fiscal', 'ingestada', '2009-04-23')"))

        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '1', 'Hecho imponible', 'articulo' FROM norma WHERE codigo = 'SOCIMI_TEST'"
        ))
        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '12', 'Distribucion de resultados', 'articulo' FROM norma WHERE codigo = 'SOCIMI_TEST'"
        ))
        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '3', 'Requisitos objetivos', 'articulo' FROM norma WHERE codigo = 'SOCIMI_TEST'"
        ))

        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 1. Las SOCIMI estan sujetas al Impuesto sobre Sociedades conforme a esta ley.', '2009-04-23', NULL, 'socimi-1'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'SOCIMI_TEST') AND numero = '1'
            """
        ))
        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 12. Las SOCIMI distribuiran al menos el 80% de sus resultados imponibles.', '2009-04-23', NULL, 'socimi-12'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'SOCIMI_TEST') AND numero = '12'
            """
        ))
        conn.execute(text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT id, 'Articulo 3. Para aplicar el regimen SOCIMI se requiere que el 80% del valor del activo sean inmuebles arrendados.', '2009-04-23', NULL, 'socimi-3'
            FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'SOCIMI_TEST') AND numero = '3'
            """
        ))

        conn.execute(text(
            """
            INSERT OR IGNORE INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad)
            VALUES ('SOCIMI_ASSET_COMPOSITION', '>=80% activos inmobiliarios arrendados', 'Mantener >=80% del valor del activo en inmuebles arrendados (art. 3 Ley 11/2009)', 'socimi', 'societario_fiscal', 'periodicidad', 'anual', 'finanzas', 'alta')
            """
        ))
        conn.execute(text(
            """
            INSERT OR IGNORE INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad)
            VALUES ('SOCIMI_DISTRIBUTION', '>=80% distribucion de resultados', 'Distribuir >=80% de los resultados imponibles (art. 12 Ley 11/2009)', 'socimi', 'societario_fiscal', 'periodicidad', 'anual', 'finanzas', 'alta')
            """
        ))
        conn.execute(text(
            """
            INSERT OR IGNORE INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad)
            VALUES ('SOCIMI_TAX_UNDISTRIBUTED', 'Gravamen 15-19% beneficios no distribuidos', 'Gravamen 15-19% sobre beneficios no distribuidos (art. 24 Ley 11/2009)', 'socimi', 'tributario', 'periodicidad', 'anual', 'finanzas', 'media')
            """
        ))
        conn.execute(text(
            """
            INSERT OR IGNORE INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad)
            VALUES ('SOCIMI_TAX_REGIME', 'Regimen fiscal SOCIMI 0% IS', 'Aplicar regimen fiscal SOCIMI con tipo 0% si distribuye >=80% beneficios (art. 23 Ley 11/2009)', 'socimi', 'tributario', 'continuo', 'anual', 'finanzas', 'alta')
            """
        ))
        conn.execute(text(
            """
            INSERT OR IGNORE INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad)
            VALUES ('SOCIMI_80_20_RULE', 'Regla 80/20 SOCIMI', '80% activo inmobiliario arrendado + 20% liquidez maxima (art. 3 Ley 11/2009)', 'socimi', 'societario_fiscal', 'periodicidad', 'anual', 'finanzas', 'alta')
            """
        ))

    yield

    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM micro_obligacion WHERE regulacion_relacionada = 'socimi' AND codigo LIKE 'SOCIMI_%'"
        ))
        conn.execute(text(
            "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'SOCIMI_TEST'))"
        ))
        conn.execute(text(
            "DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'SOCIMI_TEST')"
        ))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'SOCIMI_TEST'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ====================================================================
# Test: GET /v1/socimi (lista normas)
# ====================================================================

class TestSocimiListaNormas:
    @pytest.mark.asyncio
    async def test_socimi_lista_status_200(self, client):
        resp = await client.get("/v1/socimi")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_socimi_lista_response_contiene_normas(self, client):
        resp = await client.get("/v1/socimi")
        data = resp.json()
        assert "normas" in data
        assert isinstance(data["normas"], list)

    @pytest.mark.asyncio
    async def test_socimi_lista_norma_socimi_presente(self, client):
        resp = await client.get("/v1/socimi")
        codigos = [n["codigo"] for n in resp.json()["normas"]]
        assert "SOCIMI" in codigos


# ====================================================================
# Test: GET /v1/socimi/{codigo} (detalle norma)
# ====================================================================

class TestSocimiDetalleNorma:
    @pytest.mark.asyncio
    async def test_socimi_norma_detalle_status_200(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_socimi_norma_detalle_codigo(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST")
        data = resp.json()
        assert data["codigo"] == "SOCIMI_TEST"

    @pytest.mark.asyncio
    async def test_socimi_norma_detalle_titulo(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST")
        data = resp.json()
        assert "Ley 11/2009" in data["titulo"] or "Test norma" in data["titulo"]

    @pytest.mark.asyncio
    async def test_socimi_norma_detalle_boe_id(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST")
        data = resp.json()
        assert data["boe_id"] == "BOE-A-2009-11218-TEST"

    @pytest.mark.asyncio
    async def test_socimi_norma_detalle_404(self, client):
        resp = await client.get("/v1/socimi/ZZZZZZZ")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/socimi/{codigo}/articulos (lista articulos)
# ====================================================================

class TestSocimiListaArticulos:
    @pytest.mark.asyncio
    async def test_socimi_articulos_status_200(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_socimi_articulos_response_model(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos")
        data = resp.json()
        assert "norma" in data
        assert "articulos" in data
        assert data["norma"] == "SOCIMI_TEST"

    @pytest.mark.asyncio
    async def test_socimi_articulos_contiene_articulos(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos")
        data = resp.json()
        articulo_nums = [a["numero"] for a in data["articulos"]]
        assert "1" in articulo_nums
        assert "12" in articulo_nums
        assert "3" in articulo_nums

    @pytest.mark.asyncio
    async def test_socimi_articulos_campo_numero(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos")
        for a in resp.json()["articulos"]:
            assert "numero" in a
            assert "titulo" in a
            assert "tipo" in a

    @pytest.mark.asyncio
    async def test_socimi_articulos_filtro_tipo(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos", params={"tipo": "articulo"})
        data = resp.json()
        for a in data["articulos"]:
            assert a["tipo"] == "articulo"

    @pytest.mark.asyncio
    async def test_socimi_articulos_404_norma_no_existente(self, client):
        resp = await client.get("/v1/socimi/ZZZZZZZ/articulos")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/socimi/{codigo}/articulos/{numero} (detalle articulo)
# ====================================================================

class TestSocimiDetalleArticulo:
    @pytest.mark.asyncio
    async def test_socimi_articulo_detalle_status_200(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_socimi_articulo_detalle_campos(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos/1")
        data = resp.json()
        assert data["norma"] == "SOCIMI_TEST"
        assert data["numero"] == "1"
        assert "texto" in data
        assert "vigente_desde" in data
        assert "confianza" in data

    @pytest.mark.asyncio
    async def test_socimi_articulo_detalle_texto_contenido(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos/1")
        data = resp.json()
        assert "SOCIMI" in data["texto"] or "Impuesto" in data["texto"]

    @pytest.mark.asyncio
    async def test_socimi_articulo_detalle_confianza_nivel(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos/1")
        data = resp.json()
        assert data["confianza"]["nivel"] == 1
        assert isinstance(data["confianza"]["fuentes"], list)

    @pytest.mark.asyncio
    async def test_socimi_articulo_detalle_404(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_socimi_articulo_detalle_vigente_en(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos/1", params={"vigente_en": "2024-01-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "SOCIMI_TEST"


# ====================================================================
# Test: GET /v1/socimi/{codigo}/articulos/{numero}/historial
# ====================================================================

class TestSocimiHistorialArticulo:
    @pytest.mark.asyncio
    async def test_socimi_historial_status_200(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos/1/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_socimi_historial_response_model(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos/1/historial")
        data = resp.json()
        assert "norma" in data
        assert "numero" in data
        assert "historial" in data
        assert isinstance(data["historial"], list)

    @pytest.mark.asyncio
    async def test_socimi_historial_version_campos(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos/1/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_socimi_historial_404(self, client):
        resp = await client.get("/v1/socimi/SOCIMI_TEST/articulos/9999/historial")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/socimi/micro-obligaciones
# ====================================================================

class TestSocimiMicroObligaciones:
    @pytest.mark.asyncio
    async def test_socimi_micro_obligaciones_status_200(self, client):
        resp = await client.get("/v1/socimi/micro-obligaciones")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_socimi_micro_obligaciones_response_model(self, client):
        resp = await client.get("/v1/socimi/micro-obligaciones")
        data = resp.json()
        assert "micro_obligaciones" in data
        assert "total" in data
        assert isinstance(data["micro_obligaciones"], list)

    @pytest.mark.asyncio
    async def test_socimi_micro_obligaciones_contiene_socimi(self, client):
        resp = await client.get("/v1/socimi/micro-obligaciones")
        data = resp.json()
        codigos = [m["codigo"] for m in data["micro_obligaciones"]]
        assert "SOCIMI_ASSET_COMPOSITION" in codigos
        assert "SOCIMI_DISTRIBUTION" in codigos
        assert "SOCIMI_TAX_UNDISTRIBUTED" in codigos
        assert "SOCIMI_TAX_REGIME" in codigos
        assert "SOCIMI_80_20_RULE" in codigos

    @pytest.mark.asyncio
    async def test_socimi_micro_obligaciones_total(self, client):
        resp = await client.get("/v1/socimi/micro-obligaciones")
        data = resp.json()
        assert data["total"] >= 5

    @pytest.mark.asyncio
    async def test_socimi_micro_obligaciones_campos(self, client):
        resp = await client.get("/v1/socimi/micro-obligaciones")
        data = resp.json()
        for m in data["micro_obligaciones"]:
            assert "codigo" in m
            assert "nombre" in m
            assert "descripcion" in m
            assert m["regulacion_relacionada"] == "socimi"
