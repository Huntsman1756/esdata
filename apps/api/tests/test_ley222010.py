"""Tests para el router de Ley 22/2010 (obligaciones informativas, sanciones CNMV).

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
async def _seed_ley222010():
    """Semilla basica de articulos Ley 22/2010 para tests del router."""
    fixtures_dir = WORKERS_DIR / "tests" / "fixtures" / "legalize_es"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixtures_dir / "ley222010.md"
    fixture.write_text(
        "# Ley 22/2010, de 20 de julio, por la que se modifica el Texto Refundido de la Ley del Impuesto sobre Sociedades\n"
        "Codigo: LEY222010\n"
        "Fecha version: 2010-07-20\n"
        "\n"
        "Articulo 1.\n"
        "Modificaciones del TRLIS. Se modifican diversos articulos del Texto Refundido de la Ley del Impuesto sobre Sociedades aprobado por Real Decreto Legislativo 4/2004.\n"
        "\n"
        "Articulo 2.\n"
        "Ambito de aplicacion. Las modificaciones entraran en vigor el 1 de enero de 2011.\n"
        "\n"
        "Articulo 3.\n"
        "Sujetos pasivos. Son sujetos pasivos las personas juridicas y otros entes previstos en el articulo 35.4 del Codigo Civil.\n"
        "\n"
        "Articulo 5.\n"
        "Obligaciones informativas. Los sujetos pasivos deberan comunicar a la Agencia Estatal de Administracion Tributaria la realizacion de operaciones con entidades establecidas en paises o territorios calificados como no cooperativos.\n"
        "\n"
        "Articulo 6.\n"
        "Comunicacion de operaciones con paises sin cooperacion. La comunicacion se realizara de forma trimestral y debera incluir la identidad del beneficiario efectivo.\n"
        "\n"
        "Articulo 7.\n"
        "Listado de paises no cooperativos. A efectos de esta ley se aplicara el listado aprobado por el Consejo de la Union Europea.\n"
        "\n"
        "Articulo 10.\n"
        "Sanciones CNMV. Las infracciones en materia de obligaciones informativas y gobierno corporativo seran sancionadas por la Comision Nacional del Mercado de Valores conforme a lo establecido en la Ley 24/1988 del Mercado de Valores.\n"
        "\n"
        "Articulo 11.\n"
        "Graduacion de sanciones. Las sanciones se graduaran atendiendo a la gravedad, cuantia y duracion de la infraccion.\n"
        "\n"
        "Articulo 12.\n"
        "Sanciones leves. Constituyen infracciones leves la omision de comunicaciones informativas cuando la cuantia no supere los 3.000 euros.\n"
        "\n"
        "Articulo 13.\n"
        "Sanciones graves. Constituyen infracciones graves las comunicaciones falsas o fraudulentas sobre operaciones con paises no cooperativos.\n"
        "\n"
        "Articulo 14.\n"
        "Sanciones muy graves. Constituyen infracciones muy graves la realizacion de operaciones encubiertas con paises no cooperativos para eludir obligaciones tributarias.\n"
        "\n"
        "Articulo 15.\n"
        "Gobierno corporativo. Los organos de administracion de las sociedades cotizadas deberan velar por el cumplimiento de las obligaciones de gobierno corporativo establecidas en la normativa del mercado de valores.\n"
        "\n"
        "Articulo 16.\n"
        "Comites de auditoria. Las sociedades cotizadas deberan contar con un comite de auditoria compuesto por miembros independientes.\n"
        "\n"
        "Articulo 18.\n"
        "Precios de transferencia. Los contribuyentes que realicen operaciones con partes vinculadas deberan documentar los criterios de valoracion aplicados.\n"
        "\n"
        "Articulo 20.\n"
        "Intercambio de informacion en la Union Europea. Las autoridades espanolas colaboraran con las autoridades tributarias de los Estados miembros conforme al Reglamento (UE) 2017/358.\n"
        "\n"
        "Articulo 25.\n"
        "Obligaciones sobre operaciones vinculadas. Se establecen obligaciones de informacion sobre operaciones con partes vinculadas en el extranjero.\n"
        "\n"
        "Articulo 30.\n"
        "Disposicion adicional. Se autoriza al Gobierno para aprobar las normas de desarrollo de esta ley.\n"
        "\n",
        encoding="utf-8",
    )

    from legalize_es import run_sync

    run_sync(engine, fixture_paths=[fixture])

    yield

    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEY222010'))"
            )
        )
        conn.execute(
            text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEY222010')")
        )
        conn.execute(text("DELETE FROM norma WHERE codigo = 'LEY222010'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestLey222010RouterCobertura:
    """Tests de cobertura para el endpoint /v1/ley222010/cobertura."""

    @pytest.mark.asyncio
    async def test_cobertura_returns_200(self, client):
        resp = await client.get("/v1/ley222010/cobertura")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cobertura_returns_articulo_count(self, client):
        resp = await client.get("/v1/ley222010/cobertura")
        data = resp.json()
        assert "articulos" in data
        assert data["articulos"] > 0

    @pytest.mark.asyncio
    async def test_cobertura_returns_norma_code(self, client):
        resp = await client.get("/v1/ley222010/cobertura")
        data = resp.json()
        assert data["codigo"] == "LEY222010"

    @pytest.mark.asyncio
    async def test_cobertura_returns_key_articles_count(self, client):
        resp = await client.get("/v1/ley222010/cobertura")
        data = resp.json()
        assert "articulos_clave" in data
        assert data["articulos_clave"] > 0

    @pytest.mark.asyncio
    async def test_cobertura_returns_versiones(self, client):
        resp = await client.get("/v1/ley222010/cobertura")
        data = resp.json()
        assert "versiones" in data


class TestLey222010RouterArticulosClave:
    """Tests para el endpoint /v1/ley222010/articulos-clave."""

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_200(self, client):
        resp = await client.get("/v1/ley222010/articulos-clave")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_list(self, client):
        resp = await client.get("/v1/ley222010/articulos-clave")
        data = resp.json()
        assert isinstance(data["articulos_clave"], list)
        assert len(data["articulos_clave"]) > 0

    @pytest.mark.asyncio
    async def test_articulos_clave_has_required_fields(self, client):
        resp = await client.get("/v1/ley222010/articulos-clave")
        data = resp.json()
        for articulo in data["articulos_clave"]:
            assert "numero" in articulo
            assert "descripcion" in articulo

    @pytest.mark.asyncio
    async def test_articulos_clave_includes_expected_articles(self, client):
        resp = await client.get("/v1/ley222010/articulos-clave")
        data = resp.json()
        nums = {a["numero"] for a in data["articulos_clave"]}
        assert "5" in nums
        assert "10" in nums
        assert "15" in nums

    @pytest.mark.asyncio
    async def test_articulos_clave_norma_field(self, client):
        resp = await client.get("/v1/ley222010/articulos-clave")
        data = resp.json()
        assert data["norma"] == "LEY222010"


class TestLey222010RouterArticuloDetalle:
    """Tests para el endpoint /v1/ley222010/articulos/{numero}."""

    @pytest.mark.asyncio
    async def test_articulo_1_returns_200(self, client):
        resp = await client.get("/v1/ley222010/articulos/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_1_has_required_fields(self, client):
        resp = await client.get("/v1/ley222010/articulos/1")
        data = resp.json()
        assert data["norma"] == "LEY222010"
        assert data["numero"] == "1"
        assert "texto" in data
        assert "vigente_desde" in data

    @pytest.mark.asyncio
    async def test_articulo_5_obligaciones_informativas(self, client):
        resp = await client.get("/v1/ley222010/articulos/5")
        data = resp.json()
        assert "informativa" in data["texto"].lower() or "comunicacion" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_5_has_key_flag(self, client):
        resp = await client.get("/v1/ley222010/articulos/5")
        data = resp.json()
        assert data["clave"] is True

    @pytest.mark.asyncio
    async def test_articulo_10_sanciones_cnmv(self, client):
        resp = await client.get("/v1/ley222010/articulos/10")
        data = resp.json()
        assert "sancion" in data["texto"].lower() or "cnmv" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/ley222010/articulos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_articulo_with_vigente_en_filter(self, client):
        resp = await client.get("/v1/ley222010/articulos/1", params={"vigente_en": "2024-01-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "LEY222010"

    @pytest.mark.asyncio
    async def test_articulo_15_has_ley_field(self, client):
        resp = await client.get("/v1/ley222010/articulos/15")
        data = resp.json()
        assert data.get("ley") == "22/2010"

    @pytest.mark.asyncio
    async def test_articulo_15_has_source(self, client):
        resp = await client.get("/v1/ley222010/articulos/15")
        data = resp.json()
        assert data.get("fuente") == "BOE-A-2010-16380"

    @pytest.mark.asyncio
    async def test_articulo_25_has_text(self, client):
        resp = await client.get("/v1/ley222010/articulos/25")
        data = resp.json()
        assert "texto" in data
        assert len(data["texto"]) > 0


class TestLey222010RouterHistorial:
    """Tests para el endpoint /v1/ley222010/articulos/{numero}/historial."""

    @pytest.mark.asyncio
    async def test_historial_articulo_1_returns_200(self, client):
        resp = await client.get("/v1/ley222010/articulos/1/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_historial_has_versiones(self, client):
        resp = await client.get("/v1/ley222010/articulos/1/historial")
        data = resp.json()
        assert "historial" in data
        assert isinstance(data["historial"], list)
        assert len(data["historial"]) > 0

    @pytest.mark.asyncio
    async def test_historial_version_has_fields(self, client):
        resp = await client.get("/v1/ley222010/articulos/1/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_historial_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/ley222010/articulos/9999/historial")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_historial_norma_field(self, client):
        resp = await client.get("/v1/ley222010/articulos/1/historial")
        data = resp.json()
        assert data["norma"] == "LEY222010"
