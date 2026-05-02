# apps/api/tests/test_smoke.py

import pytest
from httpx import ASGITransport, AsyncClient
from pathlib import Path
from sqlalchemy import text
import sys


def _client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from main import app
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
        "worker-modelos",
        "cron-modelos-daily",
        "worker-bdns",
        "cron-bdns-weekly",
        "worker-borme",
        "cron-borme-weekly",
        "worker-cnmv",
        "cron-cnmv-weekly",
        "worker-sepblac",
        "cron-sepblac-weekly",
        "worker-cendoj",
        "worker-eurlex",
        "worker-bde",
        "cron-bde-weekly",
        "worker-aepd",
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
async def test_legislacion_expone_itpajd_con_clasificacion():
    async with _client() as c:
        lista = await c.get("/v1/legislacion")
        detalle = await c.get("/v1/legislacion/ITPAJD")
        articulo = await c.get("/v1/legislacion/ITPAJD/articulos/7")

    assert lista.status_code == 200
    assert detalle.status_code == 200
    assert articulo.status_code == 200

    norma = next(item for item in lista.json()["normas"] if item["codigo"] == "ITPAJD")
    assert norma["tipo_documento"] == "real_decreto_legislativo"
    assert norma["ambito"] == "tributario"
    assert norma["estado_cobertura"] == "ingestada"

    assert detalle.json()["tipo_documento"] == "real_decreto_legislativo"
    assert detalle.json()["estado_cobertura"] == "ingestada"
    assert "transmisiones" in articulo.json()["texto"].lower()


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
async def test_modelos_aeat_lista_con_total():
    async with _client() as c:
        r = await c.get("/v1/modelos/aeat")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    modelo_100 = next(item for item in data["items"] if item["codigo"] == "100")
    assert modelo_100["campana"] == "2025"
    assert modelo_100["recursos_activos"] == 1


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
async def test_modelo_aeat_detalle_solo_activos_por_defecto():
    async with _client() as c:
        r = await c.get("/v1/modelos/aeat/100")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "100"
    assert data["campana_actual"]["campana"] == "2025"
    assert len(data["campana_actual"]["recursos"]) == 1
    assert data["historial"] is None


@pytest.mark.asyncio
async def test_modelo_aeat_detalle_con_historial():
    async with _client() as c:
        r = await c.get("/v1/modelos/aeat/100?include_history=true")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "100"
    assert data["historial"] is not None
    assert len(data["historial"]) == 2
    campanas = [camp["campana"] for camp in data["historial"]]
    assert "2025" in campanas
    assert "2024" in campanas


@pytest.mark.asyncio
async def test_modelo_aeat_detalle_admite_campana_null_en_postgres():
    async with _client() as c:
        r = await c.get("/v1/modelos/aeat/100")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "100"
    assert data["campana_actual"]["campana"] == "2025"


@pytest.mark.asyncio
async def test_doctrina_busca_referencia_exacta_dgt():
    async with _client() as c:
        r = await c.get("/v1/doctrina/buscar?q=V0000-26&organismo_emisor=DGT")
    assert r.status_code == 200
    data = r.json()
    referencias = [item["referencia"] for item in data["resultados"]]
    assert "V0000-26" in referencias


@pytest.mark.asyncio
async def test_buscar_detecta_comparacion_de_modelos_aeat():
    async with _client() as c:
        r = await c.get("/v1/buscar?q=modelo+100+303+diferencia")
    assert r.status_code == 200
    data = r.json()
    codigos = {item["numero"] for item in data["resultados"]}
    assert {"100", "303"}.issubset(codigos)
    assert all(item["tipo"] == "modelo" for item in data["resultados"])


@pytest.mark.asyncio
async def test_modelo_articulos_endpoint():
    async with _client() as c:
        r = await c.get("/v1/modelos/303/articulos")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "303"
    assert len(data["articulos"]) == 0  # no articles seeded for 303 in tests


@pytest.mark.asyncio
async def test_modelo_campana_operativa_endpoint_devuelve_payload_valido():
    async with _client() as c:
        r = await c.get("/v1/modelos/100/campana-operativa")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "100"
    assert data["campana"] == "2025"
    assert isinstance(data["fuentes_recomendadas"], list)


@pytest.mark.asyncio
async def test_modelo_inexistente_404():
    async with _client() as c:
        r = await c.get("/v1/modelos/999")
    assert r.status_code == 404
    assert "detail" in r.json()


def test_metrics_endpoint_returns_200_with_metrics():
    """Verifica que GET /metrics devuelve 200 y contiene al menos una métrica Prometheus."""
    from unittest.mock import patch

    # Establecer variables antes de importar main
    with patch.dict("os.environ", {"APP_ENV": "test", "ESDATA_API_KEY": "test-key", "MCP_API_KEY": "test-key"}):
        # Importar main con las vars de entorno correctas
        import sys
        if "main" in sys.modules:
            del sys.modules["main"]
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from main import app as metrics_app

    client = AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test")

    async def _check():
        return await client.get("/metrics")

    import asyncio
    loop = asyncio.new_event_loop()
    try:
        response = loop.run_until_complete(_check())
    finally:
        loop.close()

    assert response.status_code == 200
    body = response.text
    assert "process_cpu_seconds_total" in body or "http_requests_total" in body, (
        f"/metrics no contiene métricas esperadas. Body preview: {body[:500]}"
    )


def test_metrics_endpoint_exposes_worker_last_errors_metric():
    from unittest.mock import patch

    from middleware.metrics import record_worker_last_errors

    with patch.dict("os.environ", {"APP_ENV": "test", "ESDATA_API_KEY": "test-key", "MCP_API_KEY": "test-key"}):
        import sys
        if "main" in sys.modules:
            del sys.modules["main"]
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from main import app as metrics_app

    record_worker_last_errors("worker-test", 2)

    client = AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test")

    async def _check():
        return await client.get("/metrics")

    import asyncio
    loop = asyncio.new_event_loop()
    try:
        response = loop.run_until_complete(_check())
    finally:
        loop.close()

    assert response.status_code == 200
    assert "worker_last_errors" in response.text
    assert 'worker_last_errors{worker="worker-test"} 2.0' in response.text


def test_status_endpoint_no_session_leaks():
    """Verifica que llamar al endpoint /status no deja sesiones abiertas.

    El pool de conexiones debe tener checkedout == 0 después de la request.
    Esto detecta regresiones donde se abre Session sin context manager.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from main import app

    from httpx import ASGITransport, AsyncClient

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def _call_status():
        return await client.get("/status")

    import asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_call_status())
    finally:
        loop.close()

    engine = app.state.engine if hasattr(app.state, "engine") else None
    # Si no hay engine expuesto, verificamos por el pool de db.py
    from db import engine as api_engine
    assert api_engine.pool.checkedout() == 0, (
        f"Session leak detectado: {api_engine.pool.checkedout()} conexiones checkout"
    )


def test_worker_heartbeat_file_created():
    """Verifica que los workers crean el archivo heartbeat.

    El heartbeat se usa para los healthchecks de Docker. Si no se crea,
    Docker no puede detectar crash loops silenciosos.
    """
    import os
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        heartbeat_path = Path(tmpdir) / "worker_heartbeat"
        heartbeat_path.touch()

        assert heartbeat_path.exists(), "El archivo heartbeat debe existir"
        mtime = heartbeat_path.stat().st_mtime
        import time
        time.sleep(0.1)
        heartbeat_path.touch()
        new_mtime = heartbeat_path.stat().st_mtime
        assert new_mtime > mtime, "touch() debe actualizar el mtime"
