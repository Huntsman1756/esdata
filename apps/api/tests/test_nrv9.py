"""Tests para el router de NRV 9ª PGC (instrumentos financieros).

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
async def _seed_nrv9():
    """Semilla basica de articulos NRV9 para tests del router."""
    fixtures_dir = WORKERS_DIR / "tests" / "fixtures" / "legalize_es"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixtures_dir / "nrv9.md"
    fixture.write_text(
        "# Norma de Registro y Valoracion 9ª del Plan General de Contabilidad (instrumentos financieros)\n"
        "Codigo: NRV9\n"
        "Fecha version: 2008-10-02\n"
        "\n"
        "Articulo 1.\n"
        "Alcance. Esta norma de registro y valoracion se aplica a todos los instrumentos financieros tal y como se definen en el plan general de contabilidad.\n"
        "\n"
        "Articulo 2.\n"
        "Definiciones. A efectos de esta norma se entiende por instrumento financiero todo activo que genere un activo financiero y un pasivo financiero o instrumento de patrimonio.\n"
        "\n"
        "Articulo 3.\n"
        "Clasificacion inicial. Las entidades clasificaran sus instrumentos financieros en las categorias previstas en esta norma al momento del reconocimiento inicial.\n"
        "\n"
        "Articulo 4.\n"
        "Inversiones mantenidas hasta vencimiento. Se clasificaran como inversiones mantenidas hasta vencimiento aquellos activos financieros no derivados con pagos fijos o determinables.\n"
        "\n"
        "Articulo 5.\n"
        "Reclasificacion. Un instrumento financiero podra ser reclasificado unicamente cuando la entidad modifica su modelo de negocio para gestionar dicho instrumento.\n"
        "\n"
        "Articulo 6.\n"
        "Valor razonable. Los instrumentos financieros se valoraran inicialmente a su valor razonable que sera el precio de la transaccion mas los costes directamente atribuibles.\n"
        "\n"
        "Articulo 7.\n"
        "Deterioro de valor. La entidad reconocera una perdida por deterioro cuando exista evidencia objetiva de que el valor recuperable es inferior al valor en libros.\n"
        "\n"
        "Articulo 8.\n"
        "Coberturas. La contabilidad de coberturas permitira reflejar el efecto de la gestion de riesgos mediante instrumentos financieros derivados.\n"
        "\n"
        "Articulo 9.\n"
        "Desreconocimiento. Un instrumento financiero se dara de baja cuando se extingan los derechos contractuales sobre los flujos de caja o la entidad transfiera el activo.\n"
        "\n"
        "Articulo 10.\n"
        "Informacion a revelar. Las entidades revelaran informacion sobre la clasificacion, valoracion, deterioro y estrategias de cobertura de sus instrumentos financieros.\n",
        encoding="utf-8",
    )

    from legalize_es import run_sync

    run_sync(engine, fixture_paths=[fixture])

    yield

    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'NRV9'))"
            )
        )
        conn.execute(
            text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'NRV9')")
        )
        conn.execute(text("DELETE FROM norma WHERE codigo = 'NRV9'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestNrv9Cobertura:
    """Tests de cobertura para el endpoint /v1/pgc/nrv/9/cobertura."""

    @pytest.mark.asyncio
    async def test_cobertura_returns_200(self, client):
        resp = await client.get("/v1/pgc/nrv/9/cobertura")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cobertura_returns_articulo_count(self, client):
        resp = await client.get("/v1/pgc/nrv/9/cobertura")
        data = resp.json()
        assert "articulos" in data
        assert data["articulos"] > 0

    @pytest.mark.asyncio
    async def test_cobertura_returns_norma_code(self, client):
        resp = await client.get("/v1/pgc/nrv/9/cobertura")
        data = resp.json()
        assert data["codigo"] == "NRV9"

    @pytest.mark.asyncio
    async def test_cobertura_returns_key_articles_count(self, client):
        resp = await client.get("/v1/pgc/nrv/9/cobertura")
        data = resp.json()
        assert "articulos_clave" in data
        assert data["articulos_clave"] > 0


class TestNrv9ArticulosClave:
    """Tests para el endpoint /v1/pgc/nrv/9/articulos-clave."""

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_200(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos-clave")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_list(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos-clave")
        data = resp.json()
        assert isinstance(data["articulos_clave"], list)
        assert len(data["articulos_clave"]) > 0

    @pytest.mark.asyncio
    async def test_articulos_clave_has_required_fields(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos-clave")
        data = resp.json()
        for articulo in data["articulos_clave"]:
            assert "numero" in articulo
            assert "descripcion" in articulo

    @pytest.mark.asyncio
    async def test_articulos_clave_includes_expected_articles(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos-clave")
        data = resp.json()
        nums = {a["numero"] for a in data["articulos_clave"]}
        assert "1" in nums
        assert "6" in nums
        assert "10" in nums


class TestNrv9ArticuloDetalle:
    """Tests para el endpoint /v1/pgc/nrv/9/articulos/{numero}."""

    @pytest.mark.asyncio
    async def test_articulo_1_returns_200(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_1_has_required_fields(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/1")
        data = resp.json()
        assert data["norma"] == "NRV9"
        assert data["numero"] == "1"
        assert "texto" in data
        assert "vigente_desde" in data

    @pytest.mark.asyncio
    async def test_articulo_6_valor_razonable(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/6")
        assert resp.status_code == 200
        data = resp.json()
        assert "razon" in data["texto"].lower() or "valor" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_7_deterioro(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/7")
        assert resp.status_code == 200
        data = resp.json()
        assert "deterioro" in data["texto"].lower() or "perdida" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_8_coberturas(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/8")
        assert resp.status_code == 200
        data = resp.json()
        assert "cobertur" in data["texto"].lower() or "deriva" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_articulo_with_vigente_en_filter(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/1", params={"vigente_en": "2024-01-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "NRV9"

    @pytest.mark.asyncio
    async def test_articulo_10_has_source(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/10")
        data = resp.json()
        assert data.get("fuente") == "BOE-A-2008-10273"

    @pytest.mark.asyncio
    async def test_articulo_1_has_norma_completa(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/1")
        data = resp.json()
        assert data.get("norma_completa") == "NRV 9ª PGC"


class TestNrv9Historial:
    """Tests para el endpoint /v1/pgc/nrv/9/articulos/{numero}/historial."""

    @pytest.mark.asyncio
    async def test_historial_articulo_1_returns_200(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/1/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_historial_has_versiones(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/1/historial")
        data = resp.json()
        assert "historial" in data
        assert isinstance(data["historial"], list)
        assert len(data["historial"]) > 0

    @pytest.mark.asyncio
    async def test_historial_version_has_fields(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/1/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_historial_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/pgc/nrv/9/articulos/9999/historial")
        assert resp.status_code == 404
