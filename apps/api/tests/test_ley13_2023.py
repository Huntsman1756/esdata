"""Tests para el router de Ley 13/2023 de regulacion de la IA.

Cubre: lista de normas, detalle de norma, articulos, detalle de articulo
e historial de versiones.

El seed de datos vive en conftest.py (LEY13_2023 con articulo 5).
"""

import sys
from pathlib import Path

# 1) Inyectar ruta de api antes de cualquier import
API_DIR = str(Path(__file__).resolve().parents[1])
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

# 2) Importar conftest primero (configura DATABASE_URL, crea engine SQLite, patchea db)
import conftest as _conftest  # noqa: E402

# 3) Ahora si importar main y el resto
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from main import app  # noqa: E402
from sqlalchemy import text  # noqa: E402

# 4) Patch router modules that did 'from db import db_session' (after main imports them)
import routers.ley13_2023 as _ley13_mod  # noqa: E402
_ley13_mod.db_session = _conftest._db_module.db_session


@pytest_asyncio.fixture
async def client(_seed_ley13_2023):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
def ley13_articulo_id():
    """Returns the articulo_id for articulo 5 of LEY13_2023."""
    with _conftest.engine.connect() as conn:
        row = conn.execute(text(
            "SELECT a.id FROM articulo a JOIN norma n ON n.id = a.norma_id WHERE n.codigo = 'LEY13_2023' AND a.numero = '5' ORDER BY a.id ASC LIMIT 1"
        )).first()
        return row[0] if row else None


# ====================================================================
# Test: GET /v1/ley13-2023 (lista normas)
# ====================================================================

class TestLey13ListaNormas:
    @pytest.mark.asyncio
    async def test_ley13_lista_status_200(self, client):
        resp = await client.get("/v1/ley13-2023")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ley13_lista_response_contiene_normas(self, client):
        resp = await client.get("/v1/ley13-2023")
        data = resp.json()
        assert "normas" in data
        assert isinstance(data["normas"], list)

    @pytest.mark.asyncio
    async def test_ley13_lista_norma_presente(self, client):
        resp = await client.get("/v1/ley13-2023")
        data = resp.json()
        codigos = [n["codigo"] for n in data["normas"]]
        assert "LEY13_2023" in codigos


# ====================================================================
# Test: GET /v1/ley13-2023/{codigo} (detalle norma)
# ====================================================================

class TestLey13DetalleNorma:
    @pytest.mark.asyncio
    async def test_ley13_norma_detalle_status_200(self, client):
        resp = await client.get("/v1/ley13-2023/LEY13_2023")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ley13_norma_detalle_codigo(self, client):
        resp = await client.get("/v1/ley13-2023/LEY13_2023")
        data = resp.json()
        assert data["codigo"] == "LEY13_2023"

    @pytest.mark.asyncio
    async def test_ley13_norma_detalle_titulo(self, client):
        resp = await client.get("/v1/ley13-2023/LEY13_2023")
        data = resp.json()
        assert "regulacion de la inteligencia artificial" in data["titulo"]

    @pytest.mark.asyncio
    async def test_ley13_norma_detalle_boe_id(self, client):
        resp = await client.get("/v1/ley13-2023/LEY13_2023")
        data = resp.json()
        assert data["boe_id"] == "BOE-A-2023-23080"

    @pytest.mark.asyncio
    async def test_ley13_norma_detalle_404(self, client):
        resp = await client.get("/v1/ley13-2023/ZZZZZZZ")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/ley13-2023/articulos (lista articulos)
# ====================================================================

class TestLey13ListaArticulos:
    @pytest.mark.asyncio
    async def test_ley13_articulos_status_200(self, client):
        resp = await client.get("/v1/ley13-2023/articulos")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ley13_articulos_response_model(self, client):
        resp = await client.get("/v1/ley13-2023/articulos")
        data = resp.json()
        assert "norma" in data
        assert "articulos" in data
        assert data["norma"] == "LEY13_2023"

    @pytest.mark.asyncio
    async def test_ley13_articulos_contiene_articulo_5(self, client, ley13_articulo_id):
        """El seed de conftest.py inserta articulo 5."""
        assert ley13_articulo_id is not None
        resp = await client.get("/v1/ley13-2023/articulos")
        data = resp.json()
        articulo_nums = [a["numero"] for a in data["articulos"]]
        assert "5" in articulo_nums

    @pytest.mark.asyncio
    async def test_ley13_articulos_campo_numero(self, client):
        resp = await client.get("/v1/ley13-2023/articulos")
        for a in resp.json()["articulos"]:
            assert "numero" in a
            assert "titulo" in a
            assert "tipo" in a

    @pytest.mark.asyncio
    async def test_ley13_articulos_filtro_tipo(self, client):
        resp = await client.get("/v1/ley13-2023/articulos", params={"tipo": "articulo"})
        data = resp.json()
        for a in data["articulos"]:
            assert a["tipo"] == "articulo"


# ====================================================================
# Test: GET /v1/ley13-2023/articulos/{articulo_id} (detalle articulo)
# ====================================================================

class TestLey13DetalleArticulo:
    @pytest.mark.asyncio
    async def test_ley13_articulo_detalle_status_200(self, client, ley13_articulo_id):
        assert ley13_articulo_id is not None
        resp = await client.get(f"/v1/ley13-2023/articulos/{ley13_articulo_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ley13_articulo_detalle_campos(self, client, ley13_articulo_id):
        assert ley13_articulo_id is not None
        resp = await client.get(f"/v1/ley13-2023/articulos/{ley13_articulo_id}")
        data = resp.json()
        assert "articulo_id" in data
        assert "numero" in data
        assert "texto" in data
        assert "vigente_desde" in data

    @pytest.mark.asyncio
    async def test_ley13_articulo_detalle_404(self, client):
        resp = await client.get("/v1/ley13-2023/articulos/99999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/ley13-2023/articulos/{articulo_id}/historial
# ====================================================================

class TestLey13HistorialArticulo:
    @pytest.mark.asyncio
    async def test_ley13_historial_status_200(self, client, ley13_articulo_id):
        assert ley13_articulo_id is not None
        resp = await client.get(f"/v1/ley13-2023/articulos/{ley13_articulo_id}/historial")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ley13_historial_response_model(self, client, ley13_articulo_id):
        assert ley13_articulo_id is not None
        resp = await client.get(f"/v1/ley13-2023/articulos/{ley13_articulo_id}/historial")
        data = resp.json()
        assert "articulos" in data
        assert isinstance(data["articulos"], list)

    @pytest.mark.asyncio
    async def test_ley13_historial_version_campos(self, client, ley13_articulo_id):
        assert ley13_articulo_id is not None
        resp = await client.get(f"/v1/ley13-2023/articulos/{ley13_articulo_id}/historial")
        data = resp.json()
        for version in data["articulos"]:
            assert "numero" in version
            assert "vigente_desde" in version

    @pytest.mark.asyncio
    async def test_ley13_historial_404(self, client):
        resp = await client.get("/v1/ley13-2023/articulos/99999/historial")
        assert resp.status_code == 404
