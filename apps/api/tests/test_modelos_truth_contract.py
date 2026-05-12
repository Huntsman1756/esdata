"""Truth contract tests for AEAT modelos responses."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


def _seed_sociedad_valores_modelos():
    from db import engine

    rows = [
        (
            "123",
            "Retenciones e ingresos a cuenta. Determinados rendimientos del capital mobiliario",
            "trimestral",
            "IRPF",
        ),
        (
            "124",
            "Retenciones e ingresos a cuenta. Rentas y rendimientos del capital mobiliario derivados de la transmision de activos",
            "trimestral",
            "IRPF",
        ),
        (
            "193",
            "Declaracion informativa. Retenciones e ingresos a cuenta del IRPF sobre determinados rendimientos del capital mobiliario",
            "anual",
            "IRPF",
        ),
        (
            "216",
            "IRNR. Retenciones e ingresos a cuenta sobre rentas obtenidas sin mediacion de establecimiento permanente",
            "trimestral",
            "IRNR",
        ),
        (
            "296",
            "Declaracion informativa. Retenciones e ingresos a cuenta del Impuesto sobre la Renta de no Residentes",
            "anual",
            "IRNR",
        ),
    ]
    with engine.begin() as conn:
        for codigo, nombre, periodo, impuesto in rows:
            conn.execute(
                text(
                    """
                    INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info)
                    VALUES (:codigo, :nombre, :periodo, :impuesto, :url_info)
                    ON CONFLICT(codigo) DO UPDATE SET
                        nombre = excluded.nombre,
                        periodo = excluded.periodo,
                        impuesto = excluded.impuesto,
                        url_info = excluded.url_info
                    """
                ),
                {
                    "codigo": codigo,
                    "nombre": nombre,
                    "periodo": periodo,
                    "impuesto": impuesto,
                    "url_info": f"https://sede.agenciatributaria.gob.es/modelo-{codigo}",
                },
            )


def _cleanup_sociedad_valores_modelos():
    from db import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM aeat_modelo
                WHERE codigo IN ('123', '124', '193', '216', '296')
                """
            )
        )


@pytest.mark.asyncio
async def test_modelo_detail_marks_partial_when_campaign_lacks_official_instructions():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/303")

    assert response.status_code == 200
    data = response.json()

    assert data["codigo"] == "303"
    assert data["instrucciones"] == []
    assert data["casillas"] == []
    assert data["completeness"] == "parcial"
    assert data["verified"] is False


@pytest.mark.asyncio
async def test_modelo_campana_operativa_marks_partial_when_runtime_is_inferred():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/303/campana-operativa")

    assert response.status_code == 200
    data = response.json()

    assert data["codigo"] == "303"
    assert data["estado_metadato"] in (None, "inferido")
    assert data["completeness"] == "parcial"
    assert data["verified"] is False


@pytest.mark.asyncio
async def test_modelo_detail_keeps_strong_article_visible_for_model_100():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/100")

    assert response.status_code == 200
    data = response.json()

    assert data["codigo"] == "100"
    assert {"norma": "LIVA", "numero": "91"} in [
        {"norma": articulo["norma"], "numero": articulo["numero"]}
        for articulo in data["articulos"]
    ]
    assert any(
        articulo["norma"] == "LIVA"
        and articulo["numero"] == "91"
        and articulo["fuente"] == "Instrucciones Modelo 100 2025"
        for articulo in data["articulos"]
    )


@pytest.mark.asyncio
async def test_modelo_detail_hides_legacy_article_for_model_303():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/303")

    assert response.status_code == 200
    data = response.json()

    assert data["codigo"] == "303"
    assert data["articulos"] == []


@pytest.mark.asyncio
async def test_modelos_list_reports_zero_articulos_for_model_303_when_only_legacy_rows_exist():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos")

    assert response.status_code == 200
    data = response.json()

    modelo_303 = next(modelo for modelo in data["modelos"] if modelo["codigo"] == "303")
    assert modelo_303["articulos_count"] == 0


@pytest.mark.asyncio
async def test_modelo_detail_matches_campana_operativa_truth_contract_for_model_100():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        detail_response = await client.get("/v1/modelos/100")
        operativa_response = await client.get("/v1/modelos/100/campana-operativa")

    assert detail_response.status_code == 200
    assert operativa_response.status_code == 200

    detail_data = detail_response.json()
    operativa_data = operativa_response.json()

    assert operativa_data["estado_metadato"] is None
    assert operativa_data["completeness"] == "parcial"
    assert operativa_data["verified"] is False
    assert detail_data["completeness"] == operativa_data["completeness"]
    assert detail_data["verified"] == operativa_data["verified"]


@pytest.mark.asyncio
async def test_modelo_fuentes_oficiales_keeps_partial_truth_contract_for_model_100():
    request_id = "req-modelo-fuentes-100"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-secret-key",
            "x-request-id": request_id,
            "x-user-id": "test-user",
        },
    ) as client:
        response = await client.get("/v1/modelos/100/fuentes-oficiales")

    assert response.status_code == 200

    from services.query_audit import QueryAuditService

    entries = QueryAuditService().get_by_request_id(request_id)
    assert len(entries) == 1
    assert entries[0].tool_name == "get_modelo_fuentes_oficiales"
    assert entries[0].completeness == "parcial"
    assert entries[0].verified is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "tool_name"),
    [
        ("/v1/modelos/100/casillas", "get_modelo_casillas"),
        ("/v1/modelos/100/claves", "get_modelo_claves"),
        ("/v1/modelos/100/instrucciones", "get_modelo_instrucciones"),
    ],
)
async def test_modelo_subendpoints_keep_partial_truth_contract_for_model_100(
    path: str, tool_name: str
):
    request_id = f"req-{tool_name}-100"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "x-api-key": "test-secret-key",
            "x-request-id": request_id,
            "x-user-id": "test-user",
        },
    ) as client:
        response = await client.get(path)

    assert response.status_code == 200

    from services.query_audit import QueryAuditService

    entries = QueryAuditService().get_by_request_id(request_id)
    assert len(entries) == 1
    assert entries[0].tool_name == tool_name
    assert entries[0].completeness == "parcial"
    assert entries[0].verified is False


@pytest.mark.asyncio
async def test_modelos_por_supuesto_sociedad_valores_fail_closed_without_explicit_obligation():
    _cleanup_sociedad_valores_modelos()
    _seed_sociedad_valores_modelos()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"x-api-key": "test-secret-key"},
        ) as client:
            response = await client.get(
                "/v1/modelos/por-supuesto",
                params={
                    "tipo_entidad": "sociedad_valores",
                    "clientes_residentes": True,
                    "clientes_no_residentes": True,
                    "tipo_renta": "capital_mobiliario",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "evidence_limited"
        assert data["verified"] is False
        assert data["confidence"]["review_required"] is True
        assert all(item["clasificacion"] != "confirmado" for item in data["modelos"])

        by_codigo = {item["codigo"]: item for item in data["modelos"]}
        assert by_codigo["123"]["clasificacion"] == "candidato"
        assert by_codigo["124"]["clasificacion"] == "candidato"
        assert by_codigo["193"]["clasificacion"] == "candidato"
        assert by_codigo["216"]["clasificacion"] == "candidato"
        assert by_codigo["296"]["clasificacion"] == "candidato"
        assert by_codigo["216"]["condicion_aplicacion"]
        assert by_codigo["296"]["evidencia"][0]["source"] == "aeat_modelo"

        excluded = {item["codigo"]: item["reason"] for item in data["excluded_modelos"]}
        assert "100" in excluded
        assert "111" in excluded
        assert "115" in excluded
        assert "190" in excluded
    finally:
        _cleanup_sociedad_valores_modelos()


@pytest.mark.asyncio
async def test_modelos_por_supuesto_is_exposed_in_http_mcp_catalog():
    from mcp_catalog import HTTP_MCP_OPERATIONS, get_stdio_tool_definitions

    assert "list_modelos_por_supuesto" in HTTP_MCP_OPERATIONS
    assert any(tool["name"] == "list_modelos_por_supuesto" for tool in get_stdio_tool_definitions())


def test_compute_confianza_does_not_cover_unreturned_resolved_model():
    from routers.consulta import _compute_confianza

    confianza = _compute_confianza(
        modelos=[],
        resultados=[],
        q="sociedad de valores con clientes no residentes",
        resolved_modelos=["200"],
    )

    assert confianza["nivel"] == 0
    assert confianza["nivel_texto"] == "baja"
    assert confianza["modelos_cubiertos"] == []
    assert "modelo_200" not in confianza["fuentes"]
    assert confianza["review_required"] is True


def test_score_resultado_without_direct_terms_stays_low_even_with_rank():
    from routers.consulta import _score_resultado

    scored = _score_resultado(
        {
            "tipo": "modelo",
            "codigo": "999",
            "nombre": "Declaracion sin relacion con la consulta",
            "rank": 5,
        },
        "wallet custodian mica",
        [],
    )

    assert scored["_relevancia"]["terminos_encontrados"] == []
    assert scored["_relevancia"]["nivel"] == "baja"
    assert scored["_relevancia"]["score"] < 0.3


def _seed_many_modelo_100_casillas(total: int = 12):
    from db import engine

    with engine.begin() as conn:
        campana_id = conn.execute(
            text(
                """
                SELECT mc.id
                FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = '100' AND mc.campana = '2025'
                """
            )
        ).scalar_one()
        for value in range(1, total + 1):
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_casilla
                        (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
                    VALUES
                        (:campana_id, :codigo, :etiqueta, :descripcion, 'importe', 2, :orden)
                    ON CONFLICT(campana_id, codigo) DO UPDATE SET
                        etiqueta = excluded.etiqueta,
                        descripcion = excluded.descripcion,
                        tipo_casilla = excluded.tipo_casilla,
                        pagina = excluded.pagina,
                        orden = excluded.orden,
                        activa = 1
                    """
                ),
                {
                    "campana_id": campana_id,
                    "codigo": f"T{value:03d}",
                    "etiqueta": f"Casilla test {value}",
                    "descripcion": f"Descripcion test {value}",
                    "orden": 1000 + value,
                },
            )


def _seed_modelo_with_empty_active_campaign_and_historical_casillas(codigo: str = "290"):
    from db import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info)
                VALUES (
                    :codigo,
                    'Modelo 290. Declaracion informativa anual de cuentas financieras FATCA',
                    'anual',
                    'INFORMATIVO',
                    'https://sede.agenciatributaria.gob.es/modelo-290'
                )
                ON CONFLICT(codigo) DO UPDATE SET
                    nombre = excluded.nombre,
                    periodo = excluded.periodo,
                    impuesto = excluded.impuesto,
                    url_info = excluded.url_info,
                    activo = 1
                """
            ),
            {"codigo": codigo},
        )
        conn.execute(
            text(
                """
                INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones)
                SELECT id, '2013', 1, 'https://sede.agenciatributaria.gob.es/modelo-290-2013'
                FROM aeat_modelo
                WHERE codigo = :codigo
                ON CONFLICT(modelo_id, campana) DO UPDATE SET
                    activo = 1,
                    url_instrucciones = excluded.url_instrucciones
                """
            ),
            {"codigo": codigo},
        )
        conn.execute(
            text(
                """
                INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones)
                SELECT id, '2025', 0, 'https://sede.agenciatributaria.gob.es/modelo-290-2025'
                FROM aeat_modelo
                WHERE codigo = :codigo
                ON CONFLICT(modelo_id, campana) DO UPDATE SET
                    activo = 0,
                    url_instrucciones = excluded.url_instrucciones
                """
            ),
            {"codigo": codigo},
        )
        campana_id = conn.execute(
            text(
                """
                SELECT mc.id
                FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = :codigo AND mc.campana = '2025'
                """
            ),
            {"codigo": codigo},
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO modelo_casilla
                    (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
                VALUES
                    (:campana_id, 'DR:1:1', 'NIF entidad declarante', 'Campo oficial de diseno de registro', 'diseno_registro_campo', 1, 1)
                ON CONFLICT(campana_id, codigo) DO UPDATE SET
                    etiqueta = excluded.etiqueta,
                    descripcion = excluded.descripcion,
                    tipo_casilla = excluded.tipo_casilla,
                    pagina = excluded.pagina,
                    orden = excluded.orden,
                    activa = 1
                """
            ),
            {"campana_id": campana_id},
        )


@pytest.mark.asyncio
async def test_modelo_100_casillas_are_paginated_and_truth_labeled():
    _seed_many_modelo_100_casillas(12)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/100/casillas", params={"limit": 5, "offset": 0})

    assert response.status_code == 200
    data = response.json()

    assert data["codigo"] == "100"
    assert len(data["casillas"]) == 5
    assert data["total"] >= 13
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert data["has_more"] is True
    assert data["next_offset"] == 5
    assert data["classification"] == "confirmado"
    assert data["verified"] is False
    assert data["confidence"]["review_required"] is True
    assert "No implican" in data["obligation_notice"]


@pytest.mark.asyncio
async def test_modelo_detail_limits_embedded_casillas_for_agent_clients():
    _seed_many_modelo_100_casillas(12)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get(
            "/v1/modelos/100",
            params={"casillas_limit": 5, "casillas_offset": 0},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["codigo"] == "100"
    assert len(data["casillas"]) == 5
    assert data["casillas_total"] >= 13
    assert data["casillas_limit"] == 5
    assert data["casillas_offset"] == 0
    assert data["casillas_has_more"] is True
    assert data["casillas_next_offset"] == 5


@pytest.mark.asyncio
async def test_modelo_100_casillas_support_filtering():
    _seed_many_modelo_100_casillas(12)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get(
            "/v1/modelos/100/casillas",
            params={"limit": 20, "q": "Casilla test 7", "tipo_casilla": "importe", "pagina": 2},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all("test 7" in item["etiqueta"].lower() for item in data["casillas"])
    assert data["filters"]["q"] == "Casilla test 7"


@pytest.mark.asyncio
async def test_modelo_casillas_falls_back_to_latest_campaign_with_fields_when_active_is_empty():
    _seed_modelo_with_empty_active_campaign_and_historical_casillas("290")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/290/casillas", params={"limit": 5})

    assert response.status_code == 200
    data = response.json()
    assert data["campana_activa"] == "2013"
    assert data["campana"] == "2025"
    assert data["total"] == 1
    assert data["classification"] == "confirmado"
    assert data["verified"] is False
    assert data["confidence"]["review_required"] is True
    assert "campana activa 2013 no tiene casillas" in data["selection_notice"]


@pytest.mark.asyncio
async def test_modelo_detail_reports_casillas_fallback_campaign_transparently():
    _seed_modelo_with_empty_active_campaign_and_historical_casillas("290")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/290", params={"casillas_limit": 5})

    assert response.status_code == 200
    data = response.json()
    assert data["campana_activa"] == "2013"
    assert data["casillas_campana"] == "2025"
    assert data["casillas_total"] == 1
    assert data["verified"] is False
    assert "campana activa 2013 no tiene casillas" in data["casillas_selection_notice"]
