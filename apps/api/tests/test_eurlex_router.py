# apps/api/tests/test_eurlex_router.py

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import db_session
from main import app


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _seed_eurlex_metadata_only():
    with db_session() as db:
        db.execute(
            text(
                """
                INSERT INTO norma (
                    codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
                    tipo_documento, ambito, estado_cobertura, vigente_desde
                )
                VALUES (
                    'EUR-Lex-METADATA-ONLY',
                    'Reglamento UE metadata only test',
                    'EUR-CELEX-39999R0001',
                    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:39999R0001',
                    'ue',
                    'eurlex',
                    'reglamento',
                    'mercado_interior',
                    'ingestada',
                    '2026-01-01'
                )
                ON CONFLICT (codigo) DO UPDATE SET
                    titulo = excluded.titulo,
                    eli_uri = excluded.eli_uri,
                    tipo_fuente = excluded.tipo_fuente
                """
            )
        )
        db.commit()


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
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert "total" in data
    for item in data["documentos"]:
        assert "referencia" in item
        assert "fecha" in item
        assert "titulo" in item
        assert "tipo_documento" in item
        assert "ambito" in item
        assert "fragmento" in item
        assert "url_fuente" in item
        assert "articulos_total" in item
        assert "coverage_status" in item
        assert "articles_expected" in item
        assert "articles_parsed" in item
        assert "quality_status" in item
        assert "verified" in item
        assert "completeness" in item
        assert "evidence_notice" in item


@pytest.mark.asyncio
async def test_eurlex_lista_paginada():
    async with _client() as c:
        r = await c.get("/v1/eurlex?limit=1&offset=0")
    data = r.json()
    assert r.status_code == 200
    assert len(data["documentos"]) <= 1
    assert data["limit"] == 1
    assert data["offset"] == 0
    assert "has_more" in data


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
    assert data["articulos_total"] >= 1
    assert data["coverage_status"] == "article_text_available"
    assert "articles_expected" in data
    assert "articles_parsed" in data
    assert "quality_status" in data
    assert data["verified"] is True
    assert data["completeness"] == "parcial"
    assert "Do not claim exhaustive coverage" in data["evidence_notice"]


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
async def test_eurlex_metadata_only_is_evidence_limited():
    _seed_eurlex_metadata_only()

    async with _client() as c:
        detalle = await c.get("/v1/eurlex/EUR-Lex-METADATA-ONLY")
        listado = await c.get("/v1/eurlex?q=metadata%20only")

    detail_data = detalle.json()
    assert detalle.status_code == 200
    assert detail_data["texto"] == ""
    assert detail_data["articulos_total"] == 0
    assert detail_data["coverage_status"] == "metadata_only"
    assert detail_data["quality_status"] == "metadata_only"
    assert detail_data["verified"] is False
    assert detail_data["completeness"] == "parcial"
    assert "evidence_limited" in detail_data["evidence_notice"]

    list_item = listado.json()["documentos"][0]
    assert list_item["referencia"] == "EUR-Lex-METADATA-ONLY"
    assert list_item["fragmento"] == ""
    assert list_item["articulos_total"] == 0
    assert list_item["coverage_status"] == "metadata_only"
    assert list_item["quality_status"] == "metadata_only"
    assert list_item["verified"] is False


@pytest.mark.asyncio
async def test_eurlex_reconciles_official_empty_article_blocks():
    with db_session() as db:
        db.execute(
            text(
                """
                UPDATE norma
                SET articles_expected = 2,
                    articles_parsed = 1,
                    articles_empty_official = 1,
                    quality_status = 'article_text_available'
                WHERE codigo = 'EUR-Lex-32020R548'
                """
            )
        )
        db.execute(
            text(
                """
                INSERT INTO articulo (norma_id, numero, titulo, tipo)
                SELECT id, '95 bis', 'Articulo 95 bis', 'articulo'
                FROM norma WHERE codigo = 'EUR-Lex-32020R548'
                ON CONFLICT (norma_id, numero) DO NOTHING
                """
            )
        )
        db.execute(
            text(
                """
                INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta)
                SELECT a.id, '', '2026-06-06', NULL
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = 'EUR-Lex-32020R548' AND a.numero = '95 bis'
                """
            )
        )
        db.commit()

    async with _client() as c:
        detalle = await c.get("/v1/eurlex/EUR-Lex-32020R548")

    data = detalle.json()
    assert detalle.status_code == 200
    assert data["articles_expected"] == 2
    assert data["articles_parsed"] == 1
    assert data["articles_empty_official"] == 1
    assert data["quality_status"] == "article_text_available"
    assert "official empty blocks" in data["evidence_notice"]


@pytest.mark.asyncio
async def test_eurlex_lista_orden_desc():
    async with _client() as c:
        r = await c.get("/v1/eurlex")
    dates = [d["fecha"] for d in r.json()["documentos"] if d["fecha"]]
    assert dates == sorted(dates, reverse=True) or len(dates) <= 1
