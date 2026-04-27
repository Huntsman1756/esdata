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
    """Return the ID of the first seed linea_criterio (IVA)."""
    r = await client.get("/v1/criterio", params={"limit": 100})
    data = r.json()
    assert data["total"] >= 7
    return data["lineas"][0]["id"]


@pytest_asyncio.fixture
async def linea_id_mifid(client):
    """Return the ID of the second seed linea_criterio (Comisiones MiFID)."""
    r = await client.get("/v1/criterio", params={"limit": 100})
    data = r.json()
    assert data["total"] >= 7
    return data["lineas"][1]["id"]


# ---------------------------------------------------------------------------
# Sugerir curacion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sugerir_curacion_returns_200(client):
    r = await client.get("/v1/criterio/curacion/suggest")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_sugerir_curacion_returns_suggestions(client):
    r = await client.get("/v1/criterio/curacion/suggest")
    data = r.json()
    assert "sugerencias" in data
    assert "total_lineas" in data
    assert data["total_lineas"] >= 1
    assert len(data["sugerencias"]) >= 1


@pytest.mark.asyncio
async def test_sugerir_curacion_has_candidatos(client):
    r = await client.get("/v1/criterio/curacion/suggest")
    data = r.json()
    sugerencias = data["sugerencias"]
    assert len(sugerencias) >= 1
    for sug in sugerencias:
        assert "linea_id" in sug
        assert "linea_titulo" in sug
        assert "candidatos" in sug
        assert "total_sugeridos" in sug
        assert sug["total_sugeridos"] >= 1
        for c in sug["candidatos"]:
            assert "id" in c
            assert "referencia" in c
            assert "score" in c
            assert isinstance(c["score"], int)
            assert 0 <= c["score"] <= 3


@pytest.mark.asyncio
async def test_sugerir_curacion_iva_has_tributary_candidatos(client):
    r = await client.get("/v1/criterio/curacion/suggest")
    data = r.json()
    # Find the IVA linea
    iva_sug = None
    for sug in data["sugerencias"]:
        if "iva" in sug["linea_titulo"].lower():
            iva_sug = sug
            break
    assert iva_sug is not None
    assert iva_sug["total_sugeridos"] >= 1
    # At least one candidate with score >= 1
    high_score = [c for c in iva_sug["candidatos"] if c["score"] >= 1]
    assert len(high_score) >= 1


@pytest.mark.asyncio
async def test_sugerir_curacion_has_limit_10(client):
    r = await client.get("/v1/criterio/curacion/suggest")
    data = r.json()
    for sug in data["sugerencias"]:
        assert len(sug["candidatos"]) <= 10


# ---------------------------------------------------------------------------
# Asignar documento a linea
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asignar_documento_success(client, linea_id):
    r = await client.post("/v1/criterio/curacion/assign", json={
        "linea_id": linea_id,
        "documento_referencia": "STS-NEW/2025",
        "rol_en_linea": "soporte_complementario",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["assigned"] is True
    assert data["documento_referencia"] == "STS-NEW/2025"
    assert data["referencia_existia"] is False


@pytest.mark.asyncio
async def test_asignar_documento_duplicate(client, linea_id):
    # First assignment
    r1 = await client.post("/v1/criterio/curacion/assign", json={
        "linea_id": linea_id,
        "documento_referencia": "STS-DUP/2025",
        "rol_en_linea": "soporte",
    })
    assert r1.status_code == 200
    assert r1.json()["assigned"] is True
    assert r1.json()["referencia_existia"] is False

    # Second attempt with same reference
    r2 = await client.post("/v1/criterio/curacion/assign", json={
        "linea_id": linea_id,
        "documento_referencia": "STS-DUP/2025",
        "rol_en_linea": "soporte",
    })
    assert r2.status_code == 200
    assert r2.json()["assigned"] is False
    assert r2.json()["referencia_existia"] is True


@pytest.mark.asyncio
async def test_asignar_documento_404_linea(client):
    r = await client.post("/v1/criterio/curacion/assign", json={
        "linea_id": 999999,
        "documento_referencia": "STS-999/2025",
    })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_asignar_documento_default_rol(client, linea_id):
    r = await client.post("/v1/criterio/curacion/assign", json={
        "linea_id": linea_id,
        "documento_referencia": "STS-ROL/2025",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["assigned"] is True


@pytest.mark.asyncio
async def test_asignar_documento_from_documento_interpretativo(client, linea_id_mifid):
    """Assign a document that exists in documento_interpretativo table."""
    r = await client.post("/v1/criterio/curacion/assign", json={
        "linea_id": linea_id_mifid,
        "documento_referencia": "STS-2200/2025",
        "rol_en_linea": "doctrina_principal",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["assigned"] is True
    assert data["documento_referencia"] == "STS-2200/2025"
