"""Tests para el router de Real Decreto 217/2008 (normas contables).

Cubre: cobertura, articulos clave, detalle por numero e historial.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "workers"))

import pytest
import pytest_asyncio
from .conftest import engine
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy import text

WORKERS_DIR = Path(__file__).resolve().parents[2] / "workers"


@pytest_asyncio.fixture(autouse=True)
async def _seed_rd2172008():
    """Semilla basica de articulos RD 217/2008 para tests del router."""
    fixtures_dir = WORKERS_DIR / "tests" / "fixtures" / "legalize_es"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixtures_dir / "rd2172008.md"
    fixture.write_text(
        "# Real Decreto 217/2008, de 14 de febrero, sobre normas contables para sociedades que elaboren estados financieros individualmente o consolidadas\n"
        "Codigo: RD2172008\n"
        "Fecha version: 2008-02-14\n"
        "\n"
        "Articulo 1.\n"
        "Objeto. Este real decreto aprueba las normas contables para las entidades a que se refiere el articulo 2.\n"
        "\n"
        "Articulo 2.\n"
        "Ambito de aplicacion. Seran de aplicacion las sociedades bancarias, sociedades de valores, aseguradoras y otras entidades financieras.\n"
        "\n"
        "Articulo 3.\n"
        "Provisiones. Se constituiran las provisiones necesarias para cubrir los riesgos y gastos conocidos, aunque su cuantia o fecha de realizacion sean inciertas.\n"
        "\n"
        "Articulo 4.\n"
        "Valoracion de provisiones. Las provisiones se valoraran a la mejor estimacion del importe que sea necesario para cubrir los riesgos al momento del cierre del ejercicio.\n"
        "\n"
        "Articulo 5.\n"
        "Activos financieros. Los activos financieros se clasificararan en las siguientes categorias: activos a valor razonable con cambios en resultados, inversiones mantenidas hasta su vencimiento, prestamos y cobros, y disponibles para la venta.\n"
        "\n"
        "Articulo 6.\n"
        "Valoracion de activos financieros. Los activos financieros a valor razonable se valoraran a su valor razonable en el balance, con los cambios reconocidos en la cuenta de perdidas y ganancias.\n"
        "\n"
        "Articulo 7.\n"
        "Deterioro de activos financieros. Se reconocera el deterioro cuando el valor recobrable sea inferior al valor en libros.\n"
        "\n"
        "Articulo 8.\n"
        "Clasificacion de instrumentos. Los instrumentos financieros se clasificaran segun el modelo de negocio y las caracteristicas de los flujos de efectivo contractuales.\n"
        "\n"
        "Articulo 9.\n"
        "Instrumentos de patrimonio. Las inversiones en instrumentos de patrimonio se clasificaran a valor razonable con cambios en resultados.\n"
        "\n"
        "Articulo 10.\n"
        "Instrumentos derivados. Los instrumentos derivados se valoraran a valor razonable y se reconoceran como activos o pasivos financieros segun su valor positivo o negativo.\n"
        "\n"
        "Articulo 11.\n"
        "Coberturas. Las relaciones de coberturas que cumplan los requisitos establecidos podran contabilizarse contablemente como operaciones de cobertura.\n"
        "\n"
        "Articulo 12.\n"
        "Cuenta de perdidas y ganancias. Se presentara diferenciando los incrementos y disminuciones en el patrimonio neto originados por la explotacion.\n"
        "\n"
        "Articulo 13.\n"
        "Balance. El activo se presentara distinguiendo entre activos corrientes y no corrientes. El pasivo se clasificara segun su naturaleza.\n"
        "\n"
        "Articulo 14.\n"
        "Estado de cambios en el patrimonio neto. Se presentara como estado financiero diferenciado o como parte de un estado integral de ingresos.\n"
        "\n"
        "Articulo 15.\n"
        "Estados financieros basicos. Los estados financieros basicos comprenderan el balance, la cuenta de perdidas y ganancias, el estado de cambios en el patrimonio neto, el estado de flujos de efectivo y la memoria.\n"
        "\n"
        "Articulo 16.\n"
        "Estado de flujos de efectivo. Se presentara diferenciando las actividades de explotacion, inversion y financiacion.\n"
        "\n"
        "Articulo 17.\n"
        "Memoria. En la memoria se informara sobre las politicas contables aplicadas y demas informacion complementaria.\n"
        "\n"
        "Articulo 18.\n"
        "Notas a los estados financieros. Las notas comprenderan informacion sobre las politicas contables, notas explicativas y otras revelaciones.\n"
        "\n"
        "Articulo 20.\n"
        "Normas de consolidacion. Las sociedades que elaboren estados financieros consolidados adaptaran las normas contables a las especificidades del grupo.\n"
        "\n"
        "Articulo 22.\n"
        "Entidades de pequeno tamanho. Las entidades de pequeno tamanho podran aplicar normas simplificadas de presentacion e informacion.\n"
        "\n"
        "Articulo 25.\n"
        "Informacion complementaria. Se revelaran los riesgos financieros, las ratios prudenciales y la gestion de riesgos de mercado y credito.\n"
        "\n"
        "Articulo 27.\n"
        "Instrumentos financieros derivados. Se informara sobre la politica de gestion de riesgos y el uso de instrumentos derivados.\n"
        "\n"
        "Articulo 30.\n"
        "Disposicion adicional. Se autoriza al Ministro de Economia para aprobar las normas de desarrollo de este real decreto.\n"
        "\n",
        encoding="utf-8",
    )

    from legalize_es import run_sync

    run_sync(engine, fixture_paths=[fixture])

    yield

    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'RD2172008'))"
            )
        )
        conn.execute(
            text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'RD2172008')")
        )
        conn.execute(text("DELETE FROM norma WHERE codigo = 'RD2172008'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestRD2172008RouterCobertura:
    """Tests de cobertura para el endpoint /v1/rd2172008/cobertura."""

    @pytest.mark.asyncio
    async def test_cobertura_returns_200(self, client):
        resp = await client.get("/v1/rd2172008/cobertura")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cobertura_returns_articulo_count(self, client):
        resp = await client.get("/v1/rd2172008/cobertura")
        data = resp.json()
        assert "articulos" in data
        assert data["articulos"] > 0

    @pytest.mark.asyncio
    async def test_cobertura_returns_norma_code(self, client):
        resp = await client.get("/v1/rd2172008/cobertura")
        data = resp.json()
        assert data["codigo"] == "RD2172008"

    @pytest.mark.asyncio
    async def test_cobertura_returns_key_articles_count(self, client):
        resp = await client.get("/v1/rd2172008/cobertura")
        data = resp.json()
        assert "articulos_clave" in data
        assert data["articulos_clave"] > 0

    @pytest.mark.asyncio
    async def test_cobertura_returns_versiones(self, client):
        resp = await client.get("/v1/rd2172008/cobertura")
        data = resp.json()
        assert "versiones" in data


class TestRD2172008RouterArticulosClave:
    """Tests para el endpoint /v1/rd2172008/articulos-clave."""

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_200(self, client):
        resp = await client.get("/v1/rd2172008/articulos-clave")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_list(self, client):
        resp = await client.get("/v1/rd2172008/articulos-clave")
        data = resp.json()
        assert isinstance(data["articulos_clave"], list)
        assert len(data["articulos_clave"]) > 0

    @pytest.mark.asyncio
    async def test_articulos_clave_has_required_fields(self, client):
        resp = await client.get("/v1/rd2172008/articulos-clave")
        data = resp.json()
        for articulo in data["articulos_clave"]:
            assert "numero" in articulo
            assert "descripcion" in articulo

    @pytest.mark.asyncio
    async def test_articulos_clave_includes_expected_articles(self, client):
        resp = await client.get("/v1/rd2172008/articulos-clave")
        data = resp.json()
        nums = {a["numero"] for a in data["articulos_clave"]}
        assert "3" in nums
        assert "5" in nums
        assert "8" in nums

    @pytest.mark.asyncio
    async def test_articulos_clave_norma_field(self, client):
        resp = await client.get("/v1/rd2172008/articulos-clave")
        data = resp.json()
        assert data["norma"] == "RD2172008"


class TestRD2172008RouterArticuloDetalle:
    """Tests para el endpoint /v1/rd2172008/articulos/{numero}."""

    @pytest.mark.asyncio
    async def test_articulo_3_returns_200(self, client):
        resp = await client.get("/v1/rd2172008/articulos/3")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_3_has_required_fields(self, client):
        resp = await client.get("/v1/rd2172008/articulos/3")
        data = resp.json()
        assert data["norma"] == "RD2172008"
        assert data["numero"] == "3"
        assert "texto" in data
        assert "vigente_desde" in data

    @pytest.mark.asyncio
    async def test_articulo_5_activos_financieros(self, client):
        resp = await client.get("/v1/rd2172008/articulos/5")
        data = resp.json()
        assert "financiero" in data["texto"].lower() or "clasificar" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_5_has_key_flag(self, client):
        resp = await client.get("/v1/rd2172008/articulos/5")
        data = resp.json()
        assert data["clave"] is True

    @pytest.mark.asyncio
    async def test_articulo_8_clasificacion(self, client):
        resp = await client.get("/v1/rd2172008/articulos/8")
        data = resp.json()
        assert "clasif" in data["texto"].lower() or "instrumento" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/rd2172008/articulos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_articulo_with_vigente_en_filter(self, client):
        resp = await client.get("/v1/rd2172008/articulos/3", params={"vigente_en": "2024-01-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "RD2172008"

    @pytest.mark.asyncio
    async def test_articulo_15_has_ley_field(self, client):
        resp = await client.get("/v1/rd2172008/articulos/15")
        data = resp.json()
        assert data.get("ley") == "217/2008"

    @pytest.mark.asyncio
    async def test_articulo_20_has_source(self, client):
        resp = await client.get("/v1/rd2172008/articulos/20")
        data = resp.json()
        assert data.get("fuente") == "BOE-A-2008-500"

    @pytest.mark.asyncio
    async def test_articulo_25_has_text(self, client):
        resp = await client.get("/v1/rd2172008/articulos/25")
        data = resp.json()
        assert "texto" in data
        assert len(data["texto"]) > 0


class TestRD2172008RouterHistorial:
    """Tests para el endpoint /v1/rd2172008/articulos/{numero}/historial."""

    @pytest.mark.asyncio
    async def test_historial_articulo_3_returns_200(self, client):
        resp = await client.get("/v1/rd2172008/articulos/3/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_historial_has_versiones(self, client):
        resp = await client.get("/v1/rd2172008/articulos/3/historial")
        data = resp.json()
        assert "historial" in data
        assert isinstance(data["historial"], list)
        assert len(data["historial"]) > 0

    @pytest.mark.asyncio
    async def test_historial_version_has_fields(self, client):
        resp = await client.get("/v1/rd2172008/articulos/3/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_historial_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/rd2172008/articulos/9999/historial")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_historial_norma_field(self, client):
        resp = await client.get("/v1/rd2172008/articulos/3/historial")
        data = resp.json()
        assert data["norma"] == "RD2172008"
