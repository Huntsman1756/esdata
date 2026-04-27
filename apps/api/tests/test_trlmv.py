"""Tests para el router de TRLMV — RD Legislativo 4/2015 (Ley del Mercado de Valores).

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
async def _seed_trlmv():
    """Semilla basica de articulos TRLMV para tests del router."""
    fixtures_dir = WORKERS_DIR / "tests" / "fixtures" / "legalize_es"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixtures_dir / "trlmv.md"
    fixture.write_text(
        "# Texto Refundido de la Ley del Mercado de Valores\n"
        "Codigo: TRLMV\n"
        "Fecha version: 2015-07-29\n"
        "\n"
        "Articulo 50.\n"
        "Autorizacion. Podran establecerse en Espana, mediante constitucion de sociedad anonima, las sociedades de valores que se propongan realizar las actividades reguladas en esta ley.\n"
        "\n"
        "Articulo 63.\n"
        "Sociedades de valores. Las sociedades de valores seran sociedades anonimas de derecho espanol, con un capital social minimo de 73.000 euros, constituidas especificamente para realizar las actividades reguladas.\n"
        "\n"
        "Articulo 75.\n"
        "Registro de emisores. Los emisores de valores admitidos a cotizacion deberan inscribirse en el registro de emisores de valores.\n"
        "\n"
        "Articulo 100.\n"
        "Negocios con valores. Las operaciones con valores admitidos a cotizacion en mercados reglamentarios se realizaran conforme a las normas de buena fe y transparencia.\n"
        "\n"
        "Articulo 150.\n"
        "Insider trading. Queda prohibido utilizar informacion privilegiada en operaciones con valores admitidos a cotizacion.\n"
        "\n"
        "Articulo 190.\n"
        "Oferta publica de adquisicion. Las ofertas publicas de adquisicion de valores se regiran por esta ley y por el reglamento correspondiente.\n"
        "\n"
        "Articulo 215.\n"
        "Obligaciones de transparencia. Los emissores de valores admitidos a cotizacion tendran la obligacion de publier informacion periodica y circunstancial sobre su situacion financiera.\n"
        "\n"
        "Articulo 220.\n"
        "Informacion periodica. Los emissores publicaran anualmente cuentas auditadas y semestralmente cuentas condensadas.\n"
        "\n"
        "Articulo 228.\n"
        "Gobierno corporativo. Los emissores de valores admitidos a cotizacion deberan cumplir con los principios de buen gobierno corporativo establecidos en esta ley.\n"
        "\n"
        "Articulo 235.\n"
        "Consejo de administracion. Los organos de administracion de los emissores deberan contar con miembros independientes segun los criterios establecidos.\n"
        "\n"
        "Articulo 250.\n"
        "Mercados organizados. Los mercados organizados de valores se regiran por las normas de esta ley y sus disposiciones de desarrollo.\n"
        "\n"
        "Articulo 300.\n"
        "Sanciones. Las infracciones de las normas del mercado de valores seran sancionadas conforme a lo establecido en esta ley.\n"
        "\n"
        "Articulo 350.\n"
        "Comision Nacional del Mercado de Valores. La CNMV es el organo encargado de supervisar y inspeccionar el mercado de valores.\n",
        encoding="utf-8",
    )

    from legalize_es import run_sync

    run_sync(engine, fixture_paths=[fixture])

    yield

    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'TRLMV'))"
            )
        )
        conn.execute(
            text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'TRLMV')")
        )
        conn.execute(text("DELETE FROM norma WHERE codigo = 'TRLMV'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestTrlmvRouterCobertura:
    """Tests de cobertura para el endpoint /v1/trlmv/cobertura."""

    @pytest.mark.asyncio
    async def test_cobertura_returns_200(self, client):
        resp = await client.get("/v1/trlmv/cobertura")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cobertura_returns_articulo_count(self, client):
        resp = await client.get("/v1/trlmv/cobertura")
        data = resp.json()
        assert "articulos" in data
        assert data["articulos"] > 0

    @pytest.mark.asyncio
    async def test_cobertura_returns_norma_code(self, client):
        resp = await client.get("/v1/trlmv/cobertura")
        data = resp.json()
        assert data["codigo"] == "TRLMV"

    @pytest.mark.asyncio
    async def test_cobertura_returns_key_articles_count(self, client):
        resp = await client.get("/v1/trlmv/cobertura")
        data = resp.json()
        assert "articulos_clave" in data
        assert data["articulos_clave"] > 0

    @pytest.mark.asyncio
    async def test_cobertura_returns_versiones(self, client):
        resp = await client.get("/v1/trlmv/cobertura")
        data = resp.json()
        assert "versiones" in data


class TestTrlmvRouterArticulosClave:
    """Tests para el endpoint /v1/trlmv/articulos-clave."""

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_200(self, client):
        resp = await client.get("/v1/trlmv/articulos-clave")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_list(self, client):
        resp = await client.get("/v1/trlmv/articulos-clave")
        data = resp.json()
        assert isinstance(data["articulos_clave"], list)
        assert len(data["articulos_clave"]) > 0

    @pytest.mark.asyncio
    async def test_articulos_clave_has_required_fields(self, client):
        resp = await client.get("/v1/trlmv/articulos-clave")
        data = resp.json()
        for articulo in data["articulos_clave"]:
            assert "numero" in articulo
            assert "descripcion" in articulo

    @pytest.mark.asyncio
    async def test_articulos_clave_includes_expected_articles(self, client):
        resp = await client.get("/v1/trlmv/articulos-clave")
        data = resp.json()
        nums = {a["numero"] for a in data["articulos_clave"]}
        assert "50" in nums
        assert "63" in nums
        assert "215" in nums
        assert "228" in nums

    @pytest.mark.asyncio
    async def test_articulos_clave_has_fuente(self, client):
        resp = await client.get("/v1/trlmv/articulos-clave")
        data = resp.json()
        for articulo in data["articulos_clave"]:
            assert articulo.get("fuente") == "TRLMV"

    @pytest.mark.asyncio
    async def test_articulos_clave_has_vigente(self, client):
        resp = await client.get("/v1/trlmv/articulos-clave")
        data = resp.json()
        for articulo in data["articulos_clave"]:
            assert articulo.get("vigente") is True


class TestTrlmvRouterArticuloDetalle:
    """Tests para el endpoint /v1/trlmv/articulos/{numero}."""

    @pytest.mark.asyncio
    async def test_articulo_50_returns_200(self, client):
        resp = await client.get("/v1/trlmv/articulos/50")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_50_has_required_fields(self, client):
        resp = await client.get("/v1/trlmv/articulos/50")
        data = resp.json()
        assert data["norma"] == "TRLMV"
        assert data["numero"] == "50"
        assert "texto" in data
        assert "vigente_desde" in data

    @pytest.mark.asyncio
    async def test_articulo_63_returns_200(self, client):
        resp = await client.get("/v1/trlmv/articulos/63")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_63_sociedades_valores(self, client):
        resp = await client.get("/v1/trlmv/articulos/63")
        data = resp.json()
        assert "sociedades de valores" in data["texto"].lower() or "sociedades de valores" in data["titulo"].lower()

    @pytest.mark.asyncio
    async def test_articulo_215_returns_200(self, client):
        resp = await client.get("/v1/trlmv/articulos/215")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_215_transparencia(self, client):
        resp = await client.get("/v1/trlmv/articulos/215")
        data = resp.json()
        assert "transparencia" in data["texto"].lower() or "informacion" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_228_returns_200(self, client):
        resp = await client.get("/v1/trlmv/articulos/228")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_228_gobierno_corporativo(self, client):
        resp = await client.get("/v1/trlmv/articulos/228")
        data = resp.json()
        assert "gobierno corporativo" in data["texto"].lower() or "buen gobierno" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/trlmv/articulos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_articulo_with_vigente_en_filter(self, client):
        resp = await client.get("/v1/trlmv/articulos/50", params={"vigente_en": "2024-01-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "TRLMV"

    @pytest.mark.asyncio
    async def test_articulo_50_has_ley_field(self, client):
        resp = await client.get("/v1/trlmv/articulos/50")
        data = resp.json()
        assert data.get("ley") == "4/2015"

    @pytest.mark.asyncio
    async def test_articulo_50_has_source(self, client):
        resp = await client.get("/v1/trlmv/articulos/50")
        data = resp.json()
        assert data.get("fuente") == "BOE-A-2011-14568"

    @pytest.mark.asyncio
    async def test_articulo_50_is_key_article(self, client):
        resp = await client.get("/v1/trlmv/articulos/50")
        data = resp.json()
        assert data.get("clave") is True

    @pytest.mark.asyncio
    async def test_articulo_75_not_key_article(self, client):
        resp = await client.get("/v1/trlmv/articulos/75")
        data = resp.json()
        assert data.get("clave") is False


class TestTrlmvRouterHistorial:
    """Tests para el endpoint /v1/trlmv/articulos/{numero}/historial."""

    @pytest.mark.asyncio
    async def test_historial_articulo_50_returns_200(self, client):
        resp = await client.get("/v1/trlmv/articulos/50/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_historial_has_versiones(self, client):
        resp = await client.get("/v1/trlmv/articulos/50/historial")
        data = resp.json()
        assert "historial" in data
        assert isinstance(data["historial"], list)
        assert len(data["historial"]) > 0

    @pytest.mark.asyncio
    async def test_historial_version_has_fields(self, client):
        resp = await client.get("/v1/trlmv/articulos/50/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_historial_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/trlmv/articulos/9999/historial")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_historial_returns_norma(self, client):
        resp = await client.get("/v1/trlmv/articulos/50/historial")
        data = resp.json()
        assert data["norma"] == "TRLMV"

    @pytest.mark.asyncio
    async def test_historial_returns_ley(self, client):
        resp = await client.get("/v1/trlmv/articulos/50/historial")
        data = resp.json()
        assert data["ley"] == "4/2015"
