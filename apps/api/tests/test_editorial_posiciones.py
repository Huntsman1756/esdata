from pathlib import Path
import sys

from httpx import ASGITransport, AsyncClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


@pytest.mark.asyncio
async def test_listar_posiciones_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/posiciones")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_listar_posiciones_returns_seed_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/posiciones")
    data = r.json()
    assert data["total"] >= 1
    posiciones = data["posiciones"]
    assert len(posiciones) >= 1
    pos = posiciones[0]
    assert pos["titulo"] == "Criterio interno: adecuación MiFID II"
    assert pos["estado"] == "vigente"
    assert pos["version"] == 1
    assert pos["autor_id"] == "compliance"


@pytest.mark.asyncio
async def test_listar_posiciones_filters_by_estado():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/posiciones", params={"estado": "vigente"})
    data = r.json()
    assert r.status_code == 200
    assert data["total"] >= 1
    for pos in data["posiciones"]:
        assert pos["estado"] == "vigente"


@pytest.mark.asyncio
async def test_listar_posiciones_filters_by_fuente():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/posiciones", params={"fuente": "eurl:2014:65"})
    data = r.json()
    assert r.status_code == 200
    for pos in data["posiciones"]:
        assert pos["fuente_oficial_referencia"] == "eurl:2014:65"


@pytest.mark.asyncio
async def test_listar_posiciones_search_by_title():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/posiciones", params={"q": "MiFID"})
    data = r.json()
    assert r.status_code == 200
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_listar_posiciones_pagination():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/posiciones", params={"limit": 1, "skip": 0})
    data = r.json()
    assert r.status_code == 200
    assert len(data["posiciones"]) >= 1
    assert len(data["posiciones"]) <= 1


@pytest.mark.asyncio
async def test_get_posicion_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        list_r = await c.get("/v1/editorial/posiciones")
        data = list_r.json()
        pos_id = data["posiciones"][0]["id"]
        r = await c.get(f"/v1/editorial/posiciones/{pos_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["titulo"] == "Criterio interno: adecuación MiFID II"
    assert body["estado"] == "vigente"
    assert body["version"] == 1
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_get_posicion_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/posiciones/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "Posicion interpretativa no encontrada"


@pytest.mark.asyncio
async def test_crear_posicion_interpretativa():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/v1/editorial/posiciones", json={
            "titulo": "Posicion de prueba",
            "descripcion": "Descripcion de prueba",
            "contenido": "Contenido de prueba",
            "fuente_oficial_referencia": "BOE-A-TEST-2026",
            "autor_id": "test_user",
            "estado": "borrador",
            "vigencia_desde": "2026-06-01",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["titulo"] == "Posicion de prueba"
        assert body["estado"] == "borrador"
        assert body["version"] == 1
        assert body["autor_id"] == "test_user"
        pos_id = body["id"]

        # Verify persistence
        r2 = await c.get(f"/v1/editorial/posiciones/{pos_id}")
        assert r2.status_code == 200
        assert r2.json()["titulo"] == "Posicion de prueba"


@pytest.mark.asyncio
async def test_actualizar_posicion_interpretativa():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        create_r = await c.post("/v1/editorial/posiciones", json={
            "titulo": "Posicion original",
            "descripcion": "Descripcion original",
            "contenido": "Contenido original",
            "fuente_oficial_referencia": "BOE-A-TEST-2026",
            "autor_id": "test_user",
            "estado": "borrador",
        })
        pos_id = create_r.json()["id"]

        update_r = await c.patch(f"/v1/editorial/posiciones/{pos_id}", json={
            "estado": "vigente",
            "titulo": "Posicion actualizada",
        })
        assert update_r.status_code == 200
        body = update_r.json()
        assert body["titulo"] == "Posicion actualizada"
        assert body["estado"] == "vigente"

        get_r = await c.get(f"/v1/editorial/posiciones/{pos_id}")
        assert get_r.status_code == 200
        assert get_r.json()["estado"] == "vigente"


@pytest.mark.asyncio
async def test_actualizar_posicion_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.patch("/v1/editorial/posiciones/00000000-0000-0000-0000-000000000000", json={
            "estado": "vigente",
        })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_crear_posicion_resolves_documento_origen():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/v1/editorial/posiciones", json={
            "titulo": "Posicion con origen CNMV",
            "descripcion": "Descripcion",
            "contenido": "Contenido",
            "fuente_oficial_referencia": "BOE-A-2009-133",
            "documento_origen_referencia": "BOE-A-2009-133",
            "autor_id": "compliance",
            "estado": "vigente",
        })
    assert r.status_code == 200
    body = r.json()
    assert body["documento_origen_id"] is not None


@pytest.mark.asyncio
async def test_posicion_version_automatica():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r1 = await c.post("/v1/editorial/posiciones", json={
            "titulo": "Posicion version 1",
            "descripcion": "Primera version",
            "contenido": "Contenido v1",
            "fuente_oficial_referencia": "BOE-A-TEST-VER",
            "documento_origen_referencia": "BOE-A-2009-133",
            "autor_id": "test_user",
            "estado": "vigente",
        })
        assert r1.status_code == 200
        v1 = r1.json()
        assert v1["version"] >= 1

        r2 = await c.post("/v1/editorial/posiciones", json={
            "titulo": "Posicion version 2",
            "descripcion": "Segunda version",
            "contenido": "Contenido v2",
            "fuente_oficial_referencia": "BOE-A-TEST-VER-2",
            "documento_origen_referencia": "BOE-A-2009-133",
            "autor_id": "test_user",
            "estado": "vigente",
        })
        assert r2.status_code == 200
        v2 = r2.json()
        assert v2["version"] > v1["version"]


@pytest.mark.asyncio
async def test_listar_posiciones_empty_filter():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/posiciones", params={"estado": "borrador"})
    data = r.json()
    assert r.status_code == 200
    for pos in data["posiciones"]:
        assert pos["estado"] == "borrador"
