"""Tests para el router de Directivas DAC (DAC1-DAC9) (Fase 28.1).

Cubre: lista de normas, detalle de norma, articulos, detalle de articulo
y historial de versiones para DAC6 (norma con articulos) y DAC1 (breve).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy import text


@pytest_asyncio.fixture(autouse=True)
async def _seed_dac():
    """Semilla basica de normas DAC para tests del router.

    Limpia datos DAC del seed global de conftest para asegurar que los IDs
    de articulo sean pequenos y el fixture dac6_articulo_ids los encuentre
    antes de llegar a 200.
    """
    from db import engine

    with engine.begin() as conn:
        # Limpiar datos DAC del seed global para evitar colision de UNIQUE(codigo)
        # y que los articulos queden con IDs predecibles (1, 2, 3...)
        conn.execute(text(
            "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo IN ('DAC6', 'DAC7', 'DAC1')))"
        ))
        conn.execute(text(
            "DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo IN ('DAC6', 'DAC7', 'DAC1'))"
        ))
        conn.execute(text(
            "DELETE FROM norma WHERE codigo IN ('DAC6', 'DAC7', 'DAC1')"
        ))
        # Reset autoincrement para que las nuevas normas/articulos queden con IDs <= 200
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name IN ('norma', 'articulo', 'version_articulo')"))

        # DAC6 — con articulos
        conn.execute(text(
            """INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde, regulacion_relacionada)
               VALUES ('DAC6', 'Directiva (UE) 2018/822 — Reporte obligatorio de arreglos transfronterizos agresivos', 'Directiva (UE) 2018/822', 'https://www.eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32018L0822', 'eu', 'eurlex', 'directiva', 'fiscal_internacional', 'ingestada', '2018-06-25', 'dac_directives')"""
        ))
        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '1', 'Alcance DAC6', 'articulo' FROM norma WHERE codigo = 'DAC6'"
        ))
        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '6', 'Obligacion de Reporte', 'articulo' FROM norma WHERE codigo = 'DAC6'"
        ))
        conn.execute(text(
            """INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta)
               SELECT id, 'Articulo 1. Obliga a intermediarios a reportar arreglos transfronterizos agresivos.', '2018-06-25', NULL
               FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'DAC6') AND numero = '1'"""
        ))
        conn.execute(text(
            """INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta)
               SELECT id, 'Articulo 6. Los intermediarios deben reportar a la autoridad fiscal dentro de 30 dias.', '2018-06-25', NULL
               FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'DAC6') AND numero = '6'"""
        ))

        # DAC7 — con articulos
        conn.execute(text(
            """INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde, regulacion_relacionada)
               VALUES ('DAC7', 'Directiva (UE) 2022/2361 — Informacion para plataformas digitales', 'Directiva (UE) 2022/2361', 'https://www.eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022L2361', 'eu', 'eurlex', 'directiva', 'fiscal_internacional', 'ingestada', '2022-12-22', 'dac_directives')"""
        ))

        # DAC1 — sin articulos
        conn.execute(text(
            """INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde, regulacion_relacionada)
               VALUES ('DAC1', 'Directiva (UE) 77/780 — DAC1', 'EUR-Lex-31977L0780', 'https://eur-lex.europa.eu/eli/dir/1977/780/oj', 'ue', 'eurlex', 'directiva_ue', 'tributario_internacional', 'ingestada', '1977-11-12', 'dac_directives')"""
        ))
        conn.execute(text(
            "INSERT INTO articulo (norma_id, numero, titulo, tipo) SELECT id, '1', 'Alcance DAC7', 'articulo' FROM norma WHERE codigo = 'DAC7'"
        ))
        conn.execute(text(
            """INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta)
               SELECT id, 'Articulo 1. Obliga a plataformas digitales a reportar informacion sobre vendedores.', '2022-12-22', NULL
               FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'DAC7') AND numero = '1'"""
        ))

    yield

    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo IN ('DAC6', 'DAC7', 'DAC1')))"
        ))
        conn.execute(text(
            "DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo IN ('DAC6', 'DAC7', 'DAC1'))"
        ))
        conn.execute(text("DELETE FROM norma WHERE codigo IN ('DAC6', 'DAC7', 'DAC1')"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def dac6_articulo_ids(client):
    """Resuelve los IDs de los articulos de DAC6 via el endpoint de detalle."""
    ids = {}
    for i in range(1, 200):
        resp = await client.get(f"/v1/dac/articulos/{i}")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("norma") == "DAC6":
                if data.get("numero") == "1":
                    ids["dac6_art1"] = i
                elif data.get("numero") == "6":
                    ids["dac6_art6"] = i
        elif resp.status_code == 404 and len(ids) > 0:
            # Ya no hay mas articulos, salir
            break
    return ids


# ====================================================================
# Test: GET /v1/dac/normas (lista normas)
# ====================================================================

class TestDACListaNormas:
    @pytest.mark.asyncio
    async def test_dac_lista_status_200(self, client):
        resp = await client.get("/v1/dac/normas", params={"estado": "ingestada"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dac_lista_response_model(self, client):
        resp = await client.get("/v1/dac/normas", params={"estado": "ingestada"})
        data = resp.json()
        assert "normas" in data
        assert "total" in data
        assert isinstance(data["normas"], list)

    @pytest.mark.asyncio
    async def test_dac_lista_normas_presentes(self, client):
        resp = await client.get("/v1/dac/normas", params={"estado": "ingestada"})
        codigos = [n["codigo"] for n in resp.json()["normas"]]
        assert "DAC6" in codigos
        assert "DAC7" in codigos
        assert "DAC1" in codigos

    @pytest.mark.asyncio
    async def test_dac_lista_regulacion_relacionada(self, client):
        resp = await client.get("/v1/dac/normas", params={"estado": "ingestada"})
        data = resp.json()
        for norma in data["normas"]:
            assert norma.get("regulacion_relacionada") == "dac_directives"

    @pytest.mark.asyncio
    async def test_dac_lista_filtro_codigo(self, client):
        resp = await client.get("/v1/dac/normas", params={"codigo": "DAC6", "estado": "ingestada"})
        data = resp.json()
        assert data["total"] >= 1
        codigos = [n["codigo"] for n in data["normas"]]
        assert "DAC6" in codigos
        assert "DAC7" not in codigos

    @pytest.mark.asyncio
    async def test_dac_lista_total_minimo(self, client):
        resp = await client.get("/v1/dac/normas", params={"estado": "ingestada"})
        assert resp.json()["total"] >= 3


# ====================================================================
# Test: GET /v1/dac/normas/{codigo} (detalle norma)
# ====================================================================

class TestDACDetalleNorma:
    @pytest.mark.asyncio
    async def test_dac_norma_detalle_status_200(self, client):
        resp = await client.get("/v1/dac/normas/DAC6")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dac_norma_detalle_codigo(self, client):
        resp = await client.get("/v1/dac/normas/DAC6")
        assert resp.json()["codigo"] == "DAC6"

    @pytest.mark.asyncio
    async def test_dac_norma_detalle_titulo(self, client):
        resp = await client.get("/v1/dac/normas/DAC6")
        assert "2018/822" in resp.json()["titulo"]

    @pytest.mark.asyncio
    async def test_dac_norma_detalle_jurisdiccion(self, client):
        resp = await client.get("/v1/dac/normas/DAC6")
        assert resp.json()["jurisdiccion"] == "eu"

    @pytest.mark.asyncio
    async def test_dac_norma_detalle_tipo_fuente(self, client):
        resp = await client.get("/v1/dac/normas/DAC6")
        assert resp.json()["tipo_fuente"] == "eurlex"

    @pytest.mark.asyncio
    async def test_dac_norma_detalle_404(self, client):
        resp = await client.get("/v1/dac/normas/ZZZZZZZ")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/dac/articulos (lista articulos)
# ====================================================================

class TestDACListaArticulos:
    @pytest.mark.asyncio
    async def test_dac_articulos_status_200(self, client):
        resp = await client.get("/v1/dac/articulos")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dac_articulos_response_model(self, client):
        resp = await client.get("/v1/dac/articulos")
        data = resp.json()
        assert "norma" in data
        assert "articulos" in data
        assert "total" in data
        assert isinstance(data["articulos"], list)

    @pytest.mark.asyncio
    async def test_dac_articulos_dac6_contiene_articulos(self, client):
        resp = await client.get("/v1/dac/articulos", params={"codigo_norma": "DAC6"})
        data = resp.json()
        articulo_nums = [a["numero"] for a in data["articulos"]]
        assert "1" in articulo_nums
        assert "6" in articulo_nums

    @pytest.mark.asyncio
    async def test_dac_articulos_dac7_contiene_articulos(self, client):
        resp = await client.get("/v1/dac/articulos", params={"codigo_norma": "DAC7"})
        data = resp.json()
        articulo_nums = [a["numero"] for a in data["articulos"]]
        assert "1" in articulo_nums

    @pytest.mark.asyncio
    async def test_dac_articulos_sin_articulos(self, client):
        # DAC1 no tiene articulos
        resp = await client.get("/v1/dac/articulos", params={"codigo_norma": "DAC1"})
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_dac_articulos_campos(self, client):
        resp = await client.get("/v1/dac/articulos")
        for a in resp.json()["articulos"]:
            assert "numero" in a
            assert "titulo" in a
            assert "tipo" in a


# ====================================================================
# Test: GET /v1/dac/articulos/{articulo_id} (detalle articulo)
# ====================================================================

class TestDACDetalleArticulo:
    @pytest.mark.asyncio
    async def test_dac_articulo_detalle_status_200(self, client, dac6_articulo_ids):
        articulo_id = dac6_articulo_ids.get("dac6_art1")
        assert articulo_id is not None, "No se encontro articulo 1 de DAC6"
        resp = await client.get(f"/v1/dac/articulos/{articulo_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dac_articulo_detalle_campos(self, client, dac6_articulo_ids):
        articulo_id = dac6_articulo_ids.get("dac6_art1")
        assert articulo_id is not None
        resp = await client.get(f"/v1/dac/articulos/{articulo_id}")
        data = resp.json()
        assert "numero" in data
        assert "titulo" in data
        assert "texto" in data
        assert "vigente_desde" in data

    @pytest.mark.asyncio
    async def test_dac_articulo_detalle_texto(self, client, dac6_articulo_ids):
        articulo_id = dac6_articulo_ids.get("dac6_art1")
        assert articulo_id is not None
        resp = await client.get(f"/v1/dac/articulos/{articulo_id}")
        data = resp.json()
        assert "intermediarios" in data["texto"].lower() or "report" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_dac_articulo_detalle_404(self, client):
        resp = await client.get("/v1/dac/articulos/9999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/dac/articulos/{articulo_id}/historial
# ====================================================================

class TestDACHistorialArticulo:
    @pytest.mark.asyncio
    async def test_dac_historial_status_200(self, client, dac6_articulo_ids):
        articulo_id = dac6_articulo_ids.get("dac6_art1")
        assert articulo_id is not None
        resp = await client.get(f"/v1/dac/articulos/{articulo_id}/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dac_historial_response_model(self, client, dac6_articulo_ids):
        articulo_id = dac6_articulo_ids.get("dac6_art1")
        assert articulo_id is not None
        resp = await client.get(f"/v1/dac/articulos/{articulo_id}/historial")
        data = resp.json()
        assert "articulos" in data
        assert isinstance(data["articulos"], list)

    @pytest.mark.asyncio
    async def test_dac_historial_campos(self, client, dac6_articulo_ids):
        articulo_id = dac6_articulo_ids.get("dac6_art1")
        assert articulo_id is not None
        resp = await client.get(f"/v1/dac/articulos/{articulo_id}/historial")
        data = resp.json()
        for version in data["articulos"]:
            assert "numero" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_dac_historial_404(self, client):
        resp = await client.get("/v1/dac/articulos/9999/historial")
        assert resp.status_code == 404
