# apps/api/tests/test_smoke.py

import pytest
from httpx import ASGITransport, AsyncClient
from pathlib import Path
from sqlalchemy import text
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


def _client():
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    )


@pytest.mark.asyncio
async def test_health():
    async with _client() as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_gpt_action_spec_endpoint_serves_minimal_model_schema():
    async with _client() as c:
        r = await c.get("/gpt-actions/modelos/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert data["openapi"] == "3.1.0"
    assert "/v1/modelos/{codigo}" in data["paths"]


@pytest.mark.asyncio
async def test_privacy_policy_endpoint_serves_text():
    async with _client() as c:
        r = await c.get("/privacy")
    assert r.status_code == 200
    assert "privacy policy" in r.text.lower()


@pytest.mark.asyncio
async def test_metrics_expone_rutas_de_consulta_y_connectivity():
    async with _client() as c:
        consulta = await c.get("/v1/consulta?q=tipo+reducido+iva")
        connectivity = await c.get("/v1/connectivity/articulos/LIVA/91")
        metrics = await c.get("/metrics")

    assert consulta.status_code == 200
    assert connectivity.status_code == 200
    assert metrics.status_code == 200
    body = metrics.text
    assert 'http_requests_total{endpoint="/v1/consulta",method="GET",status="200"}' in body
    assert 'http_requests_total{endpoint="/v1/connectivity/articulos/LIVA/{}",method="GET",status="200"}' in body


@pytest.mark.asyncio
async def test_metrics_expone_faithfulness_y_review_required_en_consulta():
    async with _client() as c:
        consulta = await c.get("/v1/consulta?q=tipo+reducido+iva")
        metrics = await c.get("/metrics")

    assert consulta.status_code == 200
    assert metrics.status_code == 200
    body = metrics.text
    assert 'consulta_faithfulness_score' in body
    assert 'consulta_review_required_total{endpoint="/v1/consulta",review_required="false"}' in body


@pytest.mark.asyncio
async def test_observability_dashboard_resume_consulta_workers_y_fuentes():
    async with _client() as c:
        await c.get("/v1/consulta?q=tipo+reducido+iva")
        await c.get("/v1/connectivity/articulos/LIVA/91")
        await c.get("/v1/sources/freshness")
        await c.get("/status")
        r = await c.get("/v1/observability/dashboard")

    assert r.status_code == 200
    data = r.json()
    assert "consulta" in data
    assert "workers" in data
    assert "fuentes" in data
    assert data["consulta"]["faithfulness_score"] >= 0.0
    assert "worker-dgt" in data["workers"]
    assert "cnmv" in data["fuentes"]
    assert "summary" in data
    assert "stale_workers" in data["summary"]
    assert "stale_sources" in data["summary"]


@pytest.mark.asyncio
async def test_observability_alerts_deriva_alertas_operativas():
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
                ) VALUES (
                    'worker-dgt', '2026-04-11T10:00:00+00:00', '2026-04-11T10:05:00+00:00', 'ok',
                    0, 0,
                    12, 9, 7,
                    NULL
                )
                """
            )
        )

    async with _client() as c:
        await c.get("/v1/consulta?q=tipo+reducido+iva")
        await c.get("/status")
        await c.get("/v1/sources/freshness")
        r = await c.get("/v1/observability/alerts")

    assert r.status_code == 200
    data = r.json()
    assert "alerts" in data
    assert "summary" in data
    assert data["summary"]["warning"] >= 1
    assert any(alert["domain"] == "workers" for alert in data["alerts"])
    assert any(alert["domain"] == "sources" for alert in data["alerts"])


@pytest.mark.asyncio
async def test_openapi_includes_modelo_fuentes_oficiales_endpoint():
    async with _client() as c:
        r = await c.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "/v1/modelos/{codigo}/fuentes-oficiales" in data["paths"]
    assert "/v1/modelos/{codigo}/artefactos" in data["paths"]
    assert "/v1/modelos/campanas-operativas" in data["paths"]
    assert "/v1/modelos/{codigo}/campana-operativa" in data["paths"]
    assert "/v1/modelos/{codigo}/resumen-operativo" in data["paths"]


@pytest.mark.asyncio
async def test_openapi_marks_new_modelos_surfaces_as_beta():
    async with _client() as c:
        r = await c.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()

    beta_paths = [
        "/v1/modelos/{codigo}/fuentes-oficiales",
        "/v1/modelos/{codigo}/artefactos",
        "/v1/modelos/campanas-operativas",
        "/v1/modelos/{codigo}/campana-operativa",
        "/v1/modelos/{codigo}/resumen-operativo",
    ]

    for path in beta_paths:
        assert data["paths"][path]["get"]["x-beta"] is True


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
        "worker-bdns",
        "cron-bdns-weekly",
        "worker-borme",
        "cron-borme-weekly",
        "worker-cnmv",
        "cron-cnmv-weekly",
        "worker-sepblac",
        "cron-sepblac-weekly",
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
async def test_metrics_expone_staleness_y_lag_de_workers():
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
                ) VALUES (
                    'worker-dgt', '2026-04-11T10:00:00+00:00', '2026-04-11T10:05:00+00:00', 'ok',
                    0, 0,
                    12, 9, 7,
                    NULL
                )
                """
            )
        )

    async with _client() as c:
        status = await c.get("/status")
        metrics = await c.get("/metrics")

    assert status.status_code == 200
    assert metrics.status_code == 200
    body = metrics.text
    assert 'worker_stale_status{worker="worker-dgt"}' in body
    assert 'worker_lag_seconds{worker="worker-dgt"}' in body


@pytest.mark.asyncio
async def test_status_expone_bloque_modelos():
    async with _client() as c:
        r = await c.get("/status")
    assert r.status_code == 200
    data = r.json()
    assert "modelos" in data
    assert "campanas_activas" in data["modelos"]
    assert "ultima_actualizacion" in data["modelos"]
    assert data["modelos"]["estado"] in {"ok", "sin_datos"}


@pytest.mark.asyncio
async def test_status_expone_bloque_fuentes():
    async with _client() as c:
        r = await c.get("/status")
    assert r.status_code == 200
    data = r.json()
    assert "fuentes" in data
    assert "total" in data["fuentes"]
    assert "stale" in data["fuentes"]
    assert data["fuentes"]["total"] >= 1


@pytest.mark.asyncio
async def test_source_manifest_lista_fuentes_con_owner_y_trust_tier():
    async with _client() as c:
        r = await c.get("/v1/sources/manifest")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    fuente = data["sources"][0]
    assert "source_id" in fuente
    assert "owner" in fuente
    assert "trust_tier" in fuente
    assert "cadencia" in fuente
    assert "modo_deteccion_cambios" in fuente


@pytest.mark.asyncio
async def test_source_manifest_expone_freshness_ledger():
    async with _client() as c:
        r = await c.get("/v1/sources/freshness")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    fuente = data["sources"][0]
    assert "source_id" in fuente
    assert "last_success_at" in fuente
    assert "stale" in fuente
    assert "last_status" in fuente
    assert "snapshot_at" in fuente
    assert "snapshot_version" in fuente


@pytest.mark.asyncio
async def test_source_manifest_persiste_snapshot_durable_por_fuente():
    from conftest import engine

    async with _client() as c:
        r = await c.get("/v1/sources/freshness")

    assert r.status_code == 200
    payload = r.json()
    assert payload["total"] >= 1

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT source_id, snapshot_version, snapshot_at
                FROM source_freshness_snapshot
                ORDER BY source_id ASC, snapshot_at DESC
                """
            )
        ).mappings().all()

    assert len(rows) >= payload["total"]
    assert rows[0]["source_id"]
    assert rows[0]["snapshot_version"] == "v1"
    assert rows[0]["snapshot_at"] is not None


@pytest.mark.asyncio
async def test_source_manifest_detecta_cambio_frente_a_snapshot_anterior():
    from conftest import engine

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM source_freshness_snapshot WHERE source_id = 'cnmv'"))
        conn.execute(
            text(
                """
                INSERT INTO source_freshness_snapshot (
                    snapshot_id,
                    source_id,
                    snapshot_version,
                    snapshot_at,
                    last_success_at,
                    last_status,
                    stale,
                    cadencia,
                    modo_deteccion_cambios,
                    manifest_hash,
                    payload
                ) VALUES (
                    'snap-prev-cnmv',
                    'cnmv',
                    'v1',
                    '2026-04-26T10:00:00+00:00',
                    NULL,
                    'never_run',
                    1,
                    'weekly',
                    'sha256',
                    :manifest_hash,
                    :payload
                )
                """
            ),
            {
                "manifest_hash": "manifest-prev",
                "payload": '{"last_status":"never_run","stale":true}',
            },
        )

    async with _client() as c:
        r = await c.get("/v1/sources/freshness")

    assert r.status_code == 200
    data = r.json()
    cnmv = next(source for source in data["sources"] if source["source_id"] == "cnmv")
    assert cnmv["previous_snapshot_at"] == "2026-04-26T10:00:00+00:00"
    assert isinstance(cnmv["changed_since_previous"], bool)
    assert cnmv["changed_since_previous"] is True


@pytest.mark.asyncio
async def test_metrics_expone_freshness_por_fuente():
    async with _client() as c:
        freshness = await c.get("/v1/sources/freshness")
        metrics = await c.get("/metrics")

    assert freshness.status_code == 200
    assert metrics.status_code == 200
    body = metrics.text
    assert 'source_freshness_stale_status{source_id="cnmv"}' in body
    assert 'source_freshness_changed_since_previous{source_id="cnmv"}' in body


@pytest.mark.asyncio
async def test_connectivity_articulo_expone_conexiones_cross_source():
    async with _client() as c:
        r = await c.get("/v1/connectivity/articulos/LIVA/91")

    assert r.status_code == 200
    data = r.json()

    assert data["articulo"]["norma"] == "LIVA"
    assert data["articulo"]["numero"] == "91"
    assert data["totales"]["modelos"] >= 1
    assert data["totales"]["doctrina"] >= 1
    assert data["totales"]["obligaciones"] >= 1
    assert any(item["codigo"] == "100" for item in data["modelos"])
    assert any(item["referencia"] == "V0000-26" for item in data["doctrina"])
    assert any(item["codigo"] == "IRNR_FACTA" for item in data["obligaciones"])


@pytest.mark.asyncio
async def test_connectivity_articulo_irnr_expone_modelos_y_obligaciones():
    async with _client() as c:
        r = await c.get("/v1/connectivity/articulos/IRNR/14")

    assert r.status_code == 200
    data = r.json()

    codigos = {item["codigo"] for item in data["modelos"]}
    assert {"124", "216", "296"}.issubset(codigos)
    assert data["totales"]["obligaciones"] == 0


@pytest.mark.asyncio
async def test_connectivity_articulo_inexistente_devuelve_404():
    async with _client() as c:
        r = await c.get("/v1/connectivity/articulos/LIVA/9999")

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_connectivity_documento_expone_articulos_y_obligaciones():
    async with _client() as c:
        r = await c.get("/v1/connectivity/documentos/V0000-26")

    assert r.status_code == 200
    data = r.json()

    assert data["documento"]["referencia"] == "V0000-26"
    assert any(item["norma"] == "LIVA" and item["numero"] == "91" for item in data["articulos"])
    assert any(item["codigo"] == "IRNR_FACTA" for item in data["obligaciones"])
    assert data["totales"]["articulos"] >= 1
    assert data["totales"]["obligaciones"] >= 1


@pytest.mark.asyncio
async def test_connectivity_obligacion_expone_documentos_y_articulos():
    async with _client() as c:
        r = await c.get("/v1/connectivity/obligaciones/IRNR_FACTA")

    assert r.status_code == 200
    data = r.json()

    assert data["obligacion"]["codigo"] == "IRNR_FACTA"
    assert any(item["referencia"] == "V0000-26" for item in data["documentos"])
    assert any(item["norma"] == "LIVA" and item["numero"] == "91" for item in data["articulos"])
    assert data["totales"]["documentos"] >= 1
    assert data["totales"]["articulos"] >= 1


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
async def test_legislacion_expone_irnr_con_clasificacion():
    async with _client() as c:
        lista = await c.get("/v1/legislacion")
        detalle = await c.get("/v1/legislacion/IRNR")
        articulo = await c.get("/v1/legislacion/IRNR/articulos/14")

    assert lista.status_code == 200
    assert detalle.status_code == 200
    assert articulo.status_code == 200

    norma = next(item for item in lista.json()["normas"] if item["codigo"] == "IRNR")
    assert norma["tipo_documento"] == "real_decreto_legislativo"
    assert norma["ambito"] == "tributario"
    assert norma["estado_cobertura"] == "ingestada"

    assert detalle.json()["tipo_documento"] == "real_decreto_legislativo"
    assert detalle.json()["estado_cobertura"] == "ingestada"
    assert (
        "sin mediación de establecimiento permanente"
        in articulo.json()["texto"].lower()
    )


@pytest.mark.asyncio
async def test_legislacion_expone_iiee_con_clasificacion():
    async with _client() as c:
        lista = await c.get("/v1/legislacion")
        detalle = await c.get("/v1/legislacion/IIEE")
        articulo = await c.get("/v1/legislacion/IIEE/articulos/60")

    assert lista.status_code == 200
    assert detalle.status_code == 200
    assert articulo.status_code == 200

    norma = next(item for item in lista.json()["normas"] if item["codigo"] == "IIEE")
    assert norma["tipo_documento"] == "ley"
    assert norma["ambito"] == "tributario"
    assert norma["estado_cobertura"] == "ingestada"
    assert detalle.json()["tipo_documento"] == "ley"
    assert "hidrocarburos" in articulo.json()["texto"].lower()


@pytest.mark.asyncio
async def test_legislacion_expone_hl_con_clasificacion():
    async with _client() as c:
        lista = await c.get("/v1/legislacion")
        detalle = await c.get("/v1/legislacion/HL")
        articulo = await c.get("/v1/legislacion/HL/articulos/20")

    assert lista.status_code == 200
    assert detalle.status_code == 200
    assert articulo.status_code == 200

    norma = next(item for item in lista.json()["normas"] if item["codigo"] == "HL")
    assert norma["tipo_documento"] == "real_decreto_legislativo"
    assert norma["ambito"] == "tributario_local"
    assert norma["estado_cobertura"] == "ingestada"
    assert detalle.json()["tipo_documento"] == "real_decreto_legislativo"
    assert "tasas" in articulo.json()["texto"].lower()


@pytest.mark.asyncio
async def test_legislacion_expone_dac6_espana_y_ue():
    async with _client() as c:
        lista = await c.get("/v1/legislacion")
        dac6 = await c.get("/v1/legislacion/DAC6")
        dac6_articulo = await c.get("/v1/legislacion/DAC6/articulos/206 bis")
        dac6rd = await c.get("/v1/legislacion/DAC6RD")
        dac6eu = await c.get("/v1/legislacion/DAC6EU")

    assert lista.status_code == 200
    assert dac6.status_code == 200
    assert dac6_articulo.status_code == 200
    assert dac6rd.status_code == 200
    assert dac6eu.status_code == 200

    normas = {item["codigo"]: item for item in lista.json()["normas"]}

    assert normas["DAC6"]["tipo_fuente"] == "boe"
    assert normas["DAC6"]["ambito"] == "tributario_internacional"
    assert normas["DAC6"]["estado_cobertura"] == "ingestada"

    assert dac6.json()["tipo_documento"] == "ley"
    assert "mecanismos transfronterizos" in dac6_articulo.json()["texto"].lower()
    assert dac6rd.json()["tipo_documento"] == "real_decreto"
    assert dac6rd.json()["ambito"] == "tributario_internacional"

    assert dac6eu.json()["jurisdiccion"] == "ue"
    assert dac6eu.json()["tipo_fuente"] == "eurlex"
    assert dac6eu.json()["tipo_documento"] == "directiva_ue"
    assert dac6eu.json()["estado_cobertura"] == "referenciada"


@pytest.mark.asyncio
async def test_modelo_fuentes_oficiales_expone_aeat_y_boe():
    async with _client() as c:
        r = await c.get("/v1/modelos/100/fuentes-oficiales")

    assert r.status_code == 200
    data = r.json()

    assert data["codigo"] == "100"
    assert data["campana_activa"] == "2025"
    assert len(data["fuentes_oficiales"]) >= 3
    assert any(
        item["tipo"] == "aeat_modelo"
        and item["url"] == "https://sede.agenciatributaria.gob.es/modelo-100"
        for item in data["fuentes_oficiales"]
    )
    assert any(
        item["tipo"] == "aeat_instrucciones"
        and item["campana"] == "2025"
        for item in data["fuentes_oficiales"]
    )
    assert any(
        item["tipo"] == "boe"
        and item["boe_id"] == "BOE-A-2024-26789"
        for item in data["fuentes_oficiales"]
    )
    assert "fuente maestra" in data["criterio_uso"].lower()


@pytest.mark.asyncio
async def test_modelo_artefactos_expone_superficie_tecnica_de_campana():
    async with _client() as c:
        r = await c.get("/v1/modelos/100/artefactos")

    assert r.status_code == 200
    data = r.json()

    assert data["codigo"] == "100"
    assert data["campana_activa"] == "2025"
    assert any(
        item["tipo"] == "instrucciones"
        and item["url"] == "https://sede.agenciatributaria.gob.es/modelo-100-instrucciones"
        for item in data["artefactos"]
    )
    assert any(
        item["tipo"] == "normativa_campana"
        and item["url"] == "https://sede.agenciatributaria.gob.es/modelo-100-normativa"
        for item in data["artefactos"]
    )
    assert any(
        item["tipo"] == "formato"
        and item["url"] == "https://sede.agenciatributaria.gob.es/modelo-100-formato"
        for item in data["artefactos"]
    )
    assert any(
        item["tipo"] == "boe_modelo"
        and item["boe_id"] == "BOE-A-2024-26789"
        for item in data["artefactos"]
    )
    assert "validacion local" in data["criterio_validacion"].lower()


@pytest.mark.asyncio
async def test_modelo_resumen_operativo_expone_quien_debe_y_plazo():
    async with _client() as c:
        r = await c.get("/v1/modelos/100/resumen-operativo")

    assert r.status_code == 200
    data = r.json()

    assert data["codigo"] == "100"
    assert data["campana_activa"] == "2025"
    assert data["periodo"] == "anual"
    assert data["impuesto"] == "IRPF"
    assert "obligados a declarar" in data["quien_debe_presentarlo"].lower()
    assert "campana de renta" in data["plazo_presentacion"].lower()
    assert any(
        item["tipo"] == "aeat_instrucciones"
        for item in data["fuentes_recomendadas"]
    )


@pytest.mark.asyncio
async def test_modelo_resumen_operativo_no_usa_seccion_presentacion_como_plazo():
    from conftest import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM modelo_instruccion
                WHERE campana_id = (
                    SELECT mc.id
                    FROM modelo_campana mc
                    JOIN aeat_modelo m ON m.id = mc.modelo_id
                    WHERE m.codigo = '100' AND mc.campana = '2025'
                )
                AND seccion IN ('plazo', 'quien-debe')
                """
            )
        )
        conn.execute(
            text(
                """
                DELETE FROM modelo_instruccion
                WHERE campana_id = (
                    SELECT mc.id
                    FROM modelo_campana mc
                    JOIN aeat_modelo m ON m.id = mc.modelo_id
                    WHERE m.codigo = '100' AND mc.campana = '2025'
                )
                AND seccion = 'presentacion'
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
                SELECT mc.id,
                       'presentacion',
                       'Presentacion del modelo 100',
                       'La presentacion del modelo 100 se realiza exclusivamente por via electronica o por los canales habilitados por AEAT.',
                       99
                FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = '100' AND mc.campana = '2025'
                """
            )
        )

    async with _client() as c:
        r = await c.get("/v1/modelos/100/resumen-operativo")

    assert r.status_code == 200
    data = r.json()

    assert "ficha aeat del modelo 100" in data["plazo_presentacion"].lower()


@pytest.mark.asyncio
async def test_modelo_campana_operativa_expone_obligados_plazo_y_presentacion():
    async with _client() as c:
        r = await c.get("/v1/modelos/216/campana-operativa")

    assert r.status_code == 200
    data = r.json()

    assert data["codigo"] == "216"
    assert data["campana"] == "2025"
    assert data["periodo"] == "mensual"
    assert data["impuesto"] == "IRNR"
    assert data["frecuencia_presentacion"] == "mensual"
    assert data["canal_presentacion"] == "electronica"
    assert data["categoria_obligado"] == "retenedor_irnr"
    assert data["ventana_presentacion"] == "primeros_20_dias_mes_siguiente"
    assert data["norma_base"] == "IRNR art. 14"
    assert data["origen_metadato"] == "seed_curado"
    assert data["estado_metadato"] == "curado"
    assert "obligados a practicar retenciones" in data["obligados_resumen"].lower()
    assert "primeros veinte dias naturales" in data["plazo_resumen"].lower()
    assert "via electronica" in data["presentacion_resumen"].lower()
    assert any(
        item["tipo"] == "aeat_instrucciones"
        for item in data["fuentes_recomendadas"]
    )


@pytest.mark.asyncio
async def test_modelo_campana_operativa_usa_seccion_presentacion_como_fallback_sin_metadata_curada():
    from conftest import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM modelo_campana_operativa
                WHERE campana_id = (
                    SELECT mc.id
                    FROM modelo_campana mc
                    JOIN aeat_modelo m ON m.id = mc.modelo_id
                    WHERE m.codigo = '216' AND mc.campana = '2025'
                )
                """
            )
        )
        conn.execute(
            text(
                """
                DELETE FROM modelo_instruccion
                WHERE campana_id = (
                    SELECT mc.id
                    FROM modelo_campana mc
                    JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = '216' AND mc.campana = '2025'
                )
                AND seccion IN ('como-presentar', 'plazo')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
                SELECT mc.id,
                       'presentacion',
                       'Presentacion del modelo 216',
                       'La presentacion del modelo 216 se realiza exclusivamente por via electronica en la sede de la AEAT.',
                       3
                FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = '216' AND mc.campana = '2025'
                """
            )
        )

    async with _client() as c:
        r = await c.get("/v1/modelos/216/campana-operativa")

    assert r.status_code == 200
    data = r.json()

    assert "consultar la sede aeat" in data["plazo_resumen"].lower()
    assert "exclusivamente por via electronica" in data["presentacion_resumen"].lower()


@pytest.mark.asyncio
async def test_modelos_campanas_operativas_agrega_varios_modelos():
    async with _client() as c:
        r = await c.get("/v1/modelos/campanas-operativas?codigos=111,115,124,216,296,303,349,390,036,347")

    assert r.status_code == 200
    data = r.json()

    assert [item["codigo"] for item in data["modelos"]] == ["111", "115", "124", "216", "296", "303", "349", "390", "036", "347"]
    modelo_111 = next(item for item in data["modelos"] if item["codigo"] == "111")
    assert modelo_111["categoria_obligado"] == "retenedor_irpf"
    assert modelo_111["frecuencia_presentacion"] == "trimestral"
    modelo_303 = next(item for item in data["modelos"] if item["codigo"] == "303")
    assert modelo_303["campana"] == "2025"
    assert modelo_303["periodo"] == "trimestral"
    assert modelo_303["frecuencia_presentacion"] == "trimestral"
    assert modelo_303["canal_presentacion"] == "electronica"
    assert modelo_303["categoria_obligado"] == "empresario_o_profesional_iva"
    assert modelo_303["norma_base"] == "LIVA art. 71"
    assert modelo_303["estado_metadato"] == "curado"
    assert "autoliquidar el iva" in modelo_303["obligados_resumen"].lower()
    assert "plazos generales" in modelo_303["plazo_resumen"].lower()
    modelo_036 = next(item for item in data["modelos"] if item["codigo"] == "036")
    assert modelo_036["categoria_obligado"] == "obligado_censal"
    assert modelo_036["ventana_presentacion"] == "1_mes_desde_hecho"


@pytest.mark.asyncio
async def test_modelos_campanas_operativas_deduplica_y_descarta_codigos_desconocidos():
    async with _client() as c:
        r = await c.get(
            "/v1/modelos/campanas-operativas?codigos=303,303,XYZ_INEXISTENTE,216,,216"
        )

    assert r.status_code == 200
    data = r.json()
    codigos = [item["codigo"] for item in data["modelos"]]

    assert codigos == ["303", "216"]


# TODO: test fuentes-oficiales partial payload when there is no active campaign; see apps/api/services/modelos.py:327
# TODO: test artefactos with missing url_formato or url_normativa; see apps/api/services/modelos.py:445
# TODO: test fallback schema without origen_metadato/estado_metadato in get_modelo_campana_operativa_row; see apps/api/services/modelos.py:60
# TODO: test _infer_* helpers with None or unrecognized inputs; see apps/api/services/modelos.py:23,36,47
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
async def test_busqueda_full_text_incluye_source_url_y_motivo_ranking():
    async with _client() as c:
        r = await c.get("/v1/legislacion/buscar?q=tipo+reducido&norma=LIVA")

    assert r.status_code == 200
    data = r.json()
    resultado = data["resultados"][0]

    assert resultado["source_url"] == "https://www.boe.es/diario_boe/txt.php?id=BOE-A-1992-28740"
    assert resultado["fuente_norma"] == "BOE-A-1992-28740"
    assert resultado["motivo_ranking"]


@pytest.mark.asyncio
async def test_doctrina_buscar_por_texto():
    async with _client() as c:
        r = await c.get("/v1/doctrina/buscar?q=tipo+reducido")
    assert r.status_code == 200
    data = r.json()
    assert len(data["resultados"]) >= 1
    assert any(item["referencia"] == "V0000-26" for item in data["resultados"])


@pytest.mark.asyncio
async def test_doctrina_buscar_incluye_source_url():
    async with _client() as c:
        r = await c.get("/v1/doctrina/buscar?q=tipo+reducido")

    assert r.status_code == 200
    data = r.json()
    resultado = next(item for item in data["resultados"] if item["referencia"] == "V0000-26")

    assert resultado["source_url"] == "https://example.invalid/dgt/V0000-26"
    assert resultado["fragmento"]


@pytest.mark.asyncio
async def test_consulta_incluye_evidencia_normativa_estructurada():
    async with _client() as c:
        r = await c.get("/v1/consulta?q=tipo+reducido")

    assert r.status_code == 200
    data = r.json()
    normativa = next(item for item in data["resultados"] if item["tipo"] == "normativa")

    assert normativa["source_url"] == "https://www.boe.es/diario_boe/txt.php?id=BOE-A-1992-28740"
    assert normativa["fuente_norma"] == "BOE-A-1992-28740"
    assert normativa["motivo_ranking"]
    assert normativa["evidencia"]["source_url"] == "https://www.boe.es/diario_boe/txt.php?id=BOE-A-1992-28740"
    assert normativa["evidencia"]["fuente_norma"] == "BOE-A-1992-28740"
    assert normativa["evidencia"]["fragmento_exacto"] == normativa["fragmento"]
    assert normativa["evidencia"]["motivo_ranking"]


@pytest.mark.asyncio
async def test_consulta_incluye_chunk_id_y_source_hash_en_evidencia_normativa():
    async with _client() as c:
        r = await c.get("/v1/consulta?q=tipo+reducido")

    assert r.status_code == 200
    data = r.json()
    normativa = next(item for item in data["resultados"] if item["tipo"] == "normativa")

    assert "chunk_id" in normativa["evidencia"]
    assert normativa["evidencia"]["source_hash"]
    assert len(normativa["evidencia"]["source_hash"]) == 64


@pytest.mark.asyncio
async def test_consulta_respeta_vigente_en_en_resultados_normativos():
    from conftest import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE version_articulo
                SET vigente_hasta = '2010-12-31'
                WHERE articulo_id = (
                    SELECT a.id
                    FROM articulo a
                    JOIN norma n ON n.id = a.norma_id
                    WHERE n.codigo = 'LIVA' AND a.numero = '91'
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
                SELECT a.id,
                       'Artículo 91. Tipos impositivos reducidos. Redacción vigente desde 2011 con referencia expresa al tipo reducido para libros electrónicos.',
                       '2011-01-01',
                       NULL,
                       'a91-2011'
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = 'LIVA' AND a.numero = '91'
                """
            )
        )

    async with _client() as c:
        pasada = await c.get("/v1/consulta?q=tipo+reducido&vigente_en=2010-01-01")
        actual = await c.get("/v1/consulta?q=tipo+reducido&vigente_en=2020-01-01")

    assert pasada.status_code == 200
    assert actual.status_code == 200

    normativa_pasada = next(item for item in pasada.json()["resultados"] if item["tipo"] == "normativa")
    normativa_actual = next(item for item in actual.json()["resultados"] if item["tipo"] == "normativa")

    assert "primera necesidad" in normativa_pasada["texto"].lower()
    assert normativa_pasada["vigente_hasta"] == "2010-12-31"
    assert "libros electrónicos" in normativa_actual["texto"].lower()
    assert normativa_actual["vigente_desde"] == "2011-01-01"


@pytest.mark.asyncio
async def test_bdns_lista_y_detalle():
    async with _client() as c:
        lista = await c.get("/v1/bdns")
        detalle = await c.get("/v1/bdns/BDNS-749075-1034404")
        filtrada = await c.get("/v1/bdns?q=becas")

    assert lista.status_code == 200
    assert detalle.status_code == 200
    assert filtrada.status_code == 200

    referencias = [item["referencia"] for item in lista.json()["convocatorias"]]
    assert "BDNS-749075-1034404" in referencias
    assert "becas" in detalle.json()["texto"].lower()
    assert len(filtrada.json()["convocatorias"]) >= 1


@pytest.mark.asyncio
async def test_cnmv_lista_y_detalle():
    async with _client() as c:
        lista = await c.get("/v1/cnmv")
        detalle = await c.get("/v1/cnmv/BOE-A-2009-133")
        filtrada = await c.get("/v1/cnmv?q=cuentas+anuales&ambito=reporting_financiero")

    assert lista.status_code == 200
    assert detalle.status_code == 200
    assert filtrada.status_code == 200

    referencias = [item["referencia"] for item in lista.json()["documentos"]]
    assert "BOE-A-2009-133" in referencias
    assert detalle.json()["tipo_documento"] == "circular_cnmv"
    assert detalle.json()["ambito"] == "reporting_financiero"
    assert "estados de información reservada" in detalle.json()["texto"].lower()
    assert len(filtrada.json()["documentos"]) >= 1


@pytest.mark.asyncio
async def test_cnmv_obligaciones_endpoint():
    async with _client() as c:
        resp = await c.get("/v1/cnmv/BOE-A-2009-133/obligaciones")

    assert resp.status_code == 200
    data = resp.json()
    assert data["referencia"] == "BOE-A-2009-133"
    assert "obligaciones" in data
    assert "total" in data
    assert isinstance(data["obligaciones"], list)


@pytest.mark.asyncio
async def test_cnmv_filtro_obligacion():
    async with _client() as c:
        lista = await c.get("/v1/cnmv")
        filtrada = await c.get("/v1/cnmv?obligacion=reporting_prudencial")

    assert lista.status_code == 200
    assert filtrada.status_code == 200
    referencias = [item["referencia"] for item in lista.json()["documentos"]]
    filtradas_refs = [item["referencia"] for item in filtrada.json()["documentos"]]
    for ref in filtradas_refs:
        assert ref in referencias


@pytest.mark.asyncio
async def test_sepblac_lista_y_detalle():
    async with _client() as c:
        lista = await c.get("/v1/sepblac")
        detalle = await c.get("/v1/sepblac/SEPBLAC-MODELO-19")
        filtrada = await c.get(
            "/v1/sepblac?q=comunicaci%C3%B3n+por+indicio&ambito=aml_cft_reporting"
        )

    assert lista.status_code == 200
    assert detalle.status_code == 200
    assert filtrada.status_code == 200

    referencias = [item["referencia"] for item in lista.json()["documentos"]]
    assert "SEPBLAC-MODELO-19" in referencias
    assert detalle.json()["tipo_documento"] == "formulario_sepblac"
    assert detalle.json()["ambito"] == "aml_cft_reporting"
    assert "modelo 19" in detalle.json()["texto"].lower()
    assert len(filtrada.json()["documentos"]) >= 1


@pytest.mark.asyncio
async def test_cendoj_lista_y_detalle():
    async with _client() as c:
        lista = await c.get("/v1/cendoj")
        detalle = await c.get("/v1/cendoj/STS-2847/2025")
        filtrada = await c.get("/v1/cendoj?q=tipo+reducido&tribunal=tribunal_supremo")

    assert lista.status_code == 200
    assert detalle.status_code == 200
    assert filtrada.status_code == 200

    referencias = [item["referencia"] for item in lista.json()["documentos"]]
    assert "STS-2847/2025" in referencias
    assert detalle.json()["tipo_documento"] == "sentencia"
    assert detalle.json()["ambito"] == "tributario"
    assert "trib supremo" in detalle.json()["titulo"].lower()
    assert len(filtrada.json()["documentos"]) >= 1


@pytest.mark.asyncio
async def test_eurlex_lista_y_detalle():
    async with _client() as c:
        lista = await c.get("/v1/eurlex")
        filtrada = await c.get("/v1/eurlex?q=reglamento&ambito=mercado_interior")

    assert lista.status_code == 200
    referencias = [item["referencia"] for item in lista.json()["documentos"]]
    assert "EUR-Lex-32020R548" in referencias
    assert len(filtrada.json()["documentos"]) >= 1


@pytest.mark.asyncio
async def test_bde_lista_y_detalle():
    async with _client() as c:
        lista = await c.get("/v1/bde")
        detalle = await c.get("/v1/bde/BDE-IB-2025-01")
        filtrada = await c.get("/v1/bde?q=estabilidad+financiera&ambito=estabilidad_financiera")

    assert lista.status_code == 200
    assert detalle.status_code == 200
    assert filtrada.status_code == 200

    referencias = [item["referencia"] for item in lista.json()["documentos"]]
    assert "BDE-IB-2025-01" in referencias
    assert detalle.json()["tipo_documento"] == "informe_bde"
    assert detalle.json()["ambito"] == "estabilidad_financiera"
    assert "informe bde" in detalle.json()["titulo"].lower()
    assert len(filtrada.json()["documentos"]) >= 1


@pytest.mark.asyncio
async def test_aepd_lista_y_detalle():
    async with _client() as c:
        lista = await c.get("/v1/aepd")
        filtrada = await c.get("/v1/aepd?q=proteccion&ambito=proteccion_datos")

    assert lista.status_code == 200
    referencias = [item["referencia"] for item in lista.json()["documentos"]]
    assert "AEPD-R-2025-1234" in referencias
    assert len(filtrada.json()["documentos"]) >= 1


@pytest.mark.asyncio
async def test_obligaciones_lista_y_detalle():
    async with _client() as c:
        lista = await c.get("/v1/obligaciones")
        cnmv = await c.get("/v1/obligaciones?fuente=cnmv&ambito=reporting_regulatorio")
        detalle = await c.get("/v1/obligaciones/SEPBLAC-INDICIO-M19")

    assert lista.status_code == 200
    assert cnmv.status_code == 200
    assert detalle.status_code == 200

    codigos = [item["codigo"] for item in lista.json()["obligaciones"]]
    assert "CNMV-IR-RESERVADA" in codigos
    assert "SEPBLAC-INDICIO-M19" in codigos
    assert len(cnmv.json()["obligaciones"]) >= 1

    data = detalle.json()
    assert data["fuente"] == "sepblac"
    assert data["reporte_modelo"] == "modelo_19"
    assert data["seccion_origen"] == "15.5"
    assert len(data["documentos"]) >= 1
    assert data["documentos"][0]["referencia"] == "SEPBLAC-MODELO-19"


@pytest.mark.asyncio
async def test_obligaciones_operativas():
    async with _client() as c:
        operativas = await c.get("/v1/obligaciones/operativas")
        deadlines = await c.get("/v1/obligaciones/deadlines")
        detalle_op = await c.get("/v1/obligaciones/SEPBLAC-INDICIO-M19")

    assert operativas.status_code == 200
    assert deadlines.status_code == 200
    assert detalle_op.status_code == 200

    data = operativas.json()
    assert len(data) >= 1
    campos_op = list(data[0].keys())
    assert "plazo_dias" in campos_op
    assert "frecuencia_presentacion" in campos_op
    assert "sancion_min" in campos_op
    assert "sancion_max" in campos_op

    # SEPBLAC-INDICIO-M19 tiene sancion definida
    sepblac = next((o for o in data if o["codigo"] == "SEPBLAC-INDICIO-M19"), None)
    assert sepblac is not None
    assert sepblac["sancion_min"] == 10000
    assert sepblac["sancion_max"] == 6000000
    assert sepblac["plazo_dias"] == 15
    assert sepblac["frecuencia_presentacion"] == "eventual"

    # Deadlines ordena por frecuencia
    dl = deadlines.json()
    assert len(dl) >= 1
    freq_order = [item["frecuencia_presentacion"] for item in dl if item.get("frecuencia_presentacion")]
    if len(set(freq_order)) > 1:
        freq_set = {"mensual": 1, "trimestral": 2, "anual": 3}
        prev = 0
        for f in freq_order:
            cur = freq_set.get(f, 99)
            assert cur >= prev, f"Deadlines no ordenados: {freq_order}"
            prev = cur


@pytest.mark.asyncio
async def test_obligaciones_detalle_campos_operativos():
    async with _client() as c:
        detalle = await c.get("/v1/obligaciones/IRNR_FACTA")

    assert detalle.status_code == 200
    data = detalle.json()
    assert data["plazo_dias"] == 20
    assert data["frecuencia_presentacion"] == "mensual"
    assert data["ventana_presentacion"] == "primeros_20_dias_periodo_siguiente"
    assert data["trigger_presentacion"] == "fin_mes"
    assert data["canal_presentacion"] == "electronica"
    assert data["sancion_min"] == 50
    assert data["sancion_max"] == 150
    assert data["recargo_voluntario"] == "5%"
    assert data["recargo_involuntario"] == "5-10%"
    assert data["interes_demora"] == "TIE + 4%"
    assert data["prescripcion_anos"] == 4
    assert data["origen_metadato"] == "seed_curado"
    assert data["estado_metadato"] == "curado"
    assert len(data["documentos"]) >= 1


@pytest.mark.asyncio
async def test_obligaciones_detalle_incluye_operativa_de_control():
    async with _client() as c:
        detalle = await c.get("/v1/obligaciones/SEPBLAC-INDICIO-M19")

    assert detalle.status_code == 200
    data = detalle.json()
    assert data["evidencia_requerida"] == [
        "acuse_presentacion_modelo_19",
        "expediente_interno_indicio",
        "soporte_revision_compliance",
    ]
    assert data["owner_rol_sugerido"] == "compliance"
    assert data["criticidad"] == "alta"
    assert data["control_interno_sugerido"] == "escalado_indicios_y_validacion"
    assert data["procedimiento_relacionado"] == "procedimiento_comunicacion_indicios_sepblac"


@pytest.mark.asyncio
async def test_obligaciones_filtro_frecuencia():
    async with _client() as c:
        todas = await c.get("/v1/obligaciones")
        mensuales = await c.get("/v1/obligaciones?frecuencia=mensual")
        anuales = await c.get("/v1/obligaciones?frecuencia=anual")

    assert todas.status_code == 200
    assert mensuales.status_code == 200
    assert anuales.status_code == 200

    mensuales_codigos = {o["codigo"] for o in mensuales.json()["obligaciones"]}
    anuales_codigos = {o["codigo"] for o in anuales.json()["obligaciones"]}

    # IRNR_FACTA es mensual
    assert "IRNR_FACTA" in mensuales_codigos
    assert "IRNR_FACTA" not in anuales_codigos
    # IRPF_ANUAL es anual
    assert "IRPF_ANUAL" in anuales_codigos
    assert "IRPF_ANUAL" not in mensuales_codigos


@pytest.mark.asyncio
async def test_borme_lista_y_detalle():
    async with _client() as c:
        lista = await c.get("/v1/borme")
        detalle = await c.get("/v1/borme/BORME-A-2025-55-37")
        filtrada = await c.get("/v1/borme?q=alvarez&tipo=nombramiento")

    assert lista.status_code == 200
    assert detalle.status_code == 200
    assert filtrada.status_code == 200

    referencias = [item["referencia"] for item in lista.json()["actos"]]
    assert "BORME-A-2025-55-37" in referencias
    assert detalle.json()["tipo_documento"] == "nombramiento"
    assert "nombramientos" in detalle.json()["texto"].lower()
    assert len(detalle.json()["empresas_relacionadas"]) >= 2
    assert any(
        item["rol"] == "absorbida" for item in detalle.json()["empresas_relacionadas"]
    )
    assert len(filtrada.json()["actos"]) >= 1


@pytest.mark.asyncio
async def test_empresas_lista_y_detalle():
    async with _client() as c:
        lista = await c.get("/v1/empresas")
        filtrada = await c.get("/v1/empresas?q=alvarez")

    assert lista.status_code == 200
    assert filtrada.status_code == 200

    empresas = lista.json()["empresas"]
    assert len(empresas) >= 1

    empresa = next(
        item for item in empresas if item["nombre"] == "ALVAREZ GARCIA GANADERIA, S.L."
    )
    assert empresa["fuente_inicial"] == "BORME"
    assert empresa["documentos_count"] >= 1

    async with _client() as c:
        detalle = await c.get(f"/v1/empresas/{empresa['id']}")

    assert detalle.status_code == 200
    data = detalle.json()
    assert data["nombre"] == "ALVAREZ GARCIA GANADERIA, S.L."
    assert len(data["documentos"]) >= 1
    assert data["documentos"][0]["organismo_emisor"] == "BORME"
    assert any(item["rol"] == "principal" for item in data["documentos"])


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
    assert len(data["modelos"]) >= 11
    codigos = [m["codigo"] for m in data["modelos"]]
    assert "100" in codigos
    assert "111" in codigos
    assert "115" in codigos
    assert "124" in codigos
    assert "216" in codigos
    assert "296" in codigos
    assert "303" in codigos
    assert "349" in codigos
    assert "390" in codigos
    assert "036" in codigos
    assert "347" in codigos


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


@pytest.mark.asyncio
async def test_modelos_irnr_tienen_relacion_articulo():
    async with _client() as c:
        r124 = await c.get("/v1/modelos/124/articulos")
        r216 = await c.get("/v1/modelos/216/articulos")
        r296 = await c.get("/v1/modelos/296/articulos")

    assert r124.status_code == 200
    assert r216.status_code == 200
    assert r296.status_code == 200

    assert any(item["norma"] == "IRNR" for item in r124.json()["articulos"])
    assert any(item["norma"] == "IRNR" for item in r216.json()["articulos"])
    assert any(item["norma"] == "IRNR" for item in r296.json()["articulos"])


@pytest.mark.asyncio
async def test_modelo_detalle_acepta_campana_explicita():
    from conftest import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones)
                SELECT m.id, '2024', 0, 'https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2024'
                FROM aeat_modelo m WHERE m.codigo = '100'
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, orden)
                SELECT mc.id, '0042', 'Casilla histórica', 'Casilla de la campaña 2024', 'importe', 1
                FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = '100' AND mc.campana = '2024'
                """
            )
        )

    async with _client() as c:
        r = await c.get("/v1/modelos/100?campana=2024")
    assert r.status_code == 200
    data = r.json()
    assert data["campana_activa"] == "2024"
    assert any(casilla["codigo"] == "0042" for casilla in data["casillas"])


@pytest.mark.asyncio
async def test_modelo_casillas_endpoint_acepta_campana_explicita():
    from conftest import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones)
                SELECT m.id, '2023', 0, 'https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2023'
                FROM aeat_modelo m WHERE m.codigo = '100'
                ON CONFLICT DO NOTHING
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, orden)
                SELECT mc.id, '0099', 'Casilla campaña 2023', 'Casilla de validación', 'importe', 1
                FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = '100' AND mc.campana = '2023'
                ON CONFLICT DO NOTHING
                """
            )
        )

    async with _client() as c:
        r = await c.get("/v1/modelos/100/casillas?campana=2023")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "100"
    assert any(casilla["codigo"] == "0099" for casilla in data["casillas"])


@pytest.mark.asyncio
async def test_modelo_instrucciones_endpoint_devuelve_datos_de_campana_activa():
    async with _client() as c:
        r = await c.get("/v1/modelos/100/instrucciones")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "100"
    assert any(item["seccion"] == "caracteristicas" for item in data["instrucciones"])


@pytest.mark.asyncio
async def test_modelo_sin_campana_devuelve_la_activa_mas_nueva():
    from conftest import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE modelo_campana SET activo = 0 WHERE modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = '100')"
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones)
                SELECT m.id, '2026', 1, 'https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2026'
                FROM aeat_modelo m WHERE m.codigo = '100'
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, orden)
                SELECT mc.id, '7777', 'Casilla vigente nueva', 'Casilla de la campaña 2026', 'importe', 1
                FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = '100' AND mc.campana = '2026'
                """
            )
        )

    async with _client() as c:
        r = await c.get("/v1/modelos/100")
    assert r.status_code == 200
    data = r.json()
    assert data["campana_activa"] == "2026"
    assert any(casilla["codigo"] == "7777" for casilla in data["casillas"])


@pytest.mark.asyncio
async def test_consulta_expone_relevancia_y_confianza():
    async with _client() as c:
        r = await c.get("/v1/consulta?q=modelo+100+irpf")

    assert r.status_code == 200
    data = r.json()

    assert "relevancia" in data
    assert "confianza" in data
    assert "cited_chunks" in data

    relevancia = data["relevancia"]
    assert relevancia["nivel"] in {"alta", "media", "baja"}
    assert isinstance(relevancia["score"], float)
    assert relevancia["score"] >= 0.0
    assert relevancia["score"] <= 1.0
    assert isinstance(relevancia["coincidencia"], str) and len(relevancia["coincidencia"]) > 0
    assert isinstance(relevancia["terminos_encontrados"], list)
    assert isinstance(relevancia["terminos_faltantes"], list)

    confianza = data["confianza"]
    assert confianza["nivel"] in {0, 1, 2}
    assert confianza["nivel_texto"] in {"alta", "media", "baja"}
    assert isinstance(confianza["fuentes"], list)
    assert isinstance(confianza["modelos_cubiertos"], list)
    assert isinstance(confianza["resultados_clasificados"], dict)
    assert isinstance(confianza["faithfulness_score"], float)
    assert 0.0 <= confianza["faithfulness_score"] <= 1.0
    assert confianza["faithfulness_label"] in {"alta", "media", "baja"}
    assert isinstance(confianza["review_required"], bool)
    assert isinstance(data["cited_chunks"], list)
    assert len(data["cited_chunks"]) > 0
    citation = data["cited_chunks"][0]
    assert "chunk_id" in citation
    assert "source_document" in citation
    assert "rerank_score" in citation
    assert "excerpt" in citation


@pytest.mark.asyncio
async def test_consulta_relevancia_ordena_resultados_por_score():
    async with _client() as c:
        r = await c.get("/v1/consulta?q=tipo+reducido")

    assert r.status_code == 200
    data = r.json()

    scores = [r["_relevancia"]["score"] for r in data["resultados"]]
    assert scores == sorted(scores, reverse=True)

    if scores:
        assert scores[0] >= scores[-1]


@pytest.mark.asyncio
async def test_consulta_confianza_baja_consulta_vacia():
    async with _client() as c:
        r = await c.get("/v1/consulta")

    assert r.status_code == 200
    data = r.json()

    confianza = data["confianza"]
    assert confianza["nivel"] == 0
    assert confianza["nivel_texto"] == "baja"
    assert confianza["faithfulness_score"] == 0.0
    assert confianza["faithfulness_label"] == "baja"
    assert confianza["review_required"] is True
    assert "consulta vacia" in (confianza["aviso"] or "").lower()


@pytest.mark.asyncio
async def test_consulta_baja_confianza_abstiene_y_expone_disclaimer():
    async with _client() as c:
        r = await c.get("/v1/consulta?q=zzzxxyyqqq")

    assert r.status_code == 200
    assert "X-AI-Disclaimer" in r.headers
    data = r.json()
    confianza = data["confianza"]
    assert confianza["faithfulness_score"] < 0.5
    assert confianza["review_required"] is True
    assert data["resultados"] == []
    assert data["cited_chunks"] == []
    assert "evidencia insuficiente" in (confianza["aviso"] or "").lower()


@pytest.mark.asyncio
async def test_consulta_confianza_alta_no_requiere_revision_humana():
    async with _client() as c:
        r = await c.get("/v1/consulta?q=tipo+reducido+iva")

    assert r.status_code == 200
    confianza = r.json()["confianza"]

    assert confianza["faithfulness_score"] > 0.5
    assert confianza["review_required"] is False


@pytest.mark.asyncio
async def test_consulta_resultados_tienen_relevancia_interna():
    async with _client() as c:
        r = await c.get("/v1/consulta?q=modelo+100+irpf")

    assert r.status_code == 200
    data = r.json()

    for resultado in data["resultados"]:
        assert "_relevancia" in resultado
        rev = resultado["_relevancia"]
        assert rev["nivel"] in {"alta", "media", "baja"}
        assert isinstance(rev["score"], float)
        assert isinstance(rev["coincidencia"], str)
        assert isinstance(rev["terminos_encontrados"], list)
        assert isinstance(rev["terminos_faltantes"], list)


@pytest.mark.asyncio
async def test_fairness_report_endpoint_returns_report():
    async with _client() as c:
        r = await c.get("/v1/ai/fairness-report")

    assert r.status_code == 200
    data = r.json()
    assert "report" in data
    assert "results_evaluated" in data
    assert data["results_evaluated"] >= 0
    report = data["report"]
    assert "biases" in report
    assert "overall_severity" in report
    assert "bias_detected" in report
    assert "recommendations" in report


@pytest.mark.asyncio
async def test_fairness_report_with_query():
    async with _client() as c:
        r = await c.get("/v1/ai/fairness-report?q=IRPF")

    assert r.status_code == 200
    data = r.json()
    assert data["query"] == "IRPF"
    assert "report" in data
    assert len(data["report"]["biases"]) == 3


@pytest.mark.asyncio
async def test_fairness_report_disabled():
    async with _client() as c:
        r = await c.get("/v1/ai/fairness-report?enabled=false")

    assert r.status_code == 200
    data = r.json()
    assert data["report"]["overall_severity"] == "skipped"
    assert data["report"]["bias_detected"] is False


@pytest.mark.asyncio
async def test_consulta_expone_claim_citations():
    async with _client() as c:
        r = await c.get("/v1/consulta?q=tipo+reducido+iva")

    assert r.status_code == 200
    data = r.json()

    assert "claim_citations" in data
    assert isinstance(data["claim_citations"], list)

    if data["claim_citations"]:
        first = data["claim_citations"][0]
        assert "claim" in first
        assert "citations" in first
        assert isinstance(first["citations"], list)
        assert len(first["citations"]) > 0
        citation = first["citations"][0]
        assert "chunk_id" in citation
        assert "source_document" in citation
        assert "rerank_score" in citation
        assert "excerpt" in citation


@pytest.mark.asyncio
async def test_consulta_claim_citations_mapea_por_chunk_id():
    async with _client() as c:
        r = await c.get("/v1/consulta?q=deduccion+gastos+representacion+is")

    assert r.status_code == 200
    data = r.json()

    if data["claim_citations"]:
        for claim_entry in data["claim_citations"]:
            claim = claim_entry["claim"]
            assert claim.get("tipo") in ("normativa", "modelo", "obligacion", "doctrina")
            for cit in claim_entry["citations"]:
                assert cit["chunk_id"] is not None
                assert cit["rerank_score"] is not None
                assert len(cit["excerpt"]) > 0
                if cit["chunk_id"] == claim_entry["citations"][0]["chunk_id"]:
                    continue


@pytest.mark.asyncio
async def test_consulta_claim_citations_semantic_scoring():
    async with _client() as c:
        r = await c.get("/v1/consulta?q=deduccion+gastos+representacion+is")

    assert r.status_code == 200
    data = r.json()

    if data["claim_citations"]:
        for claim_entry in data["claim_citations"]:
            citations = claim_entry["citations"]
            if len(citations) >= 2:
                scores = [c["rerank_score"] for c in citations]
                assert scores == sorted(scores, reverse=True), "citations should be sorted by rerank_score desc"
