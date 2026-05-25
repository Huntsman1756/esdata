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


def _seed_modelo_296_income_keys(*, dividend_hash: str | None = "hash-dividendos"):
    from db import engine

    with engine.begin() as conn:
        model_id = conn.execute(
            text("SELECT id FROM aeat_modelo WHERE codigo = '296'")
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO modelo_campana (
                    modelo_id, campana, activo, estado_publicacion,
                    url_instrucciones, url_normativa, url_formato
                )
                VALUES (
                    :modelo_id, '2025', 1, 'publicada',
                    'https://sede.agenciatributaria.gob.es/modelo-296',
                    'https://www.boe.es/buscar/act.php?id=BOE-A-2008-18497',
                    NULL
                )
                """
            ),
            {"modelo_id": model_id},
        )
        campana_id = conn.execute(
            text(
                """
                SELECT id
                FROM modelo_campana
                WHERE modelo_id = :modelo_id
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"modelo_id": model_id},
        ).scalar_one()
        for codigo, etiqueta, source_hash in (
            (
                "1",
                "Dividendos y otras rentas derivadas de la participacion en fondos propios de entidades",
                dividend_hash,
            ),
            (
                "2",
                "Intereses y otras rentas derivadas de la cesion a terceros de capitales propios",
                "hash-intereses",
            ),
        ):
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_clave (
                        campana_id, codigo, etiqueta, descripcion, tipo_clave, tipo,
                        criterio_aplicacion, source_url, source_hash, capture_date, activa
                    )
                    VALUES (
                        :campana_id, :codigo, :etiqueta, :etiqueta,
                        'CLAVE_RENTA', 'CLAVE_RENTA',
                        'Usar en posiciones 100-101 segun el tipo de renta declarado.',
                        'https://www.boe.es/buscar/act.php?id=BOE-A-2008-18497',
                        :source_hash, '2026-05-14', 1
                    )
                    """
                ),
                {
                    "campana_id": campana_id,
                    "codigo": codigo,
                    "etiqueta": etiqueta,
                    "source_hash": source_hash,
                },
            )


def _seed_modelo_193_income_keys(*, naturaleza_hash: str | None = "hash-nat-dividendos"):
    from db import engine

    with engine.begin() as conn:
        model_id = conn.execute(
            text("SELECT id FROM aeat_modelo WHERE codigo = '193'")
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO modelo_campana (
                    modelo_id, campana, activo, estado_publicacion,
                    url_instrucciones, url_normativa, url_formato
                )
                VALUES (
                    :modelo_id, '2025', 1, 'publicada',
                    'https://sede.agenciatributaria.gob.es/modelo-193',
                    'https://www.boe.es/buscar/act.php?id=BOE-A-2000-22303',
                    NULL
                )
                """
            ),
            {"modelo_id": model_id},
        )
        campana_id = conn.execute(
            text(
                """
                SELECT id
                FROM modelo_campana
                WHERE modelo_id = :modelo_id
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"modelo_id": model_id},
        ).scalar_one()
        for codigo, tipo, etiqueta, source_hash in (
            (
                "PERCEPCION_A",
                "CLAVE_PERCEPCION",
                "Rendimientos o rentas por participacion en fondos propios de cualquier entidad",
                "hash-percepcion-a",
            ),
            (
                "NAT_A_02",
                "NATURALEZA",
                "Dividendos y participaciones en beneficios",
                naturaleza_hash,
            ),
            (
                "PERCEPCION_B",
                "CLAVE_PERCEPCION",
                "Rendimientos o rentas por cesion a terceros de capitales propios distintos de la letra D",
                "hash-percepcion-b",
            ),
            (
                "NAT_BD_01",
                "NATURALEZA",
                "Intereses de obligaciones, bonos, certificados de deposito u otros titulos privados",
                "hash-nat-intereses",
            ),
        ):
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_clave (
                        campana_id, codigo, etiqueta, descripcion, tipo_clave, tipo,
                        criterio_aplicacion, source_url, source_hash, capture_date, activa
                    )
                    VALUES (
                        :campana_id, :codigo, :etiqueta, :etiqueta,
                        :tipo, :tipo,
                        'Usar en las posiciones oficiales del registro de tipo 2.',
                        'https://www.boe.es/buscar/act.php?id=BOE-A-2000-22303',
                        :source_hash, '2026-05-14', 1
                    )
                    """
                ),
                {
                    "campana_id": campana_id,
                    "codigo": codigo,
                    "tipo": tipo,
                    "etiqueta": etiqueta,
                    "source_hash": source_hash,
                },
            )


def _cleanup_sociedad_valores_modelos():
    from db import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM modelo_clave
                WHERE campana_id IN (
                    SELECT mc.id
                    FROM modelo_campana mc
                    JOIN aeat_modelo m ON m.id = mc.modelo_id
                    WHERE m.codigo IN ('123', '124', '193', '216', '296')
                )
                """
            )
        )
        conn.execute(
            text(
                """
                DELETE FROM modelo_campana
                WHERE modelo_id IN (
                    SELECT id
                    FROM aeat_modelo
                    WHERE codigo IN ('123', '124', '193', '216', '296')
                )
                """
            )
        )
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
async def test_modelo_fuentes_oficiales_exposes_active_modelo_recurso_urls():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/100/fuentes-oficiales")

    assert response.status_code == 200
    urls = {item["url"] for item in response.json()["fuentes_oficiales"]}
    assert "https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2025.pdf" in urls
    assert "https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2024.pdf" not in urls
    assert (
        "https://sede.agenciatributaria.gob.es/Sede/condiciones-uso-sede-electronica/"
        "accesibilidad/declaracion-accesibilidad.html"
        not in urls
    )
    instrucciones = next(
        item for item in response.json()["fuentes_oficiales"]
        if item["url"] == "https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2025.pdf"
    )
    assert instrucciones["proves_campaign"] is False
    assert instrucciones["campaign_evidence_role"] == "weak"
    data = response.json()
    assert data["campana_activa"] == "2025"
    assert data["campana_persistida"] == "2025"
    assert data["campana_afirmable"] is None
    assert data["campana_candidata"] is None
    assert data["campana_resolution_status"] == "conflict"
    assert data["campana_verification_level"] == "contradictory"
    assert data["campana_safe_to_assert"] is False
    assert data["campana_assertion_code"] == "NOT_ASSERTABLE_CONFLICT"
    assert "do not treat" in data["campana_assertion_warning"].lower()
    assert "no afirmable" in data["campana_user_notice"].lower()
    assert data["campana_conflict"] is True
    assert data["campana_conflict_severity"] == "weak"
    assert data["campana_conflict_years"] == ["2025", "2026"]
    assert any(
        "2026" in item["years"]
        for item in data["campana_conflict_evidence"]
    ), data["campana_conflict_evidence"]


@pytest.mark.asyncio
async def test_modelo_artefactos_exposes_active_modelo_recurso_urls():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/100/artefactos")

    assert response.status_code == 200
    artefactos = response.json()["artefactos"]
    urls = {item["url"] for item in artefactos}
    assert "https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2025.pdf" in urls
    assert "https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2024.pdf" not in urls
    assert (
        "https://sede.agenciatributaria.gob.es/Sede/condiciones-uso-sede-electronica/"
        "accesibilidad/declaracion-accesibilidad.html"
        not in urls
    )
    assert any(item["tipo"] == "modelo_recurso:instrucciones" for item in artefactos)
    instrucciones = next(
        item for item in artefactos
        if item["url"] == "https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2025.pdf"
    )
    assert instrucciones["proves_campaign"] is False
    assert instrucciones["campaign_evidence_role"] == "weak"
    data = response.json()
    assert data["campana_activa"] == "2025"
    assert data["campana_persistida"] == "2025"
    assert data["campana_afirmable"] is None
    assert data["campana_candidata"] is None
    assert data["campana_resolution_status"] == "conflict"
    assert data["campana_verification_level"] == "contradictory"
    assert data["campana_safe_to_assert"] is False
    assert data["campana_assertion_code"] == "NOT_ASSERTABLE_CONFLICT"
    assert "do not treat" in data["campana_assertion_warning"].lower()
    assert "no afirmable" in data["campana_user_notice"].lower()
    assert data["campana_conflict"] is True
    assert data["campana_conflict_severity"] == "weak"
    assert data["campana_conflict_years"] == ["2025", "2026"]
    assert any(
        "2026" in item["years"]
        for item in data["campana_conflict_evidence"]
    ), data["campana_conflict_evidence"]


def test_campana_selection_marks_resource_only_conflict_fail_closed():
    from services.modelos import _build_campana_selection

    selection = _build_campana_selection(
        None,
        [
            {
                "tipo": "modelo_recurso:diseno_registro",
                "url": "https://sede.agenciatributaria.gob.es/dr210_2019.xlsx",
                "titulo": "Diseño registro 2019",
            },
            {
                "tipo": "modelo_recurso:diseno_registro",
                "url": "https://sede.agenciatributaria.gob.es/dr210_2026.xlsx",
                "titulo": "Diseño registro 2026",
            },
        ],
    )

    assert selection["campana_candidata"] is None
    assert selection["campana_resolution_status"] == "conflict"
    assert selection["campana_afirmable"] is None
    assert selection["campana_safe_to_assert"] is False
    assert selection["campana_verification_level"] == "contradictory"
    assert selection["campana_assertion_code"] == "NOT_ASSERTABLE_CONFLICT"
    assert "do not treat" in selection["campana_assertion_warning"].lower()
    assert selection["campana_conflict"] is True
    assert selection["campana_conflict_severity"] == "strong"
    assert selection["campana_conflict_years"] == ["2019", "2026"]


def test_campana_selection_marks_non_conflicting_persisted_year_as_weak_not_assertable():
    from services.modelos import _build_campana_selection

    selection = _build_campana_selection("2025", [])

    assert selection["campana_persistida"] == "2025"
    assert selection["campana_candidata"] == "2025"
    assert selection["campana_afirmable"] is None
    assert selection["campana_resolution_status"] == "resolved_weak"
    assert selection["campana_verification_level"] == "inferred_internal"
    assert selection["campana_safe_to_assert"] is False
    assert selection["campana_assertion_code"] == "NOT_ASSERTABLE_INFERRED_INTERNAL"
    assert "do not treat" in selection["campana_assertion_warning"].lower()
    assert "no afirmable" in selection["campana_user_notice"].lower()


def test_campana_selection_only_asserts_when_resource_explicitly_proves_campaign():
    from services.modelos import _build_campana_selection

    selection = _build_campana_selection(
        "2025",
        [
            {
                "tipo": "aeat_instrucciones",
                "url": "https://sede.agenciatributaria.gob.es/modelo-100",
                "campana": "2025",
                "proves_campaign": True,
            }
        ],
    )

    assert selection["campana_candidata"] == "2025"
    assert selection["campana_afirmable"] == "2025"
    assert selection["campana_resolution_status"] == "resolved_strong"
    assert selection["campana_verification_level"] == "direct_official"
    assert selection["campana_safe_to_assert"] is True
    assert selection["campana_assertion_code"] == "ASSERTABLE_DIRECT_OFFICIAL"
    assert selection["campana_assertion_warning"] is None


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
        assert "124" not in by_codigo
        assert by_codigo["193"]["clasificacion"] == "candidato"
        assert by_codigo["216"]["clasificacion"] == "candidato"
        assert by_codigo["296"]["clasificacion"] == "candidato"
        assert by_codigo["216"]["condicion_aplicacion"]
        assert by_codigo["296"]["evidencia"][0]["source"] == "aeat_modelo"

        excluded = {item["codigo"]: item["reason"] for item in data["excluded_modelos"]}
        assert "activos_financieros_no_confirmados_para_124" in excluded["124"]
        assert "100" in excluded
        assert "111" in excluded
        assert "115" in excluded
        assert "190" in excluded
    finally:
        _cleanup_sociedad_valores_modelos()


@pytest.mark.asyncio
async def test_modelos_por_supuesto_includes_124_only_for_specific_financial_asset_operation():
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
                    "tipo_renta": "capital_mobiliario",
                    "tipo_operacion": "transmision de activos financieros",
                },
            )

        assert response.status_code == 200
        data = response.json()

        by_codigo = {item["codigo"]: item for item in data["modelos"]}
        modelo_124 = by_codigo["124"]
        assert modelo_124["clasificacion"] == "candidato"
        assert "operacion_activos_financieros_124" in modelo_124["matched_factors"]
        assert "evidencia_explicita_de_obligatoriedad_para_sociedad_valores" in modelo_124[
            "missing_factors"
        ]
        assert data["verified"] is False
        assert data["confidence"]["review_required"] is True
    finally:
        _cleanup_sociedad_valores_modelos()


@pytest.mark.asyncio
async def test_modelos_por_supuesto_uses_296_income_key_evidence_without_confirming_obligation():
    _cleanup_sociedad_valores_modelos()
    _seed_sociedad_valores_modelos()
    _seed_modelo_296_income_keys()

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
                    "clientes_no_residentes": True,
                    "tipo_renta": "dividendos",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "evidence_limited"
        assert data["verified"] is False
        by_codigo = {item["codigo"]: item for item in data["modelos"]}
        modelo_296 = by_codigo["296"]
        assert modelo_296["clasificacion"] == "candidato"
        assert "tipo_renta_dividendos" in modelo_296["matched_factors"]
        assert "convenio_o_regla_domestica_por_pais" in modelo_296["missing_factors"]
        key_evidence = [
            item
            for item in modelo_296["evidencia"]
            if item["source"] == "modelo_clave"
        ]
        assert len(key_evidence) == 1
        assert key_evidence[0]["source_document"] == "296:CLAVE_RENTA:1"
        assert key_evidence[0]["source_hash"] == "hash-dividendos"
        assert key_evidence[0]["capture_date"] == "2026-05-14"
        assert "Dividendos" in key_evidence[0]["excerpt"]

        modelo_216 = by_codigo["216"]
        assert "tipo_renta_dividendos" not in modelo_216["matched_factors"]
        assert not any(item["source"] == "modelo_clave" for item in modelo_216["evidencia"])
    finally:
        _cleanup_sociedad_valores_modelos()


@pytest.mark.asyncio
async def test_modelos_por_supuesto_ignores_income_key_without_hash_evidence():
    _cleanup_sociedad_valores_modelos()
    _seed_sociedad_valores_modelos()
    _seed_modelo_296_income_keys(dividend_hash=None)

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
                    "clientes_no_residentes": True,
                    "tipo_renta": "dividendos",
                },
            )

        assert response.status_code == 200
        data = response.json()

        by_codigo = {item["codigo"]: item for item in data["modelos"]}
        modelo_296 = by_codigo["296"]
        assert "tipo_renta_dividendos" not in modelo_296["matched_factors"]
        assert not any(item["source"] == "modelo_clave" for item in modelo_296["evidencia"])
        assert "tipo_renta_dividendos_sin_hash_o_captura" in modelo_296["missing_factors"]
        assert data["verified"] is False
    finally:
        _cleanup_sociedad_valores_modelos()


@pytest.mark.asyncio
async def test_modelos_por_supuesto_uses_193_income_key_evidence_without_confirming_obligation():
    _cleanup_sociedad_valores_modelos()
    _seed_sociedad_valores_modelos()
    _seed_modelo_193_income_keys()

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
                    "tipo_renta": "dividendos",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "evidence_limited"
        assert data["verified"] is False
        by_codigo = {item["codigo"]: item for item in data["modelos"]}
        modelo_193 = by_codigo["193"]
        assert modelo_193["clasificacion"] == "candidato"
        assert "tipo_renta_dividendos_residentes" in modelo_193["matched_factors"]
        assert "perceptor_y_retencion_concreta" in modelo_193["missing_factors"]
        key_evidence = [
            item
            for item in modelo_193["evidencia"]
            if item["source"] == "modelo_clave"
        ]
        assert {item["source_document"] for item in key_evidence} == {
            "193:CLAVE_PERCEPCION:PERCEPCION_A",
            "193:NATURALEZA:NAT_A_02",
        }
        assert all(item["source_hash"] for item in key_evidence)
        assert all(item["capture_date"] == "2026-05-14" for item in key_evidence)

        modelo_123 = by_codigo["123"]
        assert "tipo_renta_dividendos_residentes" not in modelo_123["matched_factors"]
        assert not any(item["source"] == "modelo_clave" for item in modelo_123["evidencia"])
    finally:
        _cleanup_sociedad_valores_modelos()


@pytest.mark.asyncio
async def test_modelos_por_supuesto_ignores_193_income_key_without_hash_evidence():
    _cleanup_sociedad_valores_modelos()
    _seed_sociedad_valores_modelos()
    _seed_modelo_193_income_keys(naturaleza_hash=None)

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
                    "tipo_renta": "dividendos",
                },
            )

        assert response.status_code == 200
        data = response.json()

        by_codigo = {item["codigo"]: item for item in data["modelos"]}
        modelo_193 = by_codigo["193"]
        assert "tipo_renta_dividendos_residentes" not in modelo_193["matched_factors"]
        assert not any(item["source"] == "modelo_clave" for item in modelo_193["evidencia"])
        assert "tipo_renta_dividendos_residentes_sin_doble_clave_hash_o_captura" in modelo_193[
            "missing_factors"
        ]
        assert data["verified"] is False
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


def _seed_modelo_with_explicit_completeness(
    *,
    codigo: str,
    nombre: str,
    completeness_estado: str,
    has_casilla: bool = False,
    activo: int = 1,
) -> None:
    from db import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS modelo_campana_operativa (
                    campana_id INTEGER PRIMARY KEY,
                    categoria_obligado TEXT,
                    frecuencia_presentacion TEXT,
                    ventana_presentacion TEXT,
                    canal_presentacion TEXT,
                    obligados_resumen TEXT,
                    plazo_resumen TEXT,
                    presentacion_resumen TEXT,
                    norma_base TEXT,
                    nota TEXT,
                    origen_metadato TEXT,
                    estado_metadato TEXT,
                    completeness_estado TEXT,
                    actualizado_at TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info, activo)
                VALUES (:codigo, :nombre, 'anual', 'INFORMATIVO', :url_info, 1)
                ON CONFLICT(codigo) DO UPDATE SET
                    nombre = excluded.nombre,
                    periodo = excluded.periodo,
                    impuesto = excluded.impuesto,
                    url_info = excluded.url_info,
                    activo = 1
                """
            ),
            {
                "codigo": codigo,
                "nombre": nombre,
                "url_info": f"https://sede.agenciatributaria.gob.es/modelo-{codigo}",
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones)
                SELECT id, '2025', :activo, :url_instrucciones
                FROM aeat_modelo
                WHERE codigo = :codigo
                ON CONFLICT(modelo_id, campana) DO UPDATE SET
                    activo = excluded.activo,
                    url_instrucciones = excluded.url_instrucciones
                """
            ),
            {
                "codigo": codigo,
                "activo": activo,
                "url_instrucciones": f"https://sede.agenciatributaria.gob.es/modelo-{codigo}-2025",
            },
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
                INSERT INTO modelo_campana_operativa (
                    campana_id,
                    categoria_obligado,
                    obligados_resumen,
                    plazo_resumen,
                    presentacion_resumen,
                    nota,
                    origen_metadato,
                    estado_metadato,
                    completeness_estado
                )
                VALUES (
                    :campana_id,
                    'declaracion_informativa',
                    'Fuente AEAT verificada para prueba',
                    'Plazo segun sede AEAT',
                    'Presentacion segun sede AEAT',
                    'Metadato operativo curado para test',
                    'seed_curado',
                    'curado',
                    :completeness_estado
                )
                ON CONFLICT(campana_id) DO UPDATE SET
                    categoria_obligado = excluded.categoria_obligado,
                    obligados_resumen = excluded.obligados_resumen,
                    plazo_resumen = excluded.plazo_resumen,
                    presentacion_resumen = excluded.presentacion_resumen,
                    nota = excluded.nota,
                    origen_metadato = excluded.origen_metadato,
                    estado_metadato = excluded.estado_metadato,
                    completeness_estado = excluded.completeness_estado
                """
            ),
            {"campana_id": campana_id, "completeness_estado": completeness_estado},
        )
        if has_casilla:
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_casilla
                        (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
                    VALUES
                        (:campana_id, 'XSD:Test/Campo', 'Campo XSD de prueba', 'Campo oficial de prueba', 'diseno_registro_xsd_campo', NULL, 1)
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
    assert data["evidence_status"] == "evidence_limited"
    assert "Evidencia limitada" in data["evidence_notice"]
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
    assert data["verified"] is False
    assert data["evidence_status"] == "evidence_limited"
    assert "Evidencia limitada" in data["evidence_notice"]
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
    assert "campana persistida 2013 no tiene casillas" in data["selection_notice"]


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
    assert data["campana_persistida"] == "2013"
    assert data["campana_afirmable"] is None
    assert data["campana_safe_to_assert"] is False
    assert data["campana_resolution_status"] == "resolved_weak"
    assert data["campana_assertion_code"] == "NOT_ASSERTABLE_INFERRED_INTERNAL"
    assert "do not treat" in data["campana_assertion_warning"].lower()
    assert "no afirmable" in data["campana_user_notice"]
    assert data["casillas_campana"] == "2025"
    assert data["casillas_total"] == 1
    assert data["verified"] is False
    assert data["evidence_status"] == "evidence_limited"
    assert "Evidencia limitada" in data["evidence_notice"]
    assert "campana persistida 2013 no tiene casillas" in data["casillas_selection_notice"]


@pytest.mark.asyncio
async def test_modelo_aeat_detail_reports_casillas_fallback_campaign_transparently():
    _seed_modelo_with_empty_active_campaign_and_historical_casillas("290")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/aeat/290")

    assert response.status_code == 200
    data = response.json()
    assert data["campana_actual"]["campana"] == "2013"
    assert data["casillas_campana"] == "2025"
    assert data["casillas_total"] == 1
    assert data["verified"] is False
    assert data["evidence_status"] == "evidence_limited"
    assert "Evidencia limitada" in data["evidence_notice"]
    assert "campana persistida 2013 no tiene casillas" in data["casillas_selection_notice"]


@pytest.mark.asyncio
async def test_modelo_no_casillas_expected_is_verified_without_fake_fields():
    _seed_modelo_with_explicit_completeness(
        codigo="146",
        nombre="Modelo 146. IRPF. Pensionistas con dos o mas pagadores.",
        completeness_estado="no-casillas-expected",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        detail_response = await client.get("/v1/modelos/146", params={"casillas_limit": 5})
        casillas_response = await client.get("/v1/modelos/146/casillas", params={"limit": 5})
        operativa_response = await client.get("/v1/modelos/146/campana-operativa")

    assert detail_response.status_code == 200
    assert casillas_response.status_code == 200
    assert operativa_response.status_code == 200

    detail = detail_response.json()
    casillas = casillas_response.json()
    operativa = operativa_response.json()

    assert detail["casillas_total"] == 0
    assert detail["completeness"] == "no-casillas-expected"
    assert detail["verified"] is True
    assert detail["evidence_status"] == "no_casillas_expected"
    assert "no dispone de casillas estructuradas esperadas" in detail["evidence_notice"]
    assert casillas["classification"] == "sin_casillas_esperadas"
    assert casillas["total"] == 0
    assert casillas["evidence_status"] == "no_casillas_expected"
    assert "no dispone de casillas estructuradas esperadas" in casillas["evidence_notice"]
    assert casillas["confidence"]["review_required"] is False
    assert operativa["completeness_estado"] == "no-casillas-expected"
    assert operativa["completeness"] == "no-casillas-expected"
    assert operativa["verified"] is True


@pytest.mark.asyncio
async def test_modelo_deprecated_contract_is_explicit_and_verified():
    _seed_modelo_with_explicit_completeness(
        codigo="295",
        nombre="Modelo 295. Clientes con posicion inversora en IIC espanolas.",
        completeness_estado="deprecated",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        detail_response = await client.get("/v1/modelos/295", params={"casillas_limit": 5})
        operativa_response = await client.get("/v1/modelos/295/campana-operativa")

    assert detail_response.status_code == 200
    assert operativa_response.status_code == 200

    detail = detail_response.json()
    operativa = operativa_response.json()

    assert detail["completeness"] == "deprecated"
    assert detail["verified"] is True
    assert detail["evidence_status"] == "deprecated"
    assert "deprecated" in detail["evidence_notice"]
    assert operativa["completeness_estado"] == "deprecated"
    assert operativa["completeness"] == "deprecated"
    assert operativa["verified"] is True
