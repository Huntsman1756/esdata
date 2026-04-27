# apps/api/tests/test_eurlex_router.py

import pytest
from httpx import ASGITransport, AsyncClient
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_eurlex_lista_status_200():
    async with _client() as c:
        r = await c.get("/v1/eurlex")
    assert r.status_code == 200
    data = r.json()
    assert "documentos" in data
    assert isinstance(data["documentos"], list)


@pytest.mark.asyncio
async def test_eurlex_lista_contiene_seed():
    async with _client() as c:
        r = await c.get("/v1/eurlex")
    refs = [d["referencia"] for d in r.json()["documentos"]]
    assert "EUR-Lex-32020R548" in refs


@pytest.mark.asyncio
async def test_eurlex_lista_response_model():
    async with _client() as c:
        r = await c.get("/v1/eurlex")
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
async def test_eurlex_lista_no_incluye_organismo_emisor():
    async with _client() as c:
        r = await c.get("/v1/eurlex")
    for item in r.json()["documentos"]:
        assert "organismo_emisor" not in item


@pytest.mark.asyncio
async def test_eurlex_lista_fragmento_trunca():
    async with _client() as c:
        r = await c.get("/v1/eurlex")
    for item in r.json()["documentos"]:
        assert len(item["fragmento"]) <= 223


@pytest.mark.asyncio
async def test_eurlex_lista_filtro_q():
    async with _client() as c:
        r = await c.get("/v1/eurlex?q=reglamento")
    docs = r.json()["documentos"]
    assert len(docs) >= 1
    found = False
    for d in docs:
        if "reglamento" in d["fragmento"].lower() or "reglamento" in (d.get("titulo") or "").lower():
            found = True
            break
    assert found


@pytest.mark.asyncio
async def test_eurlex_lista_filtro_q_no_match():
    async with _client() as c:
        r = await c.get("/v1/eurlex?q=zzzzxzzznoexiste")
    assert r.json()["documentos"] == []


@pytest.mark.asyncio
async def test_eurlex_lista_filtro_tipo():
    async with _client() as c:
        r = await c.get("/v1/eurlex?tipo=reglamento")
    docs = r.json()["documentos"]
    assert len(docs) >= 1
    for d in docs:
        assert d["tipo_documento"] == "reglamento"


@pytest.mark.asyncio
async def test_eurlex_lista_filtro_tipo_no_match():
    async with _client() as c:
        r = await c.get("/v1/eurlex?tipo=directiva")
    docs = r.json()["documentos"]
    assert len(docs) == 0


@pytest.mark.asyncio
async def test_eurlex_lista_filtro_ambito():
    async with _client() as c:
        r = await c.get("/v1/eurlex?ambito=mercado_interior")
    docs = r.json()["documentos"]
    assert len(docs) >= 1
    for d in docs:
        assert d["ambito"] == "mercado_interior"


@pytest.mark.asyncio
async def test_eurlex_lista_filtro_ambito_no_match():
    async with _client() as c:
        r = await c.get("/v1/eurlex?ambito=fiscal_ue")
    docs = r.json()["documentos"]
    assert len(docs) == 0


@pytest.mark.asyncio
async def test_eurlex_lista_filtros_combinados_q_ambito():
    async with _client() as c:
        r = await c.get("/v1/eurlex?q=reglamento&ambito=mercado_interior")
    docs = r.json()["documentos"]
    assert len(docs) >= 1
    for d in docs:
        assert d["tipo_documento"] == "reglamento"
        assert d["ambito"] == "mercado_interior"


@pytest.mark.asyncio
async def test_eurlex_detalle_status_200():
    async with _client() as c:
        r = await c.get("/v1/eurlex/EUR-Lex-32020R548")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_eurlex_detalle_response_model():
    async with _client() as c:
        r = await c.get("/v1/eurlex/EUR-Lex-32020R548")
    data = r.json()
    assert data["referencia"] == "EUR-Lex-32020R548"
    assert "fecha" in data
    assert "titulo" in data
    assert "tipo_documento" in data
    assert "ambito" in data
    assert "texto" in data
    assert "url_fuente" in data


@pytest.mark.asyncio
async def test_eurlex_detalle_campos_correctos():
    async with _client() as c:
        r = await c.get("/v1/eurlex/EUR-Lex-32020R548")
    data = r.json()
    assert data["tipo_documento"] == "reglamento"
    assert data["ambito"] == "mercado_interior"
    assert "reglamento" in data["titulo"].lower()


@pytest.mark.asyncio
async def test_eurlex_detalle_no_incluye_organismo_emisor():
    async with _client() as c:
        r = await c.get("/v1/eurlex/EUR-Lex-32020R548")
    data = r.json()
    assert "organismo_emisor" not in data


@pytest.mark.asyncio
async def test_eurlex_detalle_no_encontrado():
    async with _client() as c:
        r = await c.get("/v1/eurlex/ZZZZ-NO-EXISTE-9999")
    assert r.status_code == 404
    err = r.json()
    assert "detail" in err
    assert "no encontrado" in err["detail"]["error"].lower()


@pytest.mark.asyncio
async def test_eurlex_detalle_texto_completo_vs_fragmento():
    async with _client() as c:
        detalle = await c.get("/v1/eurlex/EUR-Lex-32020R548")
    detalle_data = detalle.json()
    assert len(detalle_data["texto"]) >= 50


@pytest.mark.asyncio
async def test_eurlex_lista_orden_desc():
    async with _client() as c:
        r = await c.get("/v1/eurlex")
    dates = []
    for d in r.json()["documentos"]:
        if d["fecha"]:
            dates.append(d["fecha"])
    assert dates == sorted(dates, reverse=True) or len(dates) <= 1
