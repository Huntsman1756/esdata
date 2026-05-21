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
    *, persisted_irnr_article: bool = False, estado_vigencia: str | None = None
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
    assert body["modelo_aeat_referencia"] == "216/296"
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
    assert relacion["modelo_aeat"] == "216/296"
    assert relacion["tipo_renta"] == "retenciones_no_residentes"
    assert relacion["verified"] is True
    assert relacion["completeness"] == "partial"


@pytest.mark.asyncio
async def test_doctrina_pilot_line_retenciones_complete_requires_all_three_closures(client):
    _seed_pilot_dgt_reference(
        persisted_irnr_article=True,
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
