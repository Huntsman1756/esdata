"""Tests para el router de LEY62018 — Ley 6/2018 de Servicios de Inversion (MiFID).

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
async def _seed_ley62018():
    """Semilla basica de articulos LEY62018 para tests del router."""
    fixtures_dir = WORKERS_DIR / "tests" / "fixtures" / "legalize_es"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixtures_dir / "ley62018.md"
    fixture.write_text(
        "# Ley 6/2018, de 3 de julio, de los servicios de inversion\n"
        "Codigo: LEY62018\n"
        "Fecha version: 2018-07-03\n"
        "\n"
        "Articulo 3.\n"
        "Servicios de inversion. A los efectos de esta ley se consideran servicios de inversion: la recepcion y transmision de ordenes, la ejecucion de ordenes, la gestion de cartera, la inversion y el deposito de instrumentos financieros.\n"
        "\n"
        "Articulo 5.\n"
        "Alcance subjetivo. Esta ley sera de aplicacion a las empresas de servicios de inversion constituidas en Espana y a las sedes de empresas de terceros paises.\n"
        "\n"
        "Articulo 7.\n"
        "Servicio de asesoramiento. El servicio de asesoramiento en inversiones consiste en proporcionar recomendaciones personalizadas al inversor sobre una o mas operaciones de inversion.\n"
        "\n"
        "Articulo 10.\n"
        "Deberes de la empresa de servicios de inversion. Las empresas de servicios de inversion actuaran con honestidad, profesionalidad y en el interes de sus clientes.\n"
        "\n"
        "Articulo 12.\n"
        "Conflictos de interes. Las empresas de servicios de inversion tendran que establecer y aplicar politica efectiva para identificar conflictos de interes y prevenirlos o gestionarlos.\n"
        "\n"
        "Articulo 15.\n"
        "Compliance. Las empresas de servicios de inversion designaran una persona responsable del cumplimiento normativo que supervisara la adecuada aplicacion de las obligaciones legales.\n"
        "\n"
        "Articulo 20.\n"
        "Organos de gobierno. Los organos de gobierno de las empresas de servicios de inversion tendran la estructura y composicion adecuadas para una gestion efectiva.\n"
        "\n"
        "Articulo 25.\n"
        "Capital inicial. Las empresas de servicios de inversion deberan disponer de un capital inicial de 125.000 euros.\n"
        "\n"
        "Articulo 30.\n"
        "Autorizacion. La creacion de una empresa de servicios de inversion requerira autorizacion previa de la Comision Nacional del Mercado de Valores.\n"
        "\n"
        "Articulo 40.\n"
        "Condiciones de acceso. El acceso a la actividad de empresa de servicios de inversion requerira el cumplimiento de condiciones de organizacion y gobierno.\n"
        "\n"
        "Articulo 50.\n"
        "Tratamiento de clientes. Las empresas de servicios de inversion deberan tratar a sus clientes con diligencia, actuando siempre en su mejor interes.\n"
        "\n"
        "Articulo 60.\n"
        "Informacion sobre servicios e instrumentos financieros. Las empresas deberan facilitar informacion clara y no enganosa sobre sus servicios.\n"
        "\n"
        "Articulo 75.\n"
        "Ejecucion de ordenes. Las empresas de servicios de inversion adoptaran todas las medidas suficientes para obtener en las operaciones para sus clientes el mejor resultado posible.\n"
        "\n"
        "Articulo 90.\n"
        "Requisitos prudenciales. Las empresas de servicios de inversion estaran sujetas a requisitos prudenciales de capital y liquidez.\n"
        "\n"
        "Articulo 100.\n"
        "Infracciones y sanciones. Las infracciones de las disposiciones de esta ley seran sancionadas conforme a la legislacion vigente.\n",
        encoding="utf-8",
    )

    from legalize_es import run_sync

    run_sync(engine, fixture_paths=[fixture])

    yield

    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEY62018'))"
            )
        )
        conn.execute(
            text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEY62018')")
        )
        conn.execute(text("DELETE FROM norma WHERE codigo = 'LEY62018'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestLey62018RouterCobertura:
    """Tests de cobertura para el endpoint /v1/ley62018/cobertura."""

    @pytest.mark.asyncio
    async def test_cobertura_returns_200(self, client):
        resp = await client.get("/v1/ley62018/cobertura")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cobertura_returns_articulo_count(self, client):
        resp = await client.get("/v1/ley62018/cobertura")
        data = resp.json()
        assert "articulos" in data
        assert data["articulos"] > 0

    @pytest.mark.asyncio
    async def test_cobertura_returns_norma_code(self, client):
        resp = await client.get("/v1/ley62018/cobertura")
        data = resp.json()
        assert data["codigo"] == "LEY62018"

    @pytest.mark.asyncio
    async def test_cobertura_returns_key_articles_count(self, client):
        resp = await client.get("/v1/ley62018/cobertura")
        data = resp.json()
        assert "articulos_clave" in data
        assert data["articulos_clave"] > 0

    @pytest.mark.asyncio
    async def test_cobertura_returns_versiones(self, client):
        resp = await client.get("/v1/ley62018/cobertura")
        data = resp.json()
        assert "versiones" in data


class TestLey62018RouterArticulosClave:
    """Tests para el endpoint /v1/ley62018/articulos-clave."""

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_200(self, client):
        resp = await client.get("/v1/ley62018/articulos-clave")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulos_clave_returns_list(self, client):
        resp = await client.get("/v1/ley62018/articulos-clave")
        data = resp.json()
        assert isinstance(data["articulos_clave"], list)
        assert len(data["articulos_clave"]) > 0

    @pytest.mark.asyncio
    async def test_articulos_clave_has_required_fields(self, client):
        resp = await client.get("/v1/ley62018/articulos-clave")
        data = resp.json()
        for articulo in data["articulos_clave"]:
            assert "numero" in articulo
            assert "descripcion" in articulo

    @pytest.mark.asyncio
    async def test_articulos_clave_includes_expected_articles(self, client):
        resp = await client.get("/v1/ley62018/articulos-clave")
        data = resp.json()
        nums = {a["numero"] for a in data["articulos_clave"]}
        assert "3" in nums
        assert "7" in nums
        assert "12" in nums
        assert "15" in nums

    @pytest.mark.asyncio
    async def test_articulos_clave_has_fuente(self, client):
        resp = await client.get("/v1/ley62018/articulos-clave")
        data = resp.json()
        for articulo in data["articulos_clave"]:
            assert articulo.get("fuente") == "LEY62018"


class TestLey62018RouterArticuloDetalle:
    """Tests para el endpoint /v1/ley62018/articulos/{numero}."""

    @pytest.mark.asyncio
    async def test_articulo_3_returns_200(self, client):
        resp = await client.get("/v1/ley62018/articulos/3")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_3_has_required_fields(self, client):
        resp = await client.get("/v1/ley62018/articulos/3")
        data = resp.json()
        assert data["norma"] == "LEY62018"
        assert data["numero"] == "3"
        assert "texto" in data
        assert "vigente_desde" in data

    @pytest.mark.asyncio
    async def test_articulo_7_returns_200(self, client):
        resp = await client.get("/v1/ley62018/articulos/7")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_7_asesoramiento(self, client):
        resp = await client.get("/v1/ley62018/articulos/7")
        data = resp.json()
        assert "asesoramiento" in data["texto"].lower() or "recomendacion" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_12_returns_200(self, client):
        resp = await client.get("/v1/ley62018/articulos/12")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_12_conflictos(self, client):
        resp = await client.get("/v1/ley62018/articulos/12")
        data = resp.json()
        assert "conflic" in data["texto"].lower() or "interes" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_15_returns_200(self, client):
        resp = await client.get("/v1/ley62018/articulos/15")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_articulo_15_compliance(self, client):
        resp = await client.get("/v1/ley62018/articulos/15")
        data = resp.json()
        assert "cumplimiento" in data["texto"].lower() or "compliance" in data["texto"].lower()

    @pytest.mark.asyncio
    async def test_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/ley62018/articulos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_articulo_with_vigente_en_filter(self, client):
        resp = await client.get("/v1/ley62018/articulos/3", params={"vigente_en": "2024-01-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "LEY62018"

    @pytest.mark.asyncio
    async def test_articulo_3_has_ley_field(self, client):
        resp = await client.get("/v1/ley62018/articulos/3")
        data = resp.json()
        assert data.get("ley") == "6/2018"

    @pytest.mark.asyncio
    async def test_articulo_3_has_source(self, client):
        resp = await client.get("/v1/ley62018/articulos/3")
        data = resp.json()
        assert data.get("fuente") == "BOE-A-2018-10582"

    @pytest.mark.asyncio
    async def test_articulo_3_is_key_article(self, client):
        resp = await client.get("/v1/ley62018/articulos/3")
        data = resp.json()
        assert data.get("clave") is True

    @pytest.mark.asyncio
    async def test_articulo_25_not_key_article(self, client):
        resp = await client.get("/v1/ley62018/articulos/25")
        data = resp.json()
        assert data.get("clave") is False


class TestLey62018RouterHistorial:
    """Tests para el endpoint /v1/ley62018/articulos/{numero}/historial."""

    @pytest.mark.asyncio
    async def test_historial_articulo_3_returns_200(self, client):
        resp = await client.get("/v1/ley62018/articulos/3/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_historial_has_versiones(self, client):
        resp = await client.get("/v1/ley62018/articulos/3/historial")
        data = resp.json()
        assert "historial" in data
        assert isinstance(data["historial"], list)
        assert len(data["historial"]) > 0

    @pytest.mark.asyncio
    async def test_historial_version_has_fields(self, client):
        resp = await client.get("/v1/ley62018/articulos/3/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_historial_articulo_no_existente_returns_404(self, client):
        resp = await client.get("/v1/ley62018/articulos/9999/historial")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_historial_returns_norma(self, client):
        resp = await client.get("/v1/ley62018/articulos/3/historial")
        data = resp.json()
        assert data["norma"] == "LEY62018"

    @pytest.mark.asyncio
    async def test_historial_returns_ley(self, client):
        resp = await client.get("/v1/ley62018/articulos/3/historial")
        data = resp.json()
        assert data["ley"] == "6/2018"
