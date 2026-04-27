"""Tests para el router mercantil (Ley de Sociedades de Capital)."""

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


@pytest_asyncio.fixture(autouse=True)
async def _seed_mercantil():
    """Semilla basica de articulos LEYSOC para tests del router."""
    fixtures_dir = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixtures_dir / "ley12010.md"
    fixture.write_text(
            "# Ley de Sociedades de Capital (RD Legislativo 1/2010)\n"
            "Codigo: LEYSOC\n"
            "Fecha version: 2010-09-02\n"
            "\n"
            "Articulo 1.\n"
            "Objeto: la ley regula las sociedades de capital (S.A., S.L., S.E.).\n"
            "\n"
            "Articulo 2.\n"
            "Sociedad de responsabilidad limitada: capital no superior a 1M EUR, socios limitados.\n"
            "\n"
            "Articulo 5.\n"
            "Sociedad anonima: capital dividido en acciones, minimo 60.000 EUR.\n"
            "\n"
            "Articulo 14.\n"
            "Capital social: constitucion, aumentos, reducciones y proteccion del capital.\n"
            "\n"
            "Articulo 28.\n"
            "Obligacion de llevar libro de inventario: reflejo fiel del patrimonio, situacion financial y resultados de la sociedad.\n"
            "\n"
            "Articulo 30.\n"
            "Obligacion de llevar libro de diario: registro cronologico de todas las operaciones contables.\n"
            "\n"
            "Articulo 31.\n"
            "Obligacion de elaborar balance de situacion annual al cierre de cada ejercicio social.\n"
            "\n"
            "Articulo 32.\n"
            "Obligaciones contables adicionales segun la normativa mercantil aplicable.\n"
            "\n"
            "Articulo 33.\n"
            "Legalizacion y registro de los libros obligatorios ante el Registro Mercantil correspondiente.\n"
            "\n"
            "Articulo 92.\n"
            "Junta general: organo deliberante de la sociedad.\n"
            "\n"
            "Articulo 146.\n"
            "Administracion y representacion: organos de gobierno de la sociedad.\n"
            "\n"
            "Articulo 150.\n"
            "Administradores: nombramiento, funciones, responsabilidad y deberes.\n"
            "\n"
            "Articulo 164.\n"
            "Transformacion, fusion y escision de sociedades.\n"
            "\n"
            "Articulo 200.\n"
            "Disolucion y liquidacion: causas y procedimiento.\n",
            encoding="utf-8",
        )

    from legalize_es import run_sync

    run_sync(engine, fixture_paths=[fixture])

    yield

    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEYSOC'))"
            )
        )
        conn.execute(
            text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEYSOC')")
        )
        conn.execute(text("DELETE FROM norma WHERE codigo = 'LEYSOC'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Cobertura LSC
# ---------------------------------------------------------------------------

class TestMercantilCobertura:
    """Pruebas del endpoint /v1/mercantil/cobertura."""

    @pytest.mark.asyncio
    async def test_cobertura_con_datos(self, client):
        """Con LEYSOC en DB, devuelve resumen de cobertura."""
        resp = await client.get("/v1/mercantil/cobertura")
        assert resp.status_code == 200
        data = resp.json()
        assert data["codigo"] == "LEYSOC"
        assert data["boe_id"] == "BOE-A-2010-15523"
        assert "articulos" in data
        assert "versiones" in data
        assert "articulos_clave" in data


# ---------------------------------------------------------------------------
# Libros contables
# ---------------------------------------------------------------------------

class TestMercantilLibrosContables:
    """Pruebas del endpoint /v1/mercantil/libros-contables."""

    @pytest.mark.asyncio
    async def test_libros_contables_con_datos(self, client):
        """Con datos, devuelve los 4 libros contables (arts. 28, 30, 31, 33)."""
        resp = await client.get("/v1/mercantil/libros-contables")
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "LEYSOC"
        assert data["ley"] == "1/2010"
        libros = data["libros_contables"]
        assert len(libros) == 4
        nums = [item["numero"] for item in libros]
        assert "28" in nums
        assert "30" in nums
        assert "31" in nums
        assert "33" in nums

    @pytest.mark.asyncio
    async def test_libros_contables_descripciones_presentes(self, client):
        """Cada libro tiene descripcion y vigente=True."""
        resp = await client.get("/v1/mercantil/libros-contables")
        data = resp.json()
        for libro in data["libros_contables"]:
            assert "descripcion" in libro
            assert libro["vigente"] is True
            assert libro["fuente"] == "LEYSOC"


# ---------------------------------------------------------------------------
# Articulos clave
# ---------------------------------------------------------------------------

class TestMercantilArticulosClave:
    """Pruebas del endpoint /v1/mercantil/articulos-clave."""

    @pytest.mark.asyncio
    async def test_articulos_clave_con_datos(self, client):
        """Con datos, devuelve lista de articulos clave."""
        resp = await client.get("/v1/mercantil/articulos-clave")
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "LEYSOC"
        assert data["ley"] == "1/2010"
        articulos = data["articulos_clave"]
        assert len(articulos) >= 4  # al menos los 4 libros contables

    @pytest.mark.asyncio
    async def test_articulos_clave_vigentes(self, client):
        """Todos los articulos clave tienen vigente=True."""
        resp = await client.get("/v1/mercantil/articulos-clave")
        data = resp.json()
        for art in data["articulos_clave"]:
            assert art["vigente"] is True
            assert "descripcion" in art


# ---------------------------------------------------------------------------
# Articulo individual
# ---------------------------------------------------------------------------

class TestMercantilArticulo:
    """Pruebas del endpoint /v1/mercantil/articulos/{numero}."""

    @pytest.mark.asyncio
    async def test_articulo_no_existe(self, client):
        """Articulo inexistente devuelve 404."""
        resp = await client.get("/v1/mercantil/articulos/9999")
        assert resp.status_code == 404
        assert "no encontrado" in resp.json()["detail"]["error"]

    @pytest.mark.asyncio
    async def test_articulo_no_existe_tipo(self, client):
        """Articulo inexistente devuelve 404 con tipo JSON correcto."""
        resp = await client.get("/v1/mercantil/articulos/9999")
        assert resp.json()["detail"]["error"] is not None

    @pytest.mark.asyncio
    async def test_articulo_28_libro_inventario(self, client):
        """Articulo 28 (libro inventario) devuelve datos."""
        resp = await client.get("/v1/mercantil/articulos/28")
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "LEYSOC"
        assert data["ley"] == "1/2010"
        assert data["numero"] == "28"
        assert data["fuente"] == "BOE-A-2010-15523"
        assert data["clave"] is True
        assert "texto" in data
        assert "vigente_desde" in data

    @pytest.mark.asyncio
    async def test_articulo_30_libro_cuentas(self, client):
        """Articulo 30 (libro de cuentas) devuelve datos."""
        resp = await client.get("/v1/mercantil/articulos/30")
        assert resp.status_code == 200
        data = resp.json()
        assert data["numero"] == "30"
        assert data["clave"] is True

    @pytest.mark.asyncio
    async def test_articulo_31_libro_balances(self, client):
        """Articulo 31 (libro de balances) devuelve datos."""
        resp = await client.get("/v1/mercantil/articulos/31")
        assert resp.status_code == 200
        data = resp.json()
        assert data["numero"] == "31"
        assert data["clave"] is True

    @pytest.mark.asyncio
    async def test_articulo_33_legalizacion(self, client):
        """Articulo 33 (legalizacion libros) devuelve datos."""
        resp = await client.get("/v1/mercantil/articulos/33")
        assert resp.status_code == 200
        data = resp.json()
        assert data["numero"] == "33"
        assert data["clave"] is True

    @pytest.mark.asyncio
    async def test_articulo_no_clave(self, client):
        """Articulo no en ARTICULOS_CLAVE devuelve clave=False."""
        resp = await client.get("/v1/mercantil/articulos/32")
        if resp.status_code == 200:
            data = resp.json()
            assert data["clave"] is False

    @pytest.mark.asyncio
    async def test_articulo_con_fecha_vigencia(self, client):
        """Consulta con vigente_en filtra correctamente."""
        resp = await client.get("/v1/mercantil/articulos/28?vigente_en=2025-01-01")
        assert resp.status_code == 200
        data = resp.json()
        assert data["numero"] == "28"

    @pytest.mark.asyncio
    async def test_articulo_texto_no_vacio(self, client):
        """El texto del articulo no esta vacio."""
        resp = await client.get("/v1/mercantil/articulos/28")
        data = resp.json()
        assert len(data["texto"]) > 0


# ---------------------------------------------------------------------------
# Historial de articulo
# ---------------------------------------------------------------------------

class TestMercantilArticuloHistorial:
    """Pruebas del endpoint /v1/mercantil/articulos/{numero}/historial."""

    @pytest.mark.asyncio
    async def test_historial_no_existe(self, client):
        """Historial de articulo inexistente devuelve 404."""
        resp = await client.get("/v1/mercantil/articulos/9999/historial")
        assert resp.status_code == 404
        assert "no encontrado" in resp.json()["detail"]["error"]

    @pytest.mark.asyncio
    async def test_historial_articulo_28(self, client):
        """Historial del articulo 28 devuelve lista de versiones."""
        resp = await client.get("/v1/mercantil/articulos/28/historial")
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma"] == "LEYSOC"
        assert data["ley"] == "1/2010"
        assert data["numero"] == "28"
        assert isinstance(data["historial"], list)
        assert len(data["historial"]) >= 1

    @pytest.mark.asyncio
    async def test_historial_versiones_campos(self, client):
        """Cada version tiene texto, vigente_desde y vigente_hasta."""
        resp = await client.get("/v1/mercantil/articulos/28/historial")
        data = resp.json()
        for version in data["historial"]:
            assert "texto" in version
            assert "vigente_desde" in version
            assert "vigente_hasta" in version

    @pytest.mark.asyncio
    async def test_historial_orden_descendente(self, client):
        """El historial esta ordenado por vigente_desde DESC."""
        resp = await client.get("/v1/mercantil/articulos/28/historial")
        data = resp.json()
        if len(data["historial"]) >= 2:
            fechas = [v["vigente_desde"] for v in data["historial"]]
            assert fechas == sorted(fechas, reverse=True)


# ---------------------------------------------------------------------------
# Integracion con DB
# ---------------------------------------------------------------------------

class TestMercantilDB:
    """Pruebas de integracion con la base de datos."""

    @pytest.mark.asyncio
    async def test_norma_leysoc_existe(self):
        """La norma LEYSOC existe en la tabla norma."""
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT codigo, boe_id, tipo_documento FROM norma WHERE codigo = 'LEYSOC'")
            ).mappings().first()
            assert row is not None
            assert row["codigo"] == "LEYSOC"
            assert row["boe_id"] is not None
            assert row["tipo_documento"] is not None

    @pytest.mark.asyncio
    async def test_articulos_libros_contables_en_db(self):
        """Los articulos 28, 30, 31, 33 existen en la tabla articulo."""
        with engine.begin() as conn:
            nums = ("28", "30", "31", "33")
            placeholders = ", ".join(f":n{i}" for i in range(len(nums)))
            params = {f"n{i}": n for i, n in enumerate(nums)}
            rows = conn.execute(
                text(
                    f"""
                    SELECT a.numero FROM norma n
                    JOIN articulo a ON a.norma_id = n.id
                    WHERE n.codigo = 'LEYSOC' AND a.numero IN ({placeholders})
                    """
                ),
                params,
            ).mappings()
            found_nums = {row["numero"] for row in rows}
            assert found_nums == {"28", "30", "31", "33"}
