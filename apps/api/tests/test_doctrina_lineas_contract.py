import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import db_session
from main import app
from mcp_catalog import HTTP_MCP_OPERATIONS

REQUIRED_EVIDENCE_FIELDS = {
    "verified",
    "completeness",
    "source_url",
    "capture_date",
    "safe_to_answer",
    "evidence_notice",
    "review_required",
}


def _seed_pilot_dgt_reference(
    *,
    persisted_irnr_article: bool = False,
    persisted_model_relation: bool = False,
    estado_vigencia: str | None = None,
):
    with db_session() as db:
        db.execute(
            text(
                """
                DELETE FROM criterio_relacion
                WHERE linea_codigo = 'D-01'
                """
            )
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
                    referencia, fecha, titulo, texto, url_fuente,
                    estado_vigencia, row_completeness, row_provenance
                )
                VALUES (
                    'consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal',
                    'V0166-25', '2025-02-13',
                    'Consulta DGT piloto sobre retenciones no residentes',
                    'Ficha oficial de prueba: Real Decreto Legislativo 5/2004, articulo 31, modelos 216 y 296.',
                    'https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0166-25',
                    NULL, 'complete', 'official_exact'
                )
                """
            )
        )
        db.execute(
            text(
                """
                UPDATE documento_interpretativo
                SET estado_vigencia = :estado_vigencia
                WHERE referencia = 'V0166-25'
                """
            ),
            {"estado_vigencia": estado_vigencia},
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO source_revision (
                    worker_name, source_entity_tipo, source_entity_id,
                    content_hash_sha256, fetched_at, dgt_url
                )
                VALUES (
                    'worker-dgt', 'consulta_vinculante', 'V0166-25',
                    'sha256-v0166-25-test', '2026-05-21T08:30:00Z',
                    'https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0166-25'
                )
                """
            )
        )
        db.execute(
            text(
                """
                DELETE FROM documento_articulo
                WHERE documento_id = (
                    SELECT id FROM documento_interpretativo WHERE referencia = 'V0166-25'
                )
                AND articulo_id IN (
                    SELECT a.id
                    FROM articulo a
                    JOIN norma n ON n.id = a.norma_id
                    WHERE n.codigo = 'TRLIRNR' AND a.numero = '31'
                )
                """
            )
        )
        if persisted_irnr_article:
            db.execute(
                text(
                    """
                    INSERT OR IGNORE INTO articulo (norma_id, numero, titulo, tipo)
                    SELECT id, '31', 'Obligacion de retener sobre rentas IRNR', 'articulo'
                    FROM norma
                    WHERE codigo = 'TRLIRNR'
                    """
                )
            )
            db.execute(
                text(
                    """
                    INSERT OR IGNORE INTO documento_articulo (
                        documento_id, articulo_id, metodo_enlace, confianza_enlace, nota
                    )
                    SELECT d.id, a.id, 'manual_official', 1.0, 'Curacion D-01: texto oficial auditado'
                    FROM documento_interpretativo d
                    JOIN articulo a ON a.numero = '31'
                    JOIN norma n ON n.id = a.norma_id
                    WHERE d.referencia = 'V0166-25' AND n.codigo = 'TRLIRNR'
                    """
                )
            )
        if persisted_model_relation:
            db.execute(
                text(
                    """
                    INSERT OR IGNORE INTO criterio_relacion (
                        linea_codigo, documento_referencia, norma_codigo, articulo,
                        impuesto, modelo_aeat, tipo_renta, relacion, metodo_enlace,
                        confianza_enlace, nota_limitacion, source_url, source_hash,
                        capture_date, verified, completeness
                    )
                    VALUES (
                        'D-01', 'V0166-25', 'TRLIRNR', '31',
                        'IRNR', '216/296', 'retenciones_no_residentes',
                        'modelo_supuesto', 'manual_official',
                        1.0,
                        'Curacion D-01: modelo 216/296 auditado por supuesto en texto oficial',
                        'https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0166-25',
                        'sha256-v0166-25-test',
                        '2026-05-21T08:30:00Z',
                        1,
                        'complete'
                    )
                    """
                )
            )
        db.commit()


def _seed_pilot_document(
    *,
    referencia: str,
    titulo: str,
    texto: str,
    norma_codigo: str | None = None,
    articulo: str | None = None,
):
    with db_session() as db:
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
                    referencia, fecha, titulo, texto, url_fuente,
                    estado_vigencia, row_completeness, row_provenance
                )
                VALUES (
                    'consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal',
                    :referencia, '2026-02-05', :titulo, :texto,
                    'https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=' || :referencia,
                    NULL, 'complete', 'official_exact'
                )
                """
            ),
            {"referencia": referencia, "titulo": titulo, "texto": texto},
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO source_revision (
                    worker_name, source_entity_tipo, source_entity_id,
                    content_hash_sha256, fetched_at, dgt_url
                )
                VALUES (
                    'worker-dgt', 'consulta_vinculante', :referencia,
                    'sha256-' || lower(:referencia) || '-test', '2026-05-21T08:30:00Z',
                    'https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=' || :referencia
                )
                """
            ),
            {"referencia": referencia},
        )
        if norma_codigo and articulo:
            db.execute(
                text(
                    """
                    INSERT OR IGNORE INTO norma (
                        codigo, titulo, boe_id, jurisdiccion, tipo_fuente,
                        tipo_documento, ambito, estado_cobertura, vigente_desde
                    )
                    VALUES (
                        :norma_codigo, :norma_codigo, :norma_codigo || '-TEST',
                        'ES', 'boe', 'ley', 'tributario', 'ingestada', '2000-01-01'
                    )
                    """
                ),
                {"norma_codigo": norma_codigo},
            )
            db.execute(
                text(
                    """
                    INSERT OR IGNORE INTO articulo (norma_id, numero, titulo, tipo)
                    SELECT id, :articulo, 'Articulo piloto', 'articulo'
                    FROM norma
                    WHERE codigo = :norma_codigo
                    """
                ),
                {"norma_codigo": norma_codigo, "articulo": articulo},
            )
            db.execute(
                text(
                    """
                    INSERT OR IGNORE INTO documento_articulo (
                        documento_id, articulo_id, metodo_enlace, confianza_enlace, nota
                    )
                    SELECT d.id, a.id, 'auto_link_exact', 1.0, 'Enlace fixture'
                    FROM documento_interpretativo d
                    JOIN articulo a ON a.numero = :articulo
                    JOIN norma n ON n.id = a.norma_id
                    WHERE d.referencia = :referencia AND n.codigo = :norma_codigo
                    """
                ),
                {"referencia": referencia, "norma_codigo": norma_codigo, "articulo": articulo},
            )
        db.commit()


def _seed_generic_hashless_doctrina_line():
    with db_session() as db:
        db.execute(
            text(
                """
                DELETE FROM source_revision
                WHERE source_entity_id = 'V9999-26'
                """
            )
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
                    referencia, fecha, titulo, texto, url_fuente,
                    estado_vigencia, row_completeness, row_provenance
                )
                VALUES (
                    'consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal',
                    'V9999-26', '2026-02-05',
                    'Consulta DGT generica sin hash de revision',
                    'Ficha oficial de prueba con fuente DGT y articulo enlazado, pero sin source_revision.',
                    'https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V9999-26',
                    'vigente', 'complete', 'official_exact'
                )
                """
            )
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO norma (
                    codigo, titulo, boe_id, jurisdiccion, tipo_fuente,
                    tipo_documento, ambito, estado_cobertura, vigente_desde
                )
                VALUES (
                    'TESTHASH', 'Norma test hashless', 'TESTHASH-BOE',
                    'ES', 'boe', 'ley', 'tributario', 'ingestada', '2000-01-01'
                )
                """
            )
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO articulo (norma_id, numero, titulo, tipo)
                SELECT id, '1', 'Articulo hashless', 'articulo'
                FROM norma
                WHERE codigo = 'TESTHASH'
                """
            )
        )
        db.execute(
            text(
                """
                INSERT INTO linea_criterio (
                    titulo, cuestion_practica, descripcion, criterio_dominante,
                    ambitos, ultimo_cambio, estado, activo
                )
                SELECT
                    'Linea generica hashless DGT',
                    'Puede una linea generica responder sin hash?',
                    'Fixture de contrato doctrina fail-closed.',
                    'No debe responder sin source_revision.',
                    '["hashless","doctrina_administrativa"]',
                    '2026-05-21',
                    'vigente',
                    1
                WHERE NOT EXISTS (
                    SELECT 1 FROM linea_criterio WHERE titulo = 'Linea generica hashless DGT'
                )
                """
            )
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO linea_criterio_referencia (
                    linea_id, documento_referencia, tipo_documento,
                    organismo_emisor, fecha, rol_en_linea, orden
                )
                SELECT
                    l.id, 'V9999-26', 'consulta_vinculante',
                    'DGT', '2026-02-05', 'consulta_principal', 1
                FROM linea_criterio l
                WHERE l.titulo = 'Linea generica hashless DGT'
                """
            )
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO documento_articulo (
                    documento_id, articulo_id, metodo_enlace, confianza_enlace, nota
                )
                SELECT d.id, a.id, 'manual_official', 1.0, 'Fixture hashless'
                FROM documento_interpretativo d
                JOIN articulo a ON a.numero = '1'
                JOIN norma n ON n.id = a.norma_id
                WHERE d.referencia = 'V9999-26' AND n.codigo = 'TESTHASH'
                """
            )
        )
        db.commit()


def _seed_generic_complete_doctrina_line() -> str:
    with db_session() as db:
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
                    referencia, fecha, titulo, texto, url_fuente,
                    estado_vigencia, row_completeness, row_provenance
                )
                VALUES (
                    'consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal',
                    'V9998-26', '2026-02-06',
                    'Consulta DGT generica con hash y relacion',
                    'Ficha oficial de prueba con fuente DGT, articulo, source_revision y modelo.',
                    'https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V9998-26',
                    'vigente', 'complete', 'official_exact'
                )
                """
            )
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO source_revision (
                    worker_name, source_entity_tipo, source_entity_id,
                    content_hash_sha256, fetched_at, dgt_url
                )
                VALUES (
                    'worker-dgt', 'consulta_vinculante', 'V9998-26',
                    'sha256-v9998-26-test', '2026-05-21T09:00:00Z',
                    'https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V9998-26'
                )
                """
            )
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO norma (
                    codigo, titulo, boe_id, jurisdiccion, tipo_fuente,
                    tipo_documento, ambito, estado_cobertura, vigente_desde
                )
                VALUES (
                    'TESTFULL', 'Norma test completa', 'TESTFULL-BOE',
                    'ES', 'boe', 'ley', 'tributario', 'ingestada', '2000-01-01'
                )
                """
            )
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO articulo (norma_id, numero, titulo, tipo)
                SELECT id, '31', 'Articulo completo', 'articulo'
                FROM norma
                WHERE codigo = 'TESTFULL'
                """
            )
        )
        db.execute(
            text(
                """
                INSERT INTO linea_criterio (
                    titulo, cuestion_practica, descripcion, criterio_dominante,
                    ambitos, ultimo_cambio, estado, activo
                )
                SELECT
                    'Linea generica completa DGT',
                    'Puede una linea generica responder con evidencia completa?',
                    'Fixture de contrato doctrina completo.',
                    'Solo debe responder con source_revision y relacion normalizada.',
                    '["generic_complete","doctrina_administrativa"]',
                    '2026-05-21',
                    'vigente',
                    1
                WHERE NOT EXISTS (
                    SELECT 1 FROM linea_criterio WHERE titulo = 'Linea generica completa DGT'
                )
                """
            )
        )
        linea_id = db.execute(
            text("SELECT id FROM linea_criterio WHERE titulo = 'Linea generica completa DGT'")
        ).scalar_one()
        codigo = f"LC-{linea_id:04d}"
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO linea_criterio_referencia (
                    linea_id, documento_referencia, tipo_documento,
                    organismo_emisor, fecha, rol_en_linea, orden
                )
                VALUES (
                    :linea_id, 'V9998-26', 'consulta_vinculante',
                    'DGT', '2026-02-06', 'consulta_principal', 1
                )
                """
            ),
            {"linea_id": linea_id},
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO documento_articulo (
                    documento_id, articulo_id, metodo_enlace, confianza_enlace, nota
                )
                SELECT d.id, a.id, 'manual_official', 1.0, 'Fixture complete'
                FROM documento_interpretativo d
                JOIN articulo a ON a.numero = '31'
                JOIN norma n ON n.id = a.norma_id
                WHERE d.referencia = 'V9998-26' AND n.codigo = 'TESTFULL'
                """
            )
        )
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO criterio_relacion (
                    linea_codigo, linea_criterio_id, documento_referencia,
                    norma_codigo, articulo, impuesto, modelo_aeat, tipo_renta,
                    relacion, metodo_enlace, confianza_enlace, nota_limitacion,
                    source_url, source_hash, capture_date, verified, completeness
                )
                VALUES (
                    :codigo, :linea_id, 'V9998-26',
                    'TESTFULL', '31', 'IRNR', '216', 'servicios_profesionales',
                    'modelo_supuesto', 'manual_official', 1.0,
                    'Fixture: relacion modelo/supuesto persistida',
                    'https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V9998-26',
                    'sha256-v9998-26-test', '2026-05-21T09:00:00Z',
                    1, 'complete'
                )
                """
            ),
            {"codigo": codigo, "linea_id": linea_id},
        )
        db.commit()
        return codigo


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_doctrina_lineas_list_exposes_fail_closed_contract(client):
    response = await client.get("/v1/doctrina/lineas")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 7
    assert body["safe_to_answer"] is False
    assert body["review_required"] is True
    assert "evidence_notice" in body

    first = body["lineas"][0]
    assert REQUIRED_EVIDENCE_FIELDS.issubset(first)
    assert first["completeness"] in {"partial", "target"}
    assert first["safe_to_answer"] is False
    assert first["review_required"] is True


@pytest.mark.asyncio
async def test_generic_db_line_with_source_and_article_but_no_hash_fails_closed(client):
    _seed_generic_hashless_doctrina_line()

    response = await client.get("/v1/doctrina/lineas", params={"tema": "hashless"})

    assert response.status_code == 200
    body = response.json()
    line = next(item for item in body["lineas"] if item["titulo"] == "Linea generica hashless DGT")
    assert line["source_url"].endswith("num_consulta=V9999-26")
    assert line["source_hash"] is None
    assert line["articulo_referencia"] == "TESTHASH art. 1"
    assert line["completeness"] == "partial"
    assert line["safe_to_answer"] is False
    assert line["review_required"] is True
    assert body["safe_to_answer"] is False


@pytest.mark.asyncio
async def test_generic_db_line_with_hash_article_and_model_relation_can_answer(client):
    codigo = _seed_generic_complete_doctrina_line()

    response = await client.get(f"/v1/doctrina/lineas/{codigo}")

    assert response.status_code == 200
    body = response.json()
    assert body["codigo"] == codigo
    assert body["source_hash"] == "sha256-v9998-26-test"
    assert body["capture_date"] == "2026-05-21T09:00:00Z"
    assert body["impuesto"] == "IRNR"
    assert body["articulo_referencia"] == "TESTFULL art. 31"
    assert body["modelo_aeat_referencia"] == "216"
    assert body["completeness"] == "complete"
    assert body["verified"] is True
    assert body["safe_to_answer"] is True
    assert body["review_required"] is False


@pytest.mark.asyncio
async def test_doctrina_linea_detail_supports_codigo_and_required_evidence(client):
    list_response = await client.get("/v1/doctrina/lineas")
    codigo = list_response.json()["lineas"][0]["codigo"]

    response = await client.get(f"/v1/doctrina/lineas/{codigo}")

    assert response.status_code == 200
    body = response.json()
    assert body["codigo"] == codigo
    assert REQUIRED_EVIDENCE_FIELDS.issubset(body)
    assert body["safe_to_answer"] is False


@pytest.mark.asyncio
async def test_doctrina_pilot_line_retenciones_uses_official_evidence_fail_closed(client):
    _seed_pilot_dgt_reference()

    response = await client.get("/v1/doctrina/lineas/D-01")

    assert response.status_code == 200
    body = response.json()
    assert body["codigo"] == "D-01"
    assert body["fuente"] == "dgt"
    assert body["tema"] == "retenciones_no_residentes"
    assert body["impuesto"] == "IRNR"
    assert body["articulo_referencia"] == "TRLIRNR art. 31"
    assert body["modelo_aeat_referencia"] is None
    assert body["source_url"].endswith("num_consulta=V0166-25")
    assert body["source_hash"] == "sha256-v0166-25-test"
    assert body["capture_date"] == "2026-05-21T08:30:00Z"
    assert body["completeness"] == "partial"
    assert body["verified"] is True
    assert body["safe_to_answer"] is False
    assert body["review_required"] is True
    assert "piloto" in body["evidence_notice"].lower()


@pytest.mark.asyncio
async def test_doctrina_pilot_line_relaciones_keep_model_relation_partial(client):
    _seed_pilot_dgt_reference()

    response = await client.get("/v1/doctrina/lineas/D-01/relaciones")

    assert response.status_code == 200
    body = response.json()
    assert body["codigo"] == "D-01"
    assert body["safe_to_answer"] is False
    assert body["review_required"] is True
    relacion = body["relaciones"][0]
    assert relacion["documento_referencia"] == "V0166-25"
    assert relacion["norma_codigo"] == "TRLIRNR"
    assert relacion["articulo"] == "31"
    assert relacion["modelo_aeat"] is None
    assert relacion["tipo_renta"] == "retenciones_no_residentes"
    assert relacion["verified"] is False
    assert relacion["completeness"] == "partial"


@pytest.mark.asyncio
async def test_doctrina_pilot_line_retenciones_complete_requires_all_three_closures(client):
    _seed_pilot_dgt_reference(
        persisted_irnr_article=True,
        persisted_model_relation=True,
        estado_vigencia="historico_a_fecha_consulta",
    )

    response = await client.get("/v1/doctrina/lineas/D-01")

    assert response.status_code == 200
    body = response.json()
    assert body["codigo"] == "D-01"
    assert body["articulo_referencia"] == "TRLIRNR art. 31"
    assert body["modelo_aeat_referencia"] == "216/296"
    assert body["estado_vigente"] == "historico_a_fecha_consulta"
    assert body["completeness"] == "complete"
    assert body["safe_to_answer"] is True
    assert body["review_required"] is False

    relaciones_response = await client.get("/v1/doctrina/lineas/D-01/relaciones")
    relacion = relaciones_response.json()["relaciones"][0]
    assert relacion["verified"] is True
    assert "completa" in relacion["nota_limitacion"]
    assert "sigue partial" not in relacion["nota_limitacion"]


@pytest.mark.asyncio
async def test_doctrina_pilot_line_retenciones_stays_partial_without_persisted_model_relation(
    client,
):
    _seed_pilot_dgt_reference(
        persisted_irnr_article=True,
        persisted_model_relation=False,
        estado_vigencia="historico_a_fecha_consulta",
    )

    response = await client.get("/v1/doctrina/lineas/D-01")

    assert response.status_code == 200
    body = response.json()
    assert body["articulo_referencia"] == "TRLIRNR art. 31"
    assert body["modelo_aeat_referencia"] is None
    assert body["completeness"] == "partial"
    assert body["safe_to_answer"] is False
    assert body["review_required"] is True


@pytest.mark.asyncio
async def test_doctrina_pilot_line_iva_intracomunitario_does_not_reuse_wrong_liva_article_or_model(
    client,
):
    _seed_pilot_document(
        referencia="V0236-26",
        titulo="Tipo impositivo aplicable en IVA",
        texto="Consulta sobre tipo impositivo de productos sanitarios. Se analiza LIVA articulo 91.",
        norma_codigo="LIVA",
        articulo="91",
    )

    response = await client.get("/v1/doctrina/lineas/D-02")

    assert response.status_code == 200
    body = response.json()
    assert body["completeness"] == "partial"
    assert body["safe_to_answer"] is False
    assert body["articulo_referencia"] is None
    assert body["modelo_aeat_referencia"] is None


@pytest.mark.asyncio
async def test_doctrina_pilot_line_operaciones_vinculadas_keeps_model_partial_without_232_trace(
    client,
):
    _seed_pilot_document(
        referencia="V0144-26",
        titulo="Operaciones vinculadas y valor de mercado",
        texto="Consulta sobre operaciones vinculadas. Ley 27/2014 articulo 18 y valor de mercado.",
        norma_codigo="LIS",
        articulo="18",
    )

    response = await client.get("/v1/doctrina/lineas/D-03")

    assert response.status_code == 200
    body = response.json()
    assert body["completeness"] == "partial"
    assert body["safe_to_answer"] is False
    assert body["articulo_referencia"] == "LIS art. 18"
    assert body["modelo_aeat_referencia"] is None


@pytest.mark.asyncio
async def test_doctrina_pilot_line_canones_does_not_reuse_liva_services_as_irnr_royalties(
    client,
):
    _seed_pilot_document(
        referencia="V0228-26",
        titulo="Lugar de realizacion de prestaciones de servicios",
        texto="Consulta sobre prestaciones de servicios y lugar de realizacion. Se analiza LIVA articulo 11.",
        norma_codigo="LIVA",
        articulo="11",
    )

    response = await client.get("/v1/doctrina/lineas/D-07")

    assert response.status_code == 200
    body = response.json()
    assert body["completeness"] == "partial"
    assert body["safe_to_answer"] is False
    assert body["articulo_referencia"] is None
    assert body["modelo_aeat_referencia"] is None


@pytest.mark.asyncio
async def test_doctrina_pilot_line_professional_services_does_not_reuse_liva_exemption_as_irnr(
    client,
):
    _seed_pilot_document(
        referencia="V0191-26",
        titulo="Exencion IVA para servicios",
        texto="Consulta sobre aplicabilidad de una exencion en servicios. Se analiza LIVA articulo 20.",
        norma_codigo="LIVA",
        articulo="20",
    )

    response = await client.get("/v1/doctrina/lineas/D-09")

    assert response.status_code == 200
    body = response.json()
    assert body["completeness"] == "partial"
    assert body["safe_to_answer"] is False
    assert body["articulo_referencia"] is None
    assert body["modelo_aeat_referencia"] is None


@pytest.mark.asyncio
async def test_doctrina_pilot_lines_are_filterable_without_complete_claim(client):
    response = await client.get("/v1/doctrina/lineas", params={"tema": "criptoactivos"})

    assert response.status_code == 200
    body = response.json()
    codigos = {item["codigo"] for item in body["lineas"]}
    assert "D-05" in codigos
    pilot = next(item for item in body["lineas"] if item["codigo"] == "D-05")
    assert pilot["completeness"] in {"partial", "target"}
    assert pilot["safe_to_answer"] is False
    assert body["safe_to_answer"] is False


@pytest.mark.asyncio
async def test_doctrina_lineas_not_found_returns_404(client):
    response = await client.get("/v1/doctrina/lineas/LC-999999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_doctrina_linea_relaciones_are_partial_without_traceable_doctrine(client):
    list_response = await client.get("/v1/doctrina/lineas")
    codigo = list_response.json()["lineas"][0]["codigo"]

    response = await client.get(f"/v1/doctrina/lineas/{codigo}/relaciones")

    assert response.status_code == 200
    body = response.json()
    assert body["codigo"] == codigo
    assert body["safe_to_answer"] is False
    assert body["review_required"] is True
    assert body["relaciones"]
    assert body["relaciones"][0]["verified"] is False
    assert body["relaciones"][0]["completeness"] in {"partial", "target"}


@pytest.mark.asyncio
async def test_doctrina_coverage_declares_implemented_partial(client):
    response = await client.get("/v1/doctrina/lineas/coverage")

    assert response.status_code == 200
    body = response.json()
    assert body["familia"] == "doctrina_administrativa_dgt_teac"
    assert body["estado"] == "implemented_partial"
    assert body["safe_to_answer"] is False
    assert body["review_required"] is True
    assert body["lineas_complete"] < body["lineas_total"]
    assert body["lineas_total"] >= 16


def test_doctrina_lineas_are_exposed_to_http_mcp_catalog():
    expected = {
        "listar_lineas_criterio",
        "detalle_linea_criterio",
        "buscar_lineas_criterio",
        "detalle_linea_criterio_doctrina",
        "criterio_relacionado_con_modelo",
        "doctrina_coverage",
    }

    assert expected.issubset(set(HTTP_MCP_OPERATIONS))
