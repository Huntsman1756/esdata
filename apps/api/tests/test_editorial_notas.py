from pathlib import Path
import sys

from httpx import ASGITransport, AsyncClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


@pytest.mark.asyncio
async def test_listar_notas_editoriales_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/notas")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_listar_notas_editoriales_returns_seed_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/notas")
    data = r.json()
    assert data["total"] >= 1
    notas = data["notas"]
    assert len(notas) >= 1
    nota = notas[0]
    assert nota["titulo"] == "Resumen operativo: Circular CNMV 9/2008"
    assert nota["estado"] == "vigente"
    assert nota["tipo_contenido"] == "resumen_interno"
    assert nota["fuente_oficial_referencia"] == "BOE-A-2009-133"
    assert nota["autor_id"] == "compliance"


@pytest.mark.asyncio
async def test_listar_notas_editoriales_filters_by_estado():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/notas", params={"estado": "vigente"})
    data = r.json()
    assert r.status_code == 200
    assert data["total"] >= 1
    for nota in data["notas"]:
        assert nota["estado"] == "vigente"


@pytest.mark.asyncio
async def test_listar_notas_editoriales_filters_by_tipo():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/notas", params={"tipo": "resumen_interno"})
    data = r.json()
    assert r.status_code == 200
    for nota in data["notas"]:
        assert nota["tipo_contenido"] == "resumen_interno"


@pytest.mark.asyncio
async def test_listar_notas_editoriales_filters_by_fuente():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/notas", params={"fuente": "BOE-A-2009-133"})
    data = r.json()
    assert r.status_code == 200
    for nota in data["notas"]:
        assert nota["fuente_oficial_referencia"] == "BOE-A-2009-133"


@pytest.mark.asyncio
async def test_listar_notas_editoriales_search_by_title():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/notas", params={"q": "Circular"})
    data = r.json()
    assert r.status_code == 200
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_listar_notas_editoriales_pagination():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/notas", params={"limit": 1, "skip": 0})
    data = r.json()
    assert r.status_code == 200
    assert len(data["notas"]) >= 1
    assert len(data["notas"]) <= 1


@pytest.mark.asyncio
async def test_get_nota_editorial_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        list_r = await c.get("/v1/editorial/notas")
        data = list_r.json()
        nota_id = data["notas"][0]["id"]
        r = await c.get(f"/v1/editorial/notas/{nota_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["titulo"] == "Resumen operativo: Circular CNMV 9/2008"
    assert body["estado"] == "vigente"
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_get_nota_editorial_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/notas/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "Nota editorial no encontrada"


@pytest.mark.asyncio
async def test_crear_nota_editorial():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/v1/editorial/notas", json={
            "titulo": "Nota de prueba",
            "resumen_ejecutivo": "Resumen de prueba",
            "contexto": "Contexto de prueba",
            "impacto_practico": "Impacto de prueba",
            "advertencias": "Advertencia de prueba",
            "fuente_oficial_referencia": "BOE-A-TEST-2026",
            "autor_id": "test_user",
            "estado": "borrador",
            "tipo_contenido": "nota_operativa",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["titulo"] == "Nota de prueba"
        assert body["estado"] == "borrador"
        assert body["tipo_contenido"] == "nota_operativa"
        assert body["autor_id"] == "test_user"
        nota_id = body["id"]

        # Verify it was persisted
        r2 = await c.get(f"/v1/editorial/notas/{nota_id}")
        assert r2.status_code == 200
        assert r2.json()["titulo"] == "Nota de prueba"


@pytest.mark.asyncio
async def test_actualizar_nota_editorial():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        create_r = await c.post("/v1/editorial/notas", json={
            "titulo": "Nota original",
            "resumen_ejecutivo": "Resumen original",
            "fuente_oficial_referencia": "BOE-A-TEST-2026",
            "autor_id": "test_user",
            "estado": "borrador",
            "tipo_contenido": "resumen_interno",
        })
        nota_id = create_r.json()["id"]

        update_r = await c.patch(f"/v1/editorial/notas/{nota_id}", json={
            "estado": "vigente",
            "titulo": "Nota actualizada",
        })
        assert update_r.status_code == 200
        body = update_r.json()
        assert body["titulo"] == "Nota actualizada"
        assert body["estado"] == "vigente"

        # Verify persistence
        get_r = await c.get(f"/v1/editorial/notas/{nota_id}")
        assert get_r.status_code == 200
        assert get_r.json()["estado"] == "vigente"


@pytest.mark.asyncio
async def test_actualizar_nota_editorial_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.patch("/v1/editorial/notas/00000000-0000-0000-0000-000000000000", json={
            "estado": "vigente",
        })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_crear_nota_editorial_resolves_documento_origen():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/v1/editorial/notas", json={
            "titulo": "Nota con origen CNMV",
            "resumen_ejecutivo": "Resumen",
            "fuente_oficial_referencia": "BOE-A-2009-133",
            "documento_origen_referencia": "BOE-A-2009-133",
            "autor_id": "compliance",
            "estado": "vigente",
            "tipo_contenido": "criterio_experto",
        })
    assert r.status_code == 200
    body = r.json()
    assert body["documento_origen_id"] is not None


@pytest.mark.asyncio
async def test_listar_notas_editoriales_empty_filter():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/editorial/notas", params={"tipo": "nota_operativa"})
    data = r.json()
    assert r.status_code == 200
    for nota in data["notas"]:
        assert nota["tipo_contenido"] == "nota_operativa"
