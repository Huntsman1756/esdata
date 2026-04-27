"""Tests para el router de Ley 27/2014 (Impuesto sobre Sociedades).

Cubre: cobertura, articulos clave, detalle por numero e historial.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "workers"))

import pytest
import pytest_asyncio
from conftest import engine
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy import text

WORKERS_DIR = Path(__file__).resolve().parents[2] / "workers"


@pytest_asyncio.fixture(autouse=True)
async def _seed_lis():
    """Semilla basica de articulos LIS para tests del router."""
    fixtures_dir = WORKERS_DIR / "tests" / "fixtures" / "legalize_es"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixtures_dir / "lis.md"
    fixture.write_text(
            "# Ley 27/2014, de 27 de noviembre, del Impuesto sobre Sociedades\n"
            "Codigo: LIS\n"
            "Fecha version: 2014-11-27\n"
            "\n"
            "Articulo 1.\n"
            "Objeto. Este Impuesto grava la renta de las personas juridicas y otros entes que figuren en el art. 35.4 del Codigo Civil.\n"
            "\n"
            "Articulo 2.\n"
            "Hecho imponible. El hecho imponible consiste en la obtencion de rentas por las personas juridicas y entes mencionados.\n"
            "\n"
            "Articulo 3.\n"
            "Sujetos pasivos. Son sujetos pasivos las personas juridicas y entes previstos en el art. 35.4 del Codigo Civil.\n"
            "\n"
            "Articulo 15.\n"
            "Base imponible. La base imponible sera el resultado contable del ejercicio segun las normas contables aplicables, con las siguientes correcciones:\n"
            "a) Se incorporaran al resultado los rendimientos del capital mobiliario y las ganancias y perdidas patrimoniales.\n"
            "b) Se deduciran del resultado las cantidades entregadas a cambio de rentas del capital y las perdidas patrimoniales.\n"
            "\n"
            "Articulo 20.\n"
            "Deducciones. Las deducciones permitidas en este Impuesto son las establecidas en las leyes de los Presupuestos Generales del Estado.\n"
            "\n"
            "Articulo 24.\n"
            "Deber de informacion. Las sociedades vinculadas deberan intercambiar la informacion necesaria para la determinacion del resultado del grupo.\n"
            "\n"
            "Articulo 100.\n"
            "Transmisiones patrimoniales. Las transmisiones patrimoniales onerosas se valoraran por el valor real de los mismos o por el de la contraprestacion.\n"
            "\n"
            "Articulo 135.\n"
            "Conciliacion fiscal. El contribuyente debera presentar una declaracion de conciliacion entre la base imponible contable y la fiscal.\n"
            "\n"
            "Articulo 140.\n"
            "Precios de transferencia. Las operaciones entre partes vinculadas se valoraran segun el metodo de libre concurrence.\n"
            "\n"
            "Articulo 200.\n"
            "Deducciones. Las deducciones permitidas en este Impuesto son las establecidas en las leyes de los Presupuestos Generales del Estado.\n"
            "\n"
            "Articulo 240.\n"
            "Presentacion. La declaracion se presentara en el modelo 200 dentro de los seis primeros meses del periodo impositivo.\n"
            "\n"
            "Articulo 252.\n"
            "Responsables. Los administradores de las sociedades respondern del cumplimiento de las obligaciones tributarias.\n",
            encoding="utf-8",
        )

    from legalize_es import run_sync

    run_sync(engine, fixture_paths=[fixture])

    yield

    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LIS'))"
            )
        )
        conn.execute(
            text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LIS')")
        )
        conn.execute(text("DELETE FROM norma WHERE codigo = 'LIS'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestLisRouterCobertura:
    """Tests de cobertura para el endpoint /v1/ley272014/cobertura."""

    @pytest.mark.asyncio
    async def test_cobertura_returns_200(self, client):
        resp = await client.get("/v1/ley272014/cobertura")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cobertura_returns_articulo_count(self, client):
        resp = await client.get("/v1/ley272014/cobertura")
        data = resp.json()
        assert "articulos" in data
        assert data["articulos"] > 0

    @pytest.mark.asyncio
    async def test_cobertura_returns_norma_code(self, client):
        resp = await client.get("/v1/ley272014/cobertura")
        data = resp.json()
        assert data["codigo"] == "LIS"

    @pytest.mark.asyncio
    async def test_cobertura_returns_key_articles_count(self, client):
        resp = await client.get("/v1/ley272014/cobertura")
        data = resp.json()
        assert "articulos_clave" in data
        assert data["articulos_clave"] > 0


class TestLisRouterArticulosClave:
    """Tests para el endpoint /v1/ley272014/articulos-clave."""

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_200(self, client):
        resp = await client.get("/v1/ley272014/articulos-clave")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_list(self, client):
        resp = await client.get("/v1/ley272014/articulos-clave")
        data = resp.json()
        assert isinstance(data["articulos_clave"], list)
        assert len(data["articulos_clave"]) > 0

    @pytest.mark.asyncio
    async def test_articulos_clave_has_required_fields(self, client):
        resp = await client.get("/v1/ley272014/articulos-clave")
        data = resp.json()
        for articulo in data["articulos_clave"]:
            assert "numero" in articulo
            assert "descripcion" in articulo

    @pytest.mark.asyncio
    async def test_articulos_clave_includes_expected_articles(self, client):
        resp = await client.get("/v1/ley272014/articulos-clave")
        data = resp.json()
        nums = {a["numero"] for a in data["articulos_clave"]}
        assert "2" in nums
        assert "15" in nums
        assert "240" in nums


class TestLisRouterArticuloDetalle:
    """Tests para el endpoint /v1/ley272014/articulos/{numero}."""

    @pytest.mark.asyncio
    async def test_articulo_2_returns_200(self, client):
        resp = await client.get("/v1/ley272014/articulos/2")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_2_has_required_fields(self, client):
        resp = await client.get("/v1/ley272014/articulos/2")
        data = resp.json()
        assert data["norma"] == "LIS"
        assert data["numero"] == "2"
        assert "texto" in data
        assert "vigente_desde" in data

    @pytest.mark.asyncio
    async def test_articulo_15_returns_200(self, client):
        resp = await client.get("/v1/ley272014/articulos/15")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_15_base_imponible(self, client):
        resp = await client.get("/v1/ley272014/articulos/15")
        data = resp.json()
        assert "imponible" in data["texto"].lower() or "resultado" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_240_returns_200(self, client):
        resp = await client.get("/v1/ley272014/articulos/240")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_240_presentacion(self, client):
        resp = await client.get("/v1/ley272014/articulos/240")
        data = resp.json()
        assert "presentacion" in data["texto"].lower() or "modelo" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/ley272014/articulos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_articulo_with_vigente_en_filter(self, client):
        resp = await client.get("/v1/ley272014/articulos/2", params={"vigente_en": "2024-01-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "LIS"

    @pytest.mark.asyncio
    async def test_articulo_240_has_ley_field(self, client):
        resp = await client.get("/v1/ley272014/articulos/240")
        data = resp.json()
        assert data.get("ley") == "27/2014"

    @pytest.mark.asyncio
    async def test_articulo_240_has_source(self, client):
        resp = await client.get("/v1/ley272014/articulos/240")
        data = resp.json()
        assert data.get("fuente") == "BOE-A-2014-12328"


class TestLisRouterHistorial:
    """Tests para el endpoint /v1/ley272014/articulos/{numero}/historial."""

    @pytest.mark.asyncio
    async def test_historial_articulo_2_returns_200(self, client):
        resp = await client.get("/v1/ley272014/articulos/2/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_historial_has_versiones(self, client):
        resp = await client.get("/v1/ley272014/articulos/2/historial")
        data = resp.json()
        assert "historial" in data
        assert isinstance(data["historial"], list)
        assert len(data["historial"]) > 0

    @pytest.mark.asyncio
    async def test_historial_version_has_fields(self, client):
        resp = await client.get("/v1/ley272014/articulos/2/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_historial_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/ley272014/articulos/9999/historial")
        assert resp.status_code == 404


class TestLisRouterIntegration:
    """Tests de integracion del router con el sistema de busqueda."""

    @pytest.mark.asyncio
    async def test_search_legislacion_returns_lis_articles(self, client):
        from services.search import search_legislacion

        result = search_legislacion("sociedades", norma="LIS")
        assert "resultados" in result
        assert isinstance(result["resultados"], list)

    @pytest.mark.asyncio
    async def test_search_legislacion_lis_hecho_imponible(self, client):
        from services.search import search_legislacion

        result = search_legislacion("hecho imponible", norma="LIS")
        assert "resultados" in result

    @pytest.mark.asyncio
    async def test_search_legislacion_lis_deduciones(self, client):
        from services.search import search_legislacion

        result = search_legislacion("deducciones", norma="LIS")
        assert "resultados" in result
