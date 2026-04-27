import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def linea_id(client):
    """Return the ID of the first seed linea_criterio."""
    r = await client.get("/v1/criterio", params={"limit": 100})
    data = r.json()
    assert data["total"] >= 7
    return data["lineas"][0]["id"]


@pytest_asyncio.fixture
async def linea_id_2(client):
    """Return the ID of the second seed linea_criterio."""
    r = await client.get("/v1/criterio", params={"limit": 100})
    data = r.json()
    assert data["total"] >= 7
    lineas = data["lineas"]
    return lineas[1]["id"]


# ---------------------------------------------------------------------------
# Listar lineas de criterio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_listar_criterio_returns_200(client):
    r = await client.get("/v1/criterio")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_listar_criterio_returns_seed_data(client):
    r = await client.get("/v1/criterio")
    data = r.json()
    assert data["total"] >= 7
    assert len(data["lineas"]) >= 7


@pytest.mark.asyncio
async def test_listar_criterio_pagination(client):
    r = await client.get("/v1/criterio", params={"limit": 2, "offset": 0})
    data = r.json()
    assert data["total"] >= 7
    assert len(data["lineas"]) == 2


@pytest.mark.asyncio
async def test_listar_criterio_pagination_offset(client):
    r = await client.get("/v1/criterio", params={"limit": 2, "offset": 2})
    data = r.json()
    assert len(data["lineas"]) == 2
    assert data["total"] >= 7


@pytest.mark.asyncio
async def test_listar_criterio_filters_by_estado(client):
    r = await client.get("/v1/criterio", params={"estado": "vigente"})
    data = r.json()
    assert r.status_code == 200
    assert data["total"] >= 7
    for linea in data["lineas"]:
        assert linea["estado"] == "vigente"


@pytest.mark.asyncio
async def test_listar_criterio_filters_by_activo(client):
    r = await client.get("/v1/criterio", params={"activo": "true"})
    data = r.json()
    assert r.status_code == 200
    assert data["total"] >= 7
    for linea in data["lineas"]:
        assert linea["activo"] is True


@pytest.mark.asyncio
async def test_listar_criterio_search_by_titulo(client):
    r = await client.get("/v1/criterio", params={"q": "IVA"})
    data = r.json()
    assert r.status_code == 200
    assert data["total"] >= 1
    found = [l for l in data["lineas"] if "iva" in l["titulo"].lower()]
    assert len(found) >= 1


@pytest.mark.asyncio
async def test_listar_criterio_search_by_cuestion(client):
    r = await client.get("/v1/criterio", params={"q": "comisiones"})
    data = r.json()
    assert r.status_code == 200
    assert data["total"] >= 1
    found = [l for l in data["lineas"] if "comision" in l["cuestion_practica"].lower()]
    assert len(found) >= 1


# ---------------------------------------------------------------------------
# Obtener detalle de linea de criterio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_obtener_detalle_linea(client, linea_id):
    r = await client.get(f"/v1/criterio/{linea_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == linea_id
    assert "titulo" in data
    assert "cuestion_practica" in data
    assert "referencias" in data


@pytest.mark.asyncio
async def test_obtener_detalle_linea_404(client):
    r = await client.get("/v1/criterio/999999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Crear nueva linea de criterio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crear_linea_criterio(client):
    r = await client.post("/v1/criterio", json={
        "titulo": "Linea de prueba",
        "cuestion_practica": "Es esto correcto?",
        "descripcion": "Descripcion de prueba",
        "estado": "borrador",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["titulo"] == "Linea de prueba"
    assert data["estado"] == "borrador"
    assert data["activo"] is True


@pytest.mark.asyncio
async def test_crear_linea_criterio_sin_titulo(client):
    r = await client.post("/v1/criterio", json={
        "cuestion_practica": "Es esto correcto?",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_crear_linea_criterio_sin_cuestion(client):
    r = await client.post("/v1/criterio", json={
        "titulo": "Linea sin cuestion",
    })
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Actualizar linea de criterio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_actualizar_linea_criterio(client, linea_id):
    r = await client.patch(f"/v1/criterio/{linea_id}", json={
        "titulo": "Titulo actualizado",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["titulo"] == "Titulo actualizado"


@pytest.mark.asyncio
async def test_actualizar_linea_criterio_estado(client, linea_id):
    r = await client.patch(f"/v1/criterio/{linea_id}", json={
        "estado": "archivado",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["estado"] == "archivado"


@pytest.mark.asyncio
async def test_actualizar_linea_criterio_404(client):
    r = await client.patch("/v1/criterio/999999", json={
        "titulo": "No existe",
    })
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Gestion de referencias
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agregar_referencia(client, linea_id_2):
    r = await client.post(f"/v1/criterio/{linea_id_2}/referencias", json={
        "documento_referencia": "STS-TEST/2025",
        "tipo_documento": "sentencia",
        "organismo_emisor": "Tribunal Supremo",
        "fecha": "2025-01-15",
        "rol_en_linea": "doctrina_principal",
        "orden": 1,
    })
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "created"


@pytest.mark.asyncio
async def test_listar_referencias(client, linea_id_2):
    # First create a new reference
    r = await client.post(f"/v1/criterio/{linea_id_2}/referencias", json={
        "documento_referencia": "STS-TEST2/2025",
        "tipo_documento": "sentencia",
        "organismo_emisor": "Tribunal Supremo",
        "fecha": "2025-02-20",
        "rol_en_linea": "soporte",
        "orden": 2,
    })
    assert r.status_code == 201

    r = await client.get(f"/v1/criterio/{linea_id_2}/referencias")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # seed refs + 2 new


@pytest.mark.asyncio
async def test_agregar_referencia_sin_documento(client, linea_id_2):
    r = await client.post(f"/v1/criterio/{linea_id_2}/referencias", json={
        "tipo_documento": "sentencia",
    })
    assert r.status_code == 422
