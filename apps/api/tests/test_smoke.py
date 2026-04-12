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
async def test_doctrina_detalle_teac_acepta_referencia_con_slash():
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
                    'fiscal', '00/5678/2025', '2024-03-15',
                    'IVA. Deducciones.',
                    'Resolucion TEAC con referencia que contiene slash.',
                    'https://serviciostelematicosext.hacienda.gob.es/TEAC/00-5678-2025'
                )
                """
            )
        )

    async with _client() as c:
        r = await c.get("/v1/doctrina/00/5678/2025")
    assert r.status_code == 200
    data = r.json()
    assert data["referencia"] == "00/5678/2025"
    assert data["organismo_emisor"] == "TEAC"


@pytest.mark.asyncio
async def test_doctrina_buscar_expone_teac_con_enlace_contextual():
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
                    'fiscal', '00/9876/2024', '2024-06-20',
                    'IVA. Base imponible negativa.',
                    'Se fija criterio sobre la base imponible negativa en el IVA.',
                    'https://serviciostelematicosext.hacienda.gob.es/TEAC/00-9876-2024'
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
                SELECT d.id, a.id, 'auto_link', 0.75, 'TEAC contextual fixture'
                FROM documento_interpretativo d
                JOIN articulo a ON a.numero = '91'
                JOIN norma n ON n.id = a.norma_id
                WHERE d.referencia = '00/9876/2024' AND n.codigo = 'LIVA'
                """
            )
        )

    async with _client() as c:
        r = await c.get("/v1/doctrina/buscar?q=base+imponible&organismo_emisor=TEAC")
    assert r.status_code == 200
    data = r.json()
    item = next(
        result
        for result in data["resultados"]
        if result["referencia"] == "00/9876/2024"
    )
    assert item["organismo_emisor"] == "TEAC"
    assert item["norma"] == "LIVA"
    assert item["numero"] == "91"
    assert item["nivel_enlace"] == 0.75


@pytest.mark.asyncio
async def test_doctrina_buscar_expone_teac_con_enlace_regimen_especial():
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
                    'fiscal', '00/2468/2024', '2024-09-10',
                    'IVA. Regimen especial aplicable.',
                    'Se fija criterio sobre el regimen especial del IVA en determinadas operaciones.',
                    'https://serviciostelematicosext.hacienda.gob.es/TEAC/00-2468-2024'
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
                SELECT d.id, a.id, 'auto_link', 0.75, 'TEAC regimen fixture'
                FROM documento_interpretativo d
                JOIN articulo a ON a.numero = '91'
                JOIN norma n ON n.id = a.norma_id
                WHERE d.referencia = '00/2468/2024' AND n.codigo = 'LIVA'
                """
            )
        )

    async with _client() as c:
        r = await c.get("/v1/doctrina/buscar?q=regimen+especial&organismo_emisor=TEAC")
    assert r.status_code == 200
    data = r.json()
    item = next(
        result
        for result in data["resultados"]
        if result["referencia"] == "00/2468/2024"
    )
    assert item["organismo_emisor"] == "TEAC"
    assert item["norma"] == "LIVA"
    assert item["numero"] == "91"
    assert item["nivel_enlace"] == 0.75


@pytest.mark.asyncio
async def test_doctrina_buscar_expone_teac_con_enlace_recargo():
    from conftest import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO articulo (norma_id, numero, titulo, tipo)
                SELECT id, '24', 'Recargo de equivalencia', 'articulo'
                FROM norma WHERE codigo = 'LIVA'
                ON CONFLICT DO NOTHING
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                    ambito, referencia, fecha, titulo, texto, url_fuente
                )
                VALUES (
                    'resolucion_teac', 'TEAC', 'es', 'teac',
                    'fiscal', '00/3579/2024', '2024-11-12',
                    'IVA. Recargo de equivalencia.',
                    'Se fija criterio sobre el recargo de equivalencia en el IVA aplicable a comerciantes minoristas.',
                    'https://serviciostelematicosext.hacienda.gob.es/TEAC/00-3579-2024'
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
                SELECT d.id, a.id, 'auto_link', 0.75, 'TEAC recargo fixture'
                FROM documento_interpretativo d
                JOIN articulo a ON a.numero = '24'
                JOIN norma n ON n.id = a.norma_id
                WHERE d.referencia = '00/3579/2024' AND n.codigo = 'LIVA'
                """
            )
        )

    async with _client() as c:
        r = await c.get(
            "/v1/doctrina/buscar?q=recargo+de+equivalencia&organismo_emisor=TEAC"
        )
    assert r.status_code == 200
    data = r.json()
    item = next(
        result
        for result in data["resultados"]
        if result["referencia"] == "00/3579/2024"
    )
    assert item["organismo_emisor"] == "TEAC"
    assert item["norma"] == "LIVA"
    assert item["numero"] == "24"
    assert item["nivel_enlace"] == 0.75


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


@pytest.mark.asyncio
async def test_modelos_lista():
    async with _client() as c:
        r = await c.get("/v1/modelos")
    assert r.status_code == 200
    data = r.json()
    assert "modelos" in data
    assert len(data["modelos"]) == 2  # 100, 303 in test fixture
    codigos = [m["codigo"] for m in data["modelos"]]
    assert "100" in codigos
    assert "303" in codigos


@pytest.mark.asyncio
async def test_modelo_detalle_con_fuente():
    async with _client() as c:
        r = await c.get("/v1/modelos/100")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "100"
    assert data["impuesto"] == "IRPF"
    assert len(data["articulos"]) >= 1
    art = data["articulos"][0]
    assert "norma" in art
    assert "numero" in art
    assert "fuente" in art and art["fuente"] is not None
    assert "url_fuente" in art


@pytest.mark.asyncio
async def test_modelo_detalle_doctrina_derivada():
    async with _client() as c:
        r = await c.get("/v1/modelos/100")
    assert r.status_code == 200
    data = r.json()
    # LIVA 91 is linked to model 100 AND to doctrine V0000-26
    # so doctrina_relacionada should include V0000-26
    refs = [d["referencia"] for d in data["doctrina_relacionada"]]
    assert "V0000-26" in refs
    doc = next(d for d in data["doctrina_relacionada"] if d["referencia"] == "V0000-26")
    assert doc["organismo_emisor"] == "DGT"
    assert len(doc["via_articulos"]) >= 1


@pytest.mark.asyncio
async def test_modelo_articulos_endpoint():
    async with _client() as c:
        r = await c.get("/v1/modelos/303/articulos")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "303"
    assert len(data["articulos"]) == 0  # no articles seeded for 303 in tests


@pytest.mark.asyncio
async def test_modelo_inexistente_404():
    async with _client() as c:
        r = await c.get("/v1/modelos/999")
    assert r.status_code == 404
    assert "detail" in r.json()
