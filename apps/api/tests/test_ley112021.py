"""Tests para el router de Ley 11/2021 de prevencion y prevencion del fraude.

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
async def _seed_ley112021():
    """Semilla basica de articulos Ley 11/2021 para tests del router."""
    fixtures_dir = WORKERS_DIR / "tests" / "fixtures" / "legalize_es"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixtures_dir / "ley112021.md"
    fixture.write_text(
            "# Ley 11/2021, de 9 de julio, de prevencion y prevencion del fraude\n"
            "Codigo: LEY112021\n"
            "Fecha version: 2021-07-09\n"
            "\n"
            "Articulo 1.\n"
            "Limitaciones de pagos en efectivo. No se admitiran los pagos en efectivo que, de forma aislada o simultanea, superen la cantidad de 1.000 euros.\n"
            "\n"
            "Articulo 2.\n"
            "Exenciones. Las limitaciones del articulo 1 no seran de aplicacion a las operaciones que se realicen a traves de instrumentos electronicos o crediticos.\n"
            "\n"
            "Articulo 3.\n"
            "Obligaciones de software factoriales. Los obligados a expedir facturas deberan disponer de sistemas informaticos que garanticen la correcta registracion y conservacion de las mismas.\n"
            "\n"
            "Articulo 4.\n"
            "Requisitos del software. Los sistemas informaticos deberan permitir la generacion inalterable de facturas con los datos exigidos legalmente.\n"
            "\n"
            "Articulo 5.\n"
            "Registro de facturas recibidas y expedidas. Los obligados deberan llevar un registro de todas las facturas recibidas y expedidas, con inclusion de los datos exigidos legalmente.\n"
            "\n"
            "Articulo 6.\n"
            "Obligacion de conservacion. Las facturas y documentos justificativos se conservaran durante un plazo minimo de cuatro anos.\n"
            "\n"
            "Articulo 7.\n"
            "Comunicacion de facturas. Se comunicaran a la Administracion tributaria las facturas expedidas y recibidas en los terminos establecidos reglamentariamente.\n"
            "\n"
            "Articulo 8.\n"
            "Obligados a llevar contabilidad. Tendran la obligacion de llevar contabilidad los sujetos pasivos que realicen actividades economicas.\n"
            "\n"
            "Articulo 9.\n"
            "Obligacion de expedir facturas. Se expediran facturas en todas las entregas de bienes y prestaciones de servicios realizadas por los profesionales.\n"
            "\n"
            "Articulo 10.\n"
            "Divulgacion de datos. Los obligados deberan informar sobre los datos de sus representantes legales y personas con poderes de representacion.\n"
            "\n"
            "Articulo 11.\n"
            "Obligacion de conservacion de documentos. Los documentos se conservaran en soporte papel o informatico durante al menos cuatro anos.\n"
            "\n"
            "Articulo 12.\n"
            "Devolucion de la diferencia. Cuando los pagos superen los limites establecidos, se procedera a la devolucion de la diferencia.\n"
            "\n"
            "Articulo 13.\n"
            "Medios electronicos. Las obligaciones establecidas en esta ley se podran cumplir por medios electronicos.\n"
            "\n"
            "Articulo 14.\n"
            "Certificados de representacion. Se exigira certificado de identidad y representacion de los afectados en los terminos reglamentarios.\n"
            "\n"
            "Articulo 15.\n"
            "Registro de operaciones. Se llevara un registro de las operaciones realizadas que superen los limites establecidos.\n"
            "\n"
            "Articulo 16.\n"
            "Verificacion de identidad. Se verificara la identidad de los clientes en las operaciones sujetas a limitaciones.\n"
            "\n"
            "Articulo 17.\n"
            "Colaboracion con la administracion. Los obligados colaboraran con las administraciones tributarias en la prevencion del fraude.\n"
            "\n"
            "Articulo 18.\n"
            "Regimen sancionador. El incumplimiento de las obligaciones establecidas en esta ley dara lugar a las sanciones previstas reglamentariamente.\n"
            "\n"
            "Disposicion adicional primera.\n"
            "Regimen transitorio. Se establece un regimen transitorio para la adaptacion de los sistemas informaticos.\n"
            "\n"
            "Disposicion final primera.\n"
            "Habilitacion para el desarrollo normativo. Se habilita al Gobierno para el desarrollo reglamentario de esta ley.\n",
            encoding="utf-8",
        )

    from legalize_es import run_sync

    run_sync(engine, fixture_paths=[fixture])

    yield

    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEY112021'))"
            )
        )
        conn.execute(
            text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEY112021')")
        )
        conn.execute(text("DELETE FROM norma WHERE codigo = 'LEY112021'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestLey112021RouterCobertura:
    """Tests de cobertura para el endpoint /v1/ley112021/cobertura."""

    @pytest.mark.asyncio
    async def test_cobertura_returns_200(self, client):
        resp = await client.get("/v1/ley112021/cobertura")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cobertura_returns_articulo_count(self, client):
        resp = await client.get("/v1/ley112021/cobertura")
        data = resp.json()
        assert "articulos" in data
        assert data["articulos"] > 0

    @pytest.mark.asyncio
    async def test_cobertura_returns_norma_code(self, client):
        resp = await client.get("/v1/ley112021/cobertura")
        data = resp.json()
        assert data["codigo"] == "LEY112021"

    @pytest.mark.asyncio
    async def test_cobertura_returns_key_articles_count(self, client):
        resp = await client.get("/v1/ley112021/cobertura")
        data = resp.json()
        assert "articulos_clave" in data
        assert data["articulos_clave"] > 0


class TestLey112021RouterArticulosClave:
    """Tests para el endpoint /v1/ley112021/articulos-clave."""

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_200(self, client):
        resp = await client.get("/v1/ley112021/articulos-clave")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_list(self, client):
        resp = await client.get("/v1/ley112021/articulos-clave")
        data = resp.json()
        assert isinstance(data["articulos_clave"], list)
        assert len(data["articulos_clave"]) > 0

    @pytest.mark.asyncio
    async def test_articulos_clave_has_required_fields(self, client):
        resp = await client.get("/v1/ley112021/articulos-clave")
        data = resp.json()
        for articulo in data["articulos_clave"]:
            assert "numero" in articulo
            assert "descripcion" in articulo

    @pytest.mark.asyncio
    async def test_articulos_clave_includes_expected_articles(self, client):
        resp = await client.get("/v1/ley112021/articulos-clave")
        data = resp.json()
        nums = {a["numero"] for a in data["articulos_clave"]}
        assert "1" in nums
        assert "3" in nums
        assert "18" in nums


class TestLey112021RouterArticuloDetalle:
    """Tests para el endpoint /v1/ley112021/articulos/{numero}."""

    @pytest.mark.asyncio
    async def test_articulo_1_returns_200(self, client):
        resp = await client.get("/v1/ley112021/articulos/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_1_has_required_fields(self, client):
        resp = await client.get("/v1/ley112021/articulos/1")
        data = resp.json()
        assert data["norma"] == "LEY112021"
        assert data["numero"] == "1"
        assert "texto" in data
        assert "vigente_desde" in data

    @pytest.mark.asyncio
    async def test_articulo_1_efectivo(self, client):
        resp = await client.get("/v1/ley112021/articulos/1")
        data = resp.json()
        assert "efectivo" in data["texto"].lower() or "1.000" in data["texto"]

    @pytest.mark.asyncio
    async def test_articulo_3_returns_200(self, client):
        resp = await client.get("/v1/ley112021/articulos/3")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_3_software(self, client):
        resp = await client.get("/v1/ley112021/articulos/3")
        data = resp.json()
        assert "software" in data["texto"].lower() or "informatico" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_5_returns_200(self, client):
        resp = await client.get("/v1/ley112021/articulos/5")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_5_registro(self, client):
        resp = await client.get("/v1/ley112021/articulos/5")
        data = resp.json()
        assert "registro" in data["texto"].lower() or "factura" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_18_returns_200(self, client):
        resp = await client.get("/v1/ley112021/articulos/18")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_18_sanciones(self, client):
        resp = await client.get("/v1/ley112021/articulos/18")
        data = resp.json()
        assert "sancion" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/ley112021/articulos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_articulo_with_vigente_en_filter(self, client):
        resp = await client.get("/v1/ley112021/articulos/1", params={"vigente_en": "2024-01-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "LEY112021"

    @pytest.mark.asyncio
    async def test_articulo_18_has_ley_field(self, client):
        resp = await client.get("/v1/ley112021/articulos/18")
        data = resp.json()
        assert data.get("ley") == "11/2021"

    @pytest.mark.asyncio
    async def test_articulo_18_has_source(self, client):
        resp = await client.get("/v1/ley112021/articulos/18")
        data = resp.json()
        assert data.get("fuente") == "BOE-A-2021-11382"


class TestLey112021RouterHistorial:
    """Tests para el endpoint /v1/ley112021/articulos/{numero}/historial."""

    @pytest.mark.asyncio
    async def test_historial_articulo_1_returns_200(self, client):
        resp = await client.get("/v1/ley112021/articulos/1/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_historial_has_versiones(self, client):
        resp = await client.get("/v1/ley112021/articulos/1/historial")
        data = resp.json()
        assert "historial" in data
        assert isinstance(data["historial"], list)
        assert len(data["historial"]) > 0

    @pytest.mark.asyncio
    async def test_historial_version_has_fields(self, client):
        resp = await client.get("/v1/ley112021/articulos/1/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_historial_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/ley112021/articulos/9999/historial")
        assert resp.status_code == 404


class TestLey112021RouterIntegration:
    """Tests de integracion del router con el sistema de busqueda."""

    @pytest.mark.asyncio
    async def test_search_legislacion_returns_ley112021_articles(self, client):
        from services.search import search_legislacion

        result = search_legislacion("facturas", norma="LEY112021")
        assert "resultados" in result
        assert isinstance(result["resultados"], list)

    @pytest.mark.asyncio
    async def test_search_legislacion_ley112021_efectivo(self, client):
        from services.search import search_legislacion

        result = search_legislacion("efectivo", norma="LEY112021")
        assert "resultados" in result

    @pytest.mark.asyncio
    async def test_search_legislacion_ley112021_software(self, client):
        from services.search import search_legislacion

        result = search_legislacion("software", norma="LEY112021")
        assert "resultados" in result
