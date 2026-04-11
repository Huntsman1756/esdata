# apps/api/tests/test_smoke.py

import pytest
from httpx import ASGITransport, AsyncClient
from pathlib import Path
from sqlalchemy import text
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_health():
    async with _client() as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_status_tiene_workers():
    async with _client() as c:
        r = await c.get("/status")
    assert r.status_code == 200
    data = r.json()
    assert "workers" in data
    for w in [
        "worker-boe",
        "cron-boe-daily",
        "worker-dgt",
        "cron-dgt-weekly",
        "worker-teac",
        "cron-teac-weekly",
    ]:
        assert w in data["workers"]


@pytest.mark.asyncio
async def test_status_expone_metricas_dgt_si_existen():
    from conftest import engine

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM sync_log WHERE worker = 'worker-dgt'"))
        conn.execute(
            text(
                """
                INSERT INTO sync_log (
                    worker, started_at, finished_at, status,
                    bloques_processed, articulos_upserted,
                    documentos_processed, documentos_upserted, doctrina_links_created,
                    error_msg
                )
                VALUES (
                    'worker-dgt', '2026-04-11T10:00:00+00:00', '2026-04-11T10:05:00+00:00', 'ok',
                    0, 0,
                    12, 9, 7,
                    NULL
                )
                """
            )
        )

    async with _client() as c:
        r = await c.get("/status")
    assert r.status_code == 200
    data = r.json()
    worker = data["workers"]["worker-dgt"]
    assert worker["documentos_processed"] == 12
    assert worker["documentos_upserted"] == 9
    assert worker["doctrina_links_created"] == 7


@pytest.mark.asyncio
async def test_liva_articulo_91():
    async with _client() as c:
        r = await c.get("/v1/legislacion/LIVA/articulos/91")
    assert r.status_code == 200
    data = r.json()
    assert "texto" in data and len(data["texto"]) > 0
    assert data["confianza"]["nivel"] >= 1


@pytest.mark.asyncio
async def test_liva_articulo_91_vigente_en_fecha():
    async with _client() as c:
        r = await c.get("/v1/legislacion/LIVA/articulos/91?vigente_en=2020-01-01")
    assert r.status_code == 200
    data = r.json()
    assert data["vigente_desde"] <= "2020-01-01"
    assert data.get("vigente_hasta") is None or data["vigente_hasta"] >= "2020-01-01"


@pytest.mark.asyncio
async def test_materia_tipo_reducido_iva():
    async with _client() as c:
        r = await c.get("/v1/materias/tipo-reducido-iva")
    assert r.status_code == 200
    data = r.json()
    codigos = [a["norma"] + " " + a["numero"] for a in data["articulos"]]
    assert "LIVA 91" in codigos


@pytest.mark.asyncio
async def test_materias_lista():
    async with _client() as c:
        r = await c.get("/v1/materias")
    assert r.status_code == 200
    data = r.json()
    assert "materias" in data
    assert any(m["slug"] == "tipo-reducido-iva" for m in data["materias"])


@pytest.mark.asyncio
async def test_legislacion_lista_articulos_por_norma():
    async with _client() as c:
        r = await c.get("/v1/legislacion/LIVA/articulos")
    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "LIVA"
    assert any(a["numero"] == "91" for a in data["articulos"])


@pytest.mark.asyncio
async def test_legislacion_lista_articulos_filtra_por_tipo():
    async with _client() as c:
        r = await c.get("/v1/legislacion/LIVA/articulos?tipo=articulo")
    assert r.status_code == 200
    data = r.json()
    assert len(data["articulos"]) >= 1
    assert all(a["tipo"] == "articulo" for a in data["articulos"])


@pytest.mark.asyncio
async def test_busqueda_full_text():
    async with _client() as c:
        r = await c.get("/v1/legislacion/buscar?q=tipo+reducido&norma=LIVA")
    assert r.status_code == 200
    data = r.json()
    assert len(data["resultados"]) > 0
    for res in data["resultados"]:
        assert "confianza" in res
        assert "fragmento" in res


@pytest.mark.asyncio
async def test_doctrina_buscar_por_texto():
    async with _client() as c:
        r = await c.get("/v1/doctrina/buscar?q=tipo+reducido")
    assert r.status_code == 200
    data = r.json()
    assert len(data["resultados"]) >= 1
    assert any(item["referencia"] == "V0000-26" for item in data["resultados"])


@pytest.mark.asyncio
async def test_doctrina_buscar_filtra_por_tipo():
    async with _client() as c:
        r = await c.get("/v1/doctrina/buscar?q=tipo+reducido&tipo=consulta_vinculante")
    assert r.status_code == 200
    data = r.json()
    assert len(data["resultados"]) >= 1
    assert all(
        item["tipo_documento"] == "consulta_vinculante" for item in data["resultados"]
    )


@pytest.mark.asyncio
async def test_doctrina_buscar_filtra_por_organismo_y_expone_senal_de_enlace():
    async with _client() as c:
        r = await c.get("/v1/doctrina/buscar?q=tipo+reducido&organismo_emisor=DGT")
    assert r.status_code == 200
    data = r.json()
    assert len(data["resultados"]) >= 1
    item = next(
        result for result in data["resultados"] if result["referencia"] == "V0000-26"
    )
    assert item["organismo_emisor"] == "DGT"
    assert item["nivel_enlace"] == 1.0
    assert item["norma"] == "LIVA"
    assert item["numero"] == "91"


@pytest.mark.asyncio
async def test_doctrina_buscar_filtra_teac():
    from conftest import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                    ambito, referencia, fecha, titulo, texto, url_fuente
                )
                VALUES (
                    'resolucion_teac', 'TEAC', 'es', 'teac',
                    'fiscal', '00/1234/2024', '2024-03-15',
                    'IVA. Base imponible en operaciones vinculadas.',
                    'Se fija criterio TEAC sobre la base imponible del IVA.',
                    'https://serviciostelematicosext.hacienda.gob.es/TEAC/00-1234-2024'
                )
                """
            )
        )

    async with _client() as c:
        r = await c.get("/v1/doctrina/buscar?q=criterio&organismo_emisor=TEAC")
    assert r.status_code == 200
    data = r.json()
    item = next(
        result
        for result in data["resultados"]
        if result["referencia"] == "00/1234/2024"
    )
    assert item["organismo_emisor"] == "TEAC"
    assert item["tipo_documento"] == "resolucion_teac"


@pytest.mark.asyncio
async def test_doctrina_buscar_expone_teac_con_enlace():
    from conftest import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                    ambito, referencia, fecha, titulo, texto, url_fuente
                )
                VALUES (
                    'resolucion_teac', 'TEAC', 'es', 'teac',
                    'fiscal', '00/1234/2025', '2024-03-15',
                    'IVA. Base imponible en operaciones vinculadas.',
                    'Se analiza el articulo 91 de la Ley 37/1992.',
                    'https://serviciostelematicosext.hacienda.gob.es/TEAC/00-1234-2025'
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
                SELECT d.id, a.id, 'auto_link', 1.00, 'TEAC fixture'
                FROM documento_interpretativo d
                JOIN articulo a ON a.numero = '91'
                JOIN norma n ON n.id = a.norma_id
                WHERE d.referencia = '00/1234/2025' AND n.codigo = 'LIVA'
                """
            )
        )

    async with _client() as c:
        r = await c.get("/v1/doctrina/buscar?q=Ley+37%2F1992&organismo_emisor=TEAC")
    assert r.status_code == 200
    data = r.json()
    item = next(
        result
        for result in data["resultados"]
        if result["referencia"] == "00/1234/2025"
    )
    assert item["organismo_emisor"] == "TEAC"
    assert item["norma"] == "LIVA"
    assert item["numero"] == "91"
    assert item["nivel_enlace"] == 1.0


@pytest.mark.asyncio
async def test_doctrina_seed():
    async with _client() as c:
        r = await c.get("/v1/doctrina/V0000-26")
    assert r.status_code == 200
    data = r.json()
    assert data["confianza"]["nivel"] >= 0


@pytest.mark.asyncio
async def test_doctrina_detalle_expone_articulos_relacionados():
    async with _client() as c:
        r = await c.get("/v1/doctrina/V0000-26")
    assert r.status_code == 200
    data = r.json()
    assert data["articulos_relacionados"] == [
        {
            "norma": "LIVA",
            "numero": "91",
            "metodo_enlace": "manual",
            "confianza_enlace": 1.0,
        }
    ]


@pytest.mark.asyncio
async def test_articulo_inexistente_devuelve_404():
    async with _client() as c:
        r = await c.get("/v1/legislacion/LIVA/articulos/9999")
    assert r.status_code == 404
    assert "detail" in r.json()


@pytest.mark.asyncio
async def test_cobertura_muestra_normas():
    async with _client() as c:
        r = await c.get("/v1/legislacion/cobertura")
    assert r.status_code == 200
    data = r.json()
    assert "normas" in data
    codigos = [n["codigo"] for n in data["normas"]]
    assert "LIVA" in codigos
    liva = next(n for n in data["normas"] if n["codigo"] == "LIVA")
    assert "articulos" in liva and liva["articulos"] >= 1
    assert "versiones" in liva and liva["versiones"] >= 1
