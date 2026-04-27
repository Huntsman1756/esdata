# apps/api/tests/test_cendoj_router.py

import pytest
from httpx import ASGITransport, AsyncClient
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_cendoj_lista_status_200():
    async with _client() as c:
        r = await c.get("/v1/cendoj")
    assert r.status_code == 200
    data = r.json()
    assert "documentos" in data
    assert isinstance(data["documentos"], list)


@pytest.mark.asyncio
async def test_cendoj_lista_contiene_seed():
    async with _client() as c:
        r = await c.get("/v1/cendoj")
    refs = [d["referencia"] for d in r.json()["documentos"]]
    assert "STS-2847/2025" in refs


@pytest.mark.asyncio
async def test_cendoj_lista_response_model():
    async with _client() as c:
        r = await c.get("/v1/cendoj")
    data = r.json()
    assert "documentos" in data
    for item in data["documentos"]:
        assert "referencia" in item
        assert "fecha" in item
        assert "titulo" in item
        assert "tipo_documento" in item
        assert "ambito" in item
        assert "fragmento" in item
        assert "url_fuente" in item


@pytest.mark.asyncio
async def test_cendoj_lista_fragmento_trunca():
    async with _client() as c:
        r = await c.get("/v1/cendoj")
    for item in r.json()["documentos"]:
        assert len(item["fragmento"]) <= 223


@pytest.mark.asyncio
async def test_cendoj_lista_filtro_q():
    async with _client() as c:
        r = await c.get("/v1/cendoj?q=iva")
    docs = r.json()["documentos"]
    assert len(docs) >= 1
    found = False
    for d in docs:
        if "iva" in d["fragmento"].lower() or "iva" in (d.get("titulo") or "").lower():
            found = True
            break
    assert found


@pytest.mark.asyncio
async def test_cendoj_lista_filtro_q_no_match():
    async with _client() as c:
        r = await c.get("/v1/cendoj?q=zzzzxzzznoexiste")
    assert r.json()["documentos"] == []


@pytest.mark.asyncio
async def test_cendoj_lista_filtro_tipo():
    async with _client() as c:
        r = await c.get("/v1/cendoj?tipo=sentencia")
    docs = r.json()["documentos"]
    assert len(docs) >= 1
    for d in docs:
        assert d["tipo_documento"] == "sentencia"


@pytest.mark.asyncio
async def test_cendoj_lista_filtro_tipo_no_match():
    async with _client() as c:
        r = await c.get("/v1/cendoj?tipo=providencia")
    docs = r.json()["documentos"]
    assert len(docs) == 0


@pytest.mark.asyncio
async def test_cendoj_lista_filtro_tribunal():
    async with _client() as c:
        r = await c.get("/v1/cendoj?tribunal=tribunal_supremo")
    docs = r.json()["documentos"]
    assert len(docs) >= 1


@pytest.mark.asyncio
async def test_cendoj_lista_filtro_tribunal_no_match():
    async with _client() as c:
        r = await c.get("/v1/cendoj?tribunal=tsj")
    docs = r.json()["documentos"]
    assert len(docs) == 0, "El filtro tribunal=tsj no debería coincidir con Tribunal Supremo"


@pytest.mark.asyncio
async def test_cendoj_lista_filtro_organismo():
    async with _client() as c:
        r = await c.get("/v1/cendoj?organismo=Tribunal+Supremo")
    docs = r.json()["documentos"]
    assert len(docs) >= 1


@pytest.mark.asyncio
async def test_cendoj_lista_filtro_organismo_no_match():
    async with _client() as c:
        r = await c.get("/v1/cendoj?organismo=TSJ")
    docs = r.json()["documentos"]
    assert len(docs) == 0


@pytest.mark.asyncio
async def test_cendoj_lista_filtros_combinados_q_tipo():
    async with _client() as c:
        r = await c.get("/v1/cendoj?q=iva&tipo=sentencia")
    docs = r.json()["documentos"]
    assert len(docs) >= 1
    for d in docs:
        assert d["tipo_documento"] == "sentencia"
        assert "iva" in d["fragmento"].lower() or "iva" in (d.get("titulo") or "").lower()


@pytest.mark.asyncio
async def test_cendoj_lista_filtros_combinados_q_tribunal():
    async with _client() as c:
        r = await c.get("/v1/cendoj?q=restauracion&tribunal=tribunal_supremo")
    docs = r.json()["documentos"]
    assert len(docs) >= 1


@pytest.mark.asyncio
async def test_cendoj_detalle_status_200():
    async with _client() as c:
        r = await c.get("/v1/cendoj/STS-2847/2025")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_cendoj_detalle_response_model():
    async with _client() as c:
        r = await c.get("/v1/cendoj/STS-2847/2025")
    data = r.json()
    assert data["referencia"] == "STS-2847/2025"
    assert "fecha" in data
    assert "titulo" in data
    assert "tipo_documento" in data
    assert "ambito" in data
    assert "texto" in data
    assert "url_fuente" in data


@pytest.mark.asyncio
async def test_cendoj_detalle_campos_correctos():
    async with _client() as c:
        r = await c.get("/v1/cendoj/STS-2847/2025")
    data = r.json()
    assert data["tipo_documento"] == "sentencia"
    assert data["ambito"] == "tributario"
    assert "trib supremo" in data["titulo"].lower()
    assert "iva" in data["texto"].lower()


@pytest.mark.asyncio
async def test_cendoj_detalle_no_encontrado():
    async with _client() as c:
        r = await c.get("/v1/cendoj/ZZZZ-NO-EXISTE-9999")
    assert r.status_code == 404
    err = r.json()
    assert "detail" in err
    assert "no encontrado" in err["detail"]["error"].lower()


@pytest.mark.asyncio
async def test_cendoj_detalle_texto_completo_vs_fragmento():
    async with _client() as c:
        detalle = await c.get("/v1/cendoj/STS-2847/2025")
    detalle_data = detalle.json()
    assert len(detalle_data["texto"]) >= 50


@pytest.mark.asyncio
async def test_cendoj_lista_orden_desc():
    async with _client() as c:
        r = await c.get("/v1/cendoj")
    dates = []
    for d in r.json()["documentos"]:
        if d["fecha"]:
            dates.append(d["fecha"])
    assert dates == sorted(dates, reverse=True) or len(dates) <= 1
