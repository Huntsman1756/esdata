import re

from db import db_session
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from request_context import get_request_id, get_user_id
from schemas import (
    DoctrinaCoverageResponse,
    DoctrinaLineaCriterioItem,
    DoctrinaLineaCriterioListResponse,
    DoctrinaLineaRelacionResponse,
    DoctrinaSearchResponse,
)
from schemas import DoctrinaDetail as DoctrinaDetailSchema
from services.query_audit import get_query_audit_service
from services.search import _build_fragment, _build_tsquery_sql, _chunk_rank_boost
from services.semantic_search import hybrid_search_doctrina
from sqlalchemy import text

EXACT_LINK_METHODS = {"manual", "manual_official", "auto_link_exact"}


def _has_exact_anchor(linked_articles: list[dict]) -> bool:
    return any(item["metodo_enlace"] in EXACT_LINK_METHODS for item in linked_articles)


def _buscar_normas_boe(db, q: str, limit: int = 5) -> list[dict]:
    params = {"term_like": f"%{q}%", "limit": limit}
    ley_match = __import__("re").search(r"\b(\d{1,4})\s*/\s*(\d{4})\b", q)
    numero = ley_match.group(1) if ley_match else None
    anio = ley_match.group(2) if ley_match else None
    search_clauses = [
        "LOWER(n.titulo) LIKE LOWER(:term_like)",
        "LOWER(n.codigo) LIKE LOWER(:term_like)",
        "LOWER(n.boe_id) LIKE LOWER(:term_like)",
        "LOWER(COALESCE(va.texto, '')) LIKE LOWER(:term_like)",
    ]

    if numero and anio:
        params["numero"] = numero
        params["anio"] = anio
        search_clauses.extend(
            [
                "LOWER(n.titulo) LIKE LOWER('% ' || :numero || '/' || :anio || '%')",
                "LOWER(COALESCE(n.eli_uri, '')) LIKE LOWER('%/' || :anio || '/%/' || :numero)",
            ]
        )

    search_sql = " OR ".join(search_clauses)

    query = text(
        f"""
        SELECT
            n.boe_id AS referencia,
            n.tipo_documento,
            'BOE' AS organismo_emisor,
            n.vigente_desde AS fecha,
            n.titulo,
            n.codigo AS norma,
            a.numero,
            n.eli_uri AS source_url,
            COALESCE(va.texto, '') AS texto
        FROM norma n
        LEFT JOIN articulo a ON a.norma_id = n.id
        LEFT JOIN version_articulo va
          ON va.articulo_id = a.id
         AND va.vigente_hasta IS NULL
        WHERE n.tipo_fuente = 'boe'
          AND (
            {search_sql}
          )
        ORDER BY n.vigente_desde DESC, a.numero ASC
        LIMIT :limit
        """
    )

    rows = db.execute(query, params).mappings()
    return [
        {
            "referencia": row["referencia"],
            "tipo_documento": row["tipo_documento"],
            "organismo_emisor": row["organismo_emisor"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "nivel_enlace": 1.0,
            "norma": row["norma"],
            "numero": row["numero"],
            "fragmento": _build_fragment(row["texto"], q) if row["texto"] else row["titulo"],
            "source_url": row["source_url"],
        }
        for row in rows
    ]

def _build_doctrina_audit_chunks(result: dict) -> list[dict]:
    return [
        {
            "referencia": item.get("referencia"),
            "tipo_documento": item.get("tipo_documento"),
            "organismo_emisor": item.get("organismo_emisor"),
            "source_url": item.get("source_url"),
            "norma": item.get("norma"),
            "numero": item.get("numero"),
        }
        for item in result.get("resultados", [])
    ]


def _doctrina_result_payload(row, fragmento: str) -> dict:
    organismo = row["organismo_emisor"]
    referencia = row["referencia"]
    return {
        "referencia": referencia,
        "numero_consulta": referencia if organismo == "DGT" else None,
        "tipo_documento": row["tipo_documento"],
        "organismo_emisor": organismo,
        "organo": organismo,
        "fecha": str(row["fecha"]) if row["fecha"] else None,
        "titulo": row["titulo"],
        "nivel_enlace": float(row["nivel_enlace"] or 0),
        "norma": row["norma"],
        "numero": row["numero"],
        "fragmento": fragmento,
        "source_url": row.get("url_fuente"),
    }


def _looks_like_doctrina_reference(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]\d{4}-\d{2}", value.strip(), flags=re.IGNORECASE))


def _normalize_doctrina_results(q: str, results: list[dict]) -> list[dict]:
    exact_reference = q.strip().upper()
    seen: set[str] = set()
    normalized: list[dict] = []
    for item in results:
        referencia = str(item.get("referencia") or "")
        referencia_key = referencia.upper()
        if _looks_like_doctrina_reference(q) and referencia_key != exact_reference:
            continue
        if referencia_key in seen:
            continue
        seen.add(referencia_key)
        normalized.append(item)
    return normalized


def _record_doctrina_query_audit(
    request: Request,
    *,
    path: str,
    query_text: str,
    tool_name: str,
    retrieved_chunks: list[dict],
    response_summary: str,
    confidence: dict,
    completeness: str = "completa",
    verified: bool = True,
):
    get_query_audit_service().record_query(
        request_id=get_request_id(request),
        user_id=get_user_id(request),
        path=path,
        query_text=query_text,
        retrieved_chunks=retrieved_chunks,
        response_summary=response_summary,
        tool_name=tool_name,
        confidence=confidence,
        completeness=completeness,
        verified=verified,
    )


router = APIRouter(prefix="/v1/doctrina", tags=["doctrina"])


DOCTRINA_FUENTES = {"DGT", "TEAC"}


PILOT_LINEAS_CRITERIO = [
    {
        "id": 9001,
        "codigo": "D-01",
        "fuente": "dgt",
        "titulo": "Retenciones no residentes",
        "tema": "retenciones_no_residentes",
        "impuesto": "IRNR",
        "modelo_aeat": "216/296",
        "modelo_evidencia": "official_text_audited_by_suppuesto",
        "vigencia_estado": "historico_a_fecha_consulta",
        "referencias": [
            {
                "referencia": "V0166-25",
                "fuente": "DGT",
                "relacion": "consulta_principal",
                "norma_codigo": "TRLIRNR",
                "articulo": "31",
                "articulo_evidencia": "official_text_audited",
                "modelo_aeat": "216/296",
                "tipo_renta": "retenciones_no_residentes",
            },
            {
                "referencia": "00/02188/2017/00/00",
                "fuente": "TEAC",
                "relacion": "resolucion_soporte",
                "tipo_renta": "retenciones_no_residentes",
            },
        ],
        "gaps": [
            "validar vigencia material de consulta y resolucion",
            "persistir enlace documental TRLIRNR art. 31 en documento_articulo o tabla equivalente",
            "cerrar relacion documental con modelo AEAT por supuesto antes de marcar complete",
        ],
    },
    {
        "id": 9002,
        "codigo": "D-02",
        "fuente": "mixta",
        "titulo": "IVA intracomunitario",
        "tema": "iva_intracomunitario",
        "impuesto": "IVA",
        "modelo_aeat": "349",
        "referencias": [
            {
                "referencia": "V0236-26",
                "fuente": "DGT",
                "relacion": "consulta_principal",
                "modelo_aeat": "349",
            },
            {
                "referencia": "00/02766/2015/00/00",
                "fuente": "TEAC",
                "relacion": "resolucion_soporte",
            },
        ],
        "gaps": ["mapear articulo LIVA exacto y alcance del modelo 303/349"],
    },
    {
        "id": 9003,
        "codigo": "D-03",
        "fuente": "mixta",
        "titulo": "Operaciones vinculadas",
        "tema": "operaciones_vinculadas",
        "impuesto": "IS",
        "modelo_aeat": "232",
        "referencias": [
            {
                "referencia": "V0144-26",
                "fuente": "DGT",
                "relacion": "consulta_principal",
                "norma_codigo": "LIS",
                "articulo": "18",
                "tipo_renta": "operaciones_vinculadas",
            },
            {
                "referencia": "00/06460/2019/00/00",
                "fuente": "TEAC",
                "relacion": "resolucion_soporte",
            },
        ],
        "gaps": ["mapear supuesto documental del modelo 232 antes de marcar complete"],
    },
    {
        "id": 9004,
        "codigo": "D-04",
        "fuente": "dgt",
        "titulo": "CRS/FATCA",
        "tema": "crs_fatca",
        "impuesto": "informacion_fiscal",
        "modelo_aeat": "289",
        "modelo_evidencia": "official_text_partial",
        "referencias": [
            {
                "referencia": "V0138-24",
                "fuente": "DGT",
                "relacion": "consulta_principal",
                "modelo_aeat": "289",
                "modelo_evidencia": "official_text_partial",
            }
        ],
        "gaps": ["separar doctrina de normativa internacional y modelo AEAT operativo"],
    },
    {
        "id": 9005,
        "codigo": "D-05",
        "fuente": "dgt",
        "titulo": "Criptoactivos",
        "tema": "criptoactivos",
        "impuesto": "IRPF",
        "modelo_aeat": "721",
        "referencias": [
            {"referencia": "V0162-26", "fuente": "DGT", "relacion": "consulta_principal"}
        ],
        "gaps": ["mapear impuesto/articulo por tipo de operacion y modelo trazable"],
    },
    {
        "id": 9006,
        "codigo": "D-06",
        "fuente": "mixta",
        "titulo": "Dividendos e intereses",
        "tema": "dividendos_intereses",
        "impuesto": "IRNR",
        "modelo_aeat": "216",
        "referencias": [
            {
                "referencia": "V0187-26",
                "fuente": "DGT",
                "relacion": "consulta_principal",
                "modelo_aeat": "216",
                "tipo_renta": "dividendos_intereses",
            },
            {
                "referencia": "00/00185/2017/00/00",
                "fuente": "TEAC",
                "relacion": "resolucion_soporte",
                "tipo_renta": "dividendos_intereses",
            },
        ],
        "gaps": ["confirmar convenio/protocolo y articulo por tipo de renta"],
    },
    {
        "id": 9007,
        "codigo": "D-07",
        "fuente": "dgt",
        "titulo": "Canones",
        "tema": "canones",
        "impuesto": "IRNR",
        "modelo_aeat": "216",
        "referencias": [
            {
                "referencia": "V0228-26",
                "fuente": "DGT",
                "relacion": "consulta_principal",
                "modelo_aeat": "216",
                "tipo_renta": "canones",
            }
        ],
        "gaps": ["documentar limitaciones por pais, convenio y articulo aplicable"],
    },
    {
        "id": 9008,
        "codigo": "D-08",
        "fuente": "mixta",
        "titulo": "Establecimiento permanente",
        "tema": "establecimiento_permanente",
        "impuesto": "IRNR",
        "modelo_aeat": "200",
        "referencias": [
            {"referencia": "V0235-26", "fuente": "DGT", "relacion": "consulta_principal"},
            {
                "referencia": "00/03519/2022/00/00",
                "fuente": "TEAC",
                "relacion": "resolucion_soporte",
            },
        ],
        "gaps": ["mantener abstencion cuando el supuesto dependa de hechos o convenio"],
    },
    {
        "id": 9009,
        "codigo": "D-09",
        "fuente": "dgt",
        "titulo": "Servicios profesionales",
        "tema": "servicios_profesionales",
        "impuesto": "IRNR",
        "modelo_aeat": "216",
        "referencias": [
            {
                "referencia": "V0191-26",
                "fuente": "DGT",
                "relacion": "consulta_principal",
                "modelo_aeat": "216",
                "tipo_renta": "servicios_profesionales",
            }
        ],
        "gaps": ["relacionar pais, articulo y convenio antes de respuesta definitiva"],
    },
]

PILOT_LINEAS_BY_CODE = {
    item["codigo"]: item for item in PILOT_LINEAS_CRITERIO
}


def _linea_codigo(linea_id: int) -> str:
    return f"LC-{linea_id:04d}"


def _parse_linea_codigo(codigo: str) -> int | None:
    normalized = codigo.strip().upper()
    if normalized.startswith("LC-"):
        normalized = normalized[3:]
    try:
        return int(normalized)
    except ValueError:
        return None


def _infer_linea_fuente(dgt_refs: int, teac_refs: int) -> str:
    if dgt_refs and teac_refs:
        return "mixta"
    if dgt_refs:
        return "dgt"
    if teac_refs:
        return "teac"
    return "sin_fuente_doctrinal"


def _build_linea_notice(*, official_refs: int, article_links: int, safe_to_answer: bool) -> str:
    if safe_to_answer:
        return (
            "Linea consultable con evidencia oficial y relacion normativa trazable; "
            "mantener revision profesional para aplicabilidad al caso concreto."
        )
    if official_refs == 0:
        return (
            "Linea editorial o target: no hay resolucion DGT/TEAC oficial cargada "
            "con URL trazable suficiente para responder como doctrina oficial."
        )
    if article_links == 0:
        return (
            "Hay fuente DGT/TEAC trazable, pero falta anclaje robusto a articulo, "
            "impuesto o modelo; respuesta factual debe abstenerse."
        )
    return (
        "Evidencia parcial: la linea requiere revision porque no cumple todo el "
        "contrato de lineas de criterio fiscal."
    )


def _linea_payload(row) -> dict:
    official_refs = int(row["official_refs"] or 0)
    article_links = int(row["article_links"] or 0)
    complete_refs = int(row["complete_refs"] or 0)
    relation_links = int(row["relation_links"] or 0)
    source_hash = row["source_hash"]
    capture_date = row["source_capture_date"] or row["capture_date"] or row["fecha"]
    safe_to_answer = bool(
        official_refs > 0
        and complete_refs > 0
        and article_links > 0
        and relation_links > 0
        and source_hash
        and capture_date
    )
    completeness = "complete" if safe_to_answer else "partial" if official_refs > 0 else "target"
    source_url = row["source_url"]
    return {
        "codigo": _linea_codigo(int(row["id"])),
        "id": int(row["id"]),
        "fuente": _infer_linea_fuente(int(row["dgt_refs"] or 0), int(row["teac_refs"] or 0)),
        "titulo": row["titulo"],
        "tema": row["ambitos"],
        "impuesto": row["impuesto"],
        "articulo_referencia": row["articulo_referencia"],
        "modelo_aeat_referencia": row["modelo_aeat_referencia"],
        "fecha": str(row["fecha"]) if row["fecha"] else None,
        "estado_vigente": row["estado"],
        "resumen_oficial": row["criterio_dominante"],
        "source_url": source_url,
        "source_hash": source_hash,
        "capture_date": str(capture_date) if capture_date else None,
        "verified": safe_to_answer,
        "completeness": completeness,
        "safe_to_answer": safe_to_answer,
        "evidence_notice": _build_linea_notice(
            official_refs=official_refs,
            article_links=article_links,
            safe_to_answer=safe_to_answer,
        ),
        "review_required": not safe_to_answer,
        "referencias_total": int(row["refs_total"] or 0),
        "referencias_oficiales": official_refs,
        "articulos_relacionados_total": article_links,
    }


def _pilot_filter_match(definition: dict, impuesto: str | None, tema: str | None, modelo: str | None) -> bool:
    searchable = " ".join(
        str(value or "")
        for value in (
            definition["codigo"],
            definition["titulo"],
            definition["tema"],
            definition["impuesto"],
            definition["modelo_aeat"],
        )
    ).lower()
    if impuesto and impuesto.lower() not in searchable:
        return False
    if tema and tema.lower() not in searchable:
        return False
    if modelo and modelo.lower() not in searchable:
        return False
    return True


def _fetch_pilot_doc_rows(db, definition: dict) -> list[dict]:
    rows: list[dict] = []
    for reference in definition["referencias"]:
        result = db.execute(
            text(
                """
                SELECT
                    d.id AS documento_id,
                    d.referencia,
                    d.organismo_emisor,
                    d.tipo_documento,
                    d.fecha,
                    d.titulo,
                    d.url_fuente,
                    d.estado_vigencia,
                    COALESCE(d.row_completeness, 'partial') AS row_completeness,
                    n.codigo AS norma_codigo,
                    a.numero AS articulo,
                    da.metodo_enlace,
                    sr.content_hash_sha256 AS source_hash,
                    sr.fetched_at AS source_capture_date,
                    sr.dgt_url AS source_revision_url
                FROM documento_interpretativo d
                LEFT JOIN documento_articulo da ON da.documento_id = d.id
                LEFT JOIN articulo a ON a.id = da.articulo_id
                LEFT JOIN norma n ON n.id = a.norma_id
                LEFT JOIN source_revision sr
                  ON sr.source_entity_id = d.referencia
                 AND LOWER(sr.source_entity_tipo) IN (
                     'consulta', 'consulta_vinculante', 'documento', 'resolucion_teac'
                 )
                WHERE d.referencia = :referencia
                ORDER BY
                    CASE WHEN da.metodo_enlace IN ('manual', 'manual_official', 'auto_link_exact') THEN 0 ELSE 1 END,
                    n.codigo,
                    a.numero,
                    sr.fetched_at DESC
                """
            ),
            {"referencia": reference["referencia"]},
        ).mappings()
        rows.extend(dict(row) for row in result)
    return rows


def _pilot_doc_refs(rows: list[dict]) -> set[str]:
    return {str(row["referencia"]) for row in rows if row.get("referencia")}


def _pilot_expected_article_refs(definition: dict) -> list[dict]:
    return [
        reference
        for reference in definition["referencias"]
        if reference.get("norma_codigo") and reference.get("articulo")
    ]


def _first_pilot_row(rows: list[dict], key: str) -> dict | None:
    for row in rows:
        if row.get(key):
            return row
    return rows[0] if rows else None


def _pilot_article_reference(definition: dict, rows: list[dict]) -> str | None:
    expected_articles = _pilot_expected_article_refs(definition)
    if not expected_articles:
        return None
    for reference in expected_articles:
        expected_norma = reference.get("norma_codigo")
        expected_articulo = reference.get("articulo")
        for row in rows:
            if (
                row.get("referencia") == reference["referencia"]
                and row.get("norma_codigo")
                and row.get("articulo")
                and (expected_norma is None or row["norma_codigo"] == expected_norma)
                and (expected_articulo is None or row["articulo"] == expected_articulo)
            ):
                return f"{row['norma_codigo']} art. {row['articulo']}"
        if (
            reference.get("articulo_evidencia") == "official_text_audited"
            and expected_norma
            and expected_articulo
            and any(row.get("referencia") == reference["referencia"] for row in rows)
        ):
            return f"{expected_norma} art. {expected_articulo}"
    return None


def _pilot_relation_article_row(reference: dict, rows: list[dict]) -> dict | None:
    expected_norma = reference.get("norma_codigo")
    expected_articulo = reference.get("articulo")
    if not expected_norma or not expected_articulo:
        return None
    for row in rows:
        if (
            row.get("norma_codigo")
            and row.get("articulo")
            and (expected_norma is None or row["norma_codigo"] == expected_norma)
            and (expected_articulo is None or row["articulo"] == expected_articulo)
        ):
            return row
    if (
        reference.get("articulo_evidencia") == "official_text_audited"
        and expected_norma
        and expected_articulo
        and rows
    ):
        row = dict(rows[0])
        row["norma_codigo"] = expected_norma
        row["articulo"] = expected_articulo
        row["metodo_enlace"] = "official_text_audited"
        return row
    return None


def _pilot_has_persisted_article_relation(definition: dict, rows: list[dict]) -> bool:
    for reference in definition["referencias"]:
        expected_norma = reference.get("norma_codigo")
        expected_articulo = reference.get("articulo")
        if not expected_norma or not expected_articulo:
            continue
        for row in rows:
            if (
                row.get("referencia") == reference["referencia"]
                and row.get("norma_codigo") == expected_norma
                and row.get("articulo") == expected_articulo
                and row.get("metodo_enlace") != "official_text_audited"
            ):
                return True
    return False


def _pilot_has_complete_primary_reference(definition: dict, rows: list[dict]) -> bool:
    primary_refs = {
        reference["referencia"]
        for reference in definition["referencias"]
        if reference["relacion"] == "consulta_principal"
    }
    return any(
        row.get("referencia") in primary_refs
        and row.get("organismo_emisor") in DOCTRINA_FUENTES
        and row.get("url_fuente")
        and row.get("source_hash")
        and row.get("row_completeness") == "complete"
        for row in rows
    )


def _fetch_criterio_relaciones(db, linea_codigo: str) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT
                id,
                linea_codigo,
                linea_criterio_id,
                documento_referencia,
                norma_codigo,
                articulo,
                impuesto,
                modelo_aeat,
                tipo_renta,
                relacion,
                metodo_enlace,
                confianza_enlace,
                nota_limitacion,
                source_url,
                source_hash,
                capture_date,
                verified,
                completeness
            FROM criterio_relacion
            WHERE linea_codigo = :linea_codigo
            ORDER BY id ASC
            """
        ),
        {"linea_codigo": linea_codigo},
    ).mappings()
    return [dict(row) for row in rows]


def _complete_model_relation(definition: dict, relations: list[dict]) -> dict | None:
    expected_model = definition.get("modelo_aeat")
    if not expected_model:
        return None
    primary_refs = {
        reference["referencia"]
        for reference in definition["referencias"]
        if reference["relacion"] == "consulta_principal"
    }
    for relation in relations:
        if (
            relation.get("documento_referencia") in primary_refs
            and relation.get("modelo_aeat") == expected_model
            and relation.get("source_hash")
            and relation.get("capture_date")
            and relation.get("verified")
            and relation.get("completeness") == "complete"
        ):
            return relation
    return None


def _pilot_notice(definition: dict, *, has_official_source: bool, has_hash: bool) -> str:
    if not has_official_source:
        return (
            f"Linea piloto {definition['codigo']} target: referencia seleccionada, "
            "pero no hay documento oficial cargado en el corpus local."
        )
    if definition.get("_complete"):
        return (
            f"Linea piloto {definition['codigo']} completa para consulta factual acotada: "
            "fuente oficial, hash/capture_date, anclaje persistido, vigencia historica "
            "explicita y relacion modelo/supuesto persistida por curacion auditada. "
            "No extrapolar fuera del supuesto."
        )
    if not has_hash:
        return (
            f"Linea piloto {definition['codigo']} parcial: hay fuente oficial, "
            "pero falta hash/capture_date de source_revision para cerrar evidencia."
        )
    return (
        f"Linea piloto {definition['codigo']} curada parcialmente con evidencia oficial; "
        "sigue fail-closed hasta cerrar vigencia, articulo/modelo aplicable y gaps: "
        + "; ".join(definition["gaps"])
    )


def _pilot_linea_payload(definition: dict, rows: list[dict], relations: list[dict]) -> dict:
    official_refs = {
        row["referencia"]
        for row in rows
        if row.get("organismo_emisor") in DOCTRINA_FUENTES and row.get("url_fuente")
    }
    article_links = {
        (row["referencia"], row["norma_codigo"], row["articulo"])
        for row in rows
        if row.get("norma_codigo") and row.get("articulo")
    }
    source_row = _first_pilot_row(rows, "url_fuente")
    hash_row = _first_pilot_row(rows, "source_hash")
    source_hash = hash_row.get("source_hash") if hash_row else None
    capture_date = (
        hash_row.get("source_capture_date")
        if hash_row and hash_row.get("source_capture_date")
        else source_row.get("fecha")
        if source_row
        else None
    )
    has_official_source = bool(official_refs)
    verified = has_official_source and bool(source_hash)
    complete_model_relation = _complete_model_relation(definition, relations)
    if complete_model_relation and complete_model_relation.get("source_hash") != source_hash:
        complete_model_relation = None
    complete_ready = bool(
        has_official_source
        and source_hash
        and _pilot_has_complete_primary_reference(definition, rows)
        and _pilot_has_persisted_article_relation(definition, rows)
        and definition.get("vigencia_estado")
        and complete_model_relation
    )
    definition_for_notice = {**definition, "_complete": complete_ready}
    completeness = "complete" if complete_ready else "partial" if has_official_source else "target"
    modelo = (
        complete_model_relation.get("modelo_aeat")
        if complete_model_relation
        else definition["modelo_aeat"]
        if has_official_source and definition.get("modelo_evidencia") == "official_text_partial"
        else None
    )
    articulo_referencia = _pilot_article_reference(definition, rows)
    return {
        "codigo": definition["codigo"],
        "id": definition["id"],
        "fuente": definition["fuente"] if has_official_source else "sin_fuente_doctrinal",
        "titulo": definition["titulo"],
        "tema": definition["tema"],
        "impuesto": definition["impuesto"] if has_official_source else None,
        "articulo_referencia": articulo_referencia,
        "modelo_aeat_referencia": modelo,
        "fecha": str(source_row["fecha"]) if source_row and source_row.get("fecha") else None,
        "estado_vigente": (
            definition.get("vigencia_estado")
            or source_row.get("estado_vigencia")
            or "vigencia_no_determinada"
            if source_row
            else "target"
        ),
        "resumen_oficial": None,
        "source_url": source_row.get("url_fuente") if source_row else None,
        "source_hash": source_hash,
        "capture_date": str(complete_model_relation.get("capture_date") if complete_model_relation else capture_date)
        if (complete_model_relation or capture_date)
        else None,
        "verified": verified,
        "completeness": completeness,
        "safe_to_answer": complete_ready,
        "evidence_notice": _pilot_notice(
            definition_for_notice,
            has_official_source=has_official_source,
            has_hash=bool(source_hash),
        ),
        "review_required": not complete_ready,
        "referencias_total": len(definition["referencias"]),
        "referencias_oficiales": len(official_refs),
        "articulos_relacionados_total": max(len(article_links), 1 if articulo_referencia else 0),
    }


def _pilot_lineas_payload(
    db, impuesto: str | None = None, tema: str | None = None, modelo: str | None = None
) -> list[dict]:
    lineas = []
    for definition in PILOT_LINEAS_CRITERIO:
        if not _pilot_filter_match(definition, impuesto, tema, modelo):
            continue
        lineas.append(
            _pilot_linea_payload(
                definition,
                _fetch_pilot_doc_rows(db, definition),
                _fetch_criterio_relaciones(db, definition["codigo"]),
            )
        )
    return lineas


def _pilot_relaciones_payload(definition: dict, rows: list[dict], model_relations: list[dict]) -> list[dict]:
    relaciones = []
    doc_refs = _pilot_doc_refs(rows)
    line_complete = _pilot_linea_payload(definition, rows, model_relations)["completeness"] == "complete"
    complete_model_relation = _complete_model_relation(definition, model_relations)
    hash_row_for_relation = _first_pilot_row(rows, "source_hash")
    if (
        complete_model_relation
        and hash_row_for_relation
        and complete_model_relation.get("source_hash") != hash_row_for_relation.get("source_hash")
    ):
        complete_model_relation = None
    definition_has_expected_article = any(
        reference.get("norma_codigo") or reference.get("articulo")
        for reference in definition["referencias"]
    )
    for reference in definition["referencias"]:
        matching_rows = [row for row in rows if row.get("referencia") == reference["referencia"]]
        row = _first_pilot_row(matching_rows, "url_fuente")
        hash_row = _first_pilot_row(matching_rows, "source_hash")
        article_row = (
            None
            if definition_has_expected_article
            and not (reference.get("norma_codigo") or reference.get("articulo"))
            else _pilot_relation_article_row(reference, matching_rows)
        )
        official = bool(row and row.get("organismo_emisor") in DOCTRINA_FUENTES and row.get("url_fuente"))
        article_ready = bool(article_row and article_row.get("norma_codigo") and article_row.get("articulo"))
        relation_model = (
            complete_model_relation.get("modelo_aeat")
            if complete_model_relation
            and complete_model_relation.get("documento_referencia") == reference["referencia"]
            else reference.get("modelo_aeat")
            if official
            and (reference.get("modelo_evidencia") or definition.get("modelo_evidencia") == "official_text_partial")
            else None
        )
        verified = bool(
            official
            and hash_row
            and hash_row.get("source_hash")
            and article_ready
            and complete_model_relation
            and complete_model_relation.get("documento_referencia") == reference["referencia"]
        )
        relation_complete = bool(
            verified
            and line_complete
            and reference["relacion"] == "consulta_principal"
        )
        relaciones.append(
            {
                "linea_criterio_id": definition["id"],
                "documento_referencia": reference["referencia"],
                "fuente": row.get("organismo_emisor") if row else reference["fuente"],
                "source_url": row.get("url_fuente") if row else None,
                "capture_date": (
                    str(hash_row["source_capture_date"])
                    if hash_row and hash_row.get("source_capture_date")
                    else str(row["fecha"])
                    if row and row.get("fecha")
                    else None
                ),
                "norma_codigo": article_row.get("norma_codigo") if article_row else None,
                "articulo": article_row.get("articulo") if article_row else None,
                "modelo_aeat": relation_model,
                "tipo_renta": reference.get("tipo_renta"),
                "relacion": reference["relacion"],
                "nota_limitacion": (
                    "Relacion principal completa para consulta factual acotada: fuente, hash, "
                    "articulo, vigencia y modelo/supuesto persistido; no extrapolar fuera del supuesto."
                    if relation_complete
                    else
                    "Relacion trazada a documento y articulo desde texto oficial auditado; "
                    "la linea piloto sigue partial hasta cerrar vigencia, modelo y supuestos."
                    if article_row and article_row.get("metodo_enlace") == "official_text_audited"
                    else "Relacion trazada a documento y articulo; la linea piloto sigue partial "
                    "hasta cerrar vigencia, modelo y supuestos."
                    if verified
                    else "Relacion target/parcial: falta documento oficial cargado, hash o articulo trazable."
                ),
                "verified": verified,
                "completeness": (
                    "complete"
                    if relation_complete
                    else "partial"
                    if reference["referencia"] in doc_refs
                    else "target"
                ),
            }
        )
    return relaciones


def _lineas_base_sql(where_clause: str) -> str:
    return f"""
        SELECT
            l.id,
            l.titulo,
            l.cuestion_practica,
            l.criterio_dominante,
            CAST(l.ambitos AS TEXT) AS ambitos,
            l.estado,
            l.ultimo_cambio AS fecha,
            COUNT(DISTINCT r.id) AS refs_total,
            SUM(CASE WHEN UPPER(COALESCE(d.organismo_emisor, r.organismo_emisor, '')) = 'DGT' THEN 1 ELSE 0 END) AS dgt_refs,
            SUM(CASE WHEN UPPER(COALESCE(d.organismo_emisor, r.organismo_emisor, '')) = 'TEAC' THEN 1 ELSE 0 END) AS teac_refs,
            SUM(CASE
                WHEN UPPER(COALESCE(d.organismo_emisor, r.organismo_emisor, '')) IN ('DGT', 'TEAC')
                 AND d.url_fuente IS NOT NULL
                THEN 1 ELSE 0 END
            ) AS official_refs,
            SUM(CASE
                WHEN UPPER(COALESCE(d.organismo_emisor, r.organismo_emisor, '')) IN ('DGT', 'TEAC')
                 AND d.url_fuente IS NOT NULL
                 AND COALESCE(d.row_completeness, 'partial') = 'complete'
                THEN 1 ELSE 0 END
            ) AS complete_refs,
            COUNT(DISTINCT da.articulo_id) AS article_links,
            COUNT(DISTINCT CASE
                WHEN cr.verified = true
                 AND cr.completeness = 'complete'
                 AND cr.modelo_aeat IS NOT NULL
                 AND cr.impuesto IS NOT NULL
                 AND cr.source_hash = sr.content_hash_sha256
                 AND cr.capture_date IS NOT NULL
                THEN cr.id END
            ) AS relation_links,
            MIN(CASE
                WHEN UPPER(COALESCE(d.organismo_emisor, r.organismo_emisor, '')) IN ('DGT', 'TEAC')
                 AND d.url_fuente IS NOT NULL
                THEN d.url_fuente END
            ) AS source_url,
            MIN(CASE
                WHEN UPPER(COALESCE(d.organismo_emisor, r.organismo_emisor, '')) IN ('DGT', 'TEAC')
                 AND d.url_fuente IS NOT NULL
                THEN sr.content_hash_sha256 END
            ) AS source_hash,
            MIN(CASE
                WHEN UPPER(COALESCE(d.organismo_emisor, r.organismo_emisor, '')) IN ('DGT', 'TEAC')
                 AND d.url_fuente IS NOT NULL
                THEN CAST(sr.fetched_at AS TEXT) END
            ) AS source_capture_date,
            MIN(CASE
                WHEN UPPER(COALESCE(d.organismo_emisor, r.organismo_emisor, '')) IN ('DGT', 'TEAC')
                 AND d.url_fuente IS NOT NULL
                THEN COALESCE(CAST(d.fecha_publicacion AS TEXT), CAST(d.fecha AS TEXT)) END
            ) AS capture_date,
            MIN(CASE
                WHEN n.codigo IS NOT NULL AND a.numero IS NOT NULL
                THEN n.codigo || ' art. ' || a.numero END
            ) AS articulo_referencia,
            MIN(CASE
                WHEN cr.verified = true AND cr.completeness = 'complete'
                 AND cr.source_hash = sr.content_hash_sha256
                 AND cr.capture_date IS NOT NULL
                THEN cr.impuesto END
            ) AS impuesto,
            MIN(CASE
                WHEN cr.verified = true AND cr.completeness = 'complete'
                 AND cr.source_hash = sr.content_hash_sha256
                 AND cr.capture_date IS NOT NULL
                THEN cr.modelo_aeat END
            ) AS modelo_aeat_referencia
        FROM linea_criterio l
        LEFT JOIN linea_criterio_referencia r ON r.linea_id = l.id
        LEFT JOIN documento_interpretativo d ON d.referencia = r.documento_referencia
        LEFT JOIN source_revision sr
          ON sr.source_entity_id = d.referencia
         AND LOWER(sr.source_entity_tipo) IN (
             'consulta', 'consulta_vinculante', 'documento', 'resolucion_teac'
         )
        LEFT JOIN documento_articulo da ON da.documento_id = d.id
        LEFT JOIN articulo a ON a.id = da.articulo_id
        LEFT JOIN norma n ON n.id = a.norma_id
        LEFT JOIN criterio_relacion cr ON cr.linea_criterio_id = l.id
         AND cr.documento_referencia = r.documento_referencia
        WHERE {where_clause}
        GROUP BY l.id, l.titulo, l.cuestion_practica, l.criterio_dominante, l.ambitos, l.estado, l.ultimo_cambio
    """


def _lineas_filter_sql(impuesto: str | None, tema: str | None, modelo: str | None) -> tuple[str, dict]:
    filters = ["l.activo = true"]
    params: dict = {}
    if tema:
        filters.append(
            "(LOWER(COALESCE(CAST(l.ambitos AS TEXT), '')) LIKE LOWER(:tema) "
            "OR LOWER(l.titulo) LIKE LOWER(:tema) "
            "OR LOWER(l.cuestion_practica) LIKE LOWER(:tema))"
        )
        params["tema"] = f"%{tema}%"
    if impuesto:
        filters.append(
            "(LOWER(COALESCE(l.titulo, '')) LIKE LOWER(:impuesto) "
            "OR LOWER(COALESCE(l.cuestion_practica, '')) LIKE LOWER(:impuesto) "
            "OR LOWER(COALESCE(d.texto, '')) LIKE LOWER(:impuesto))"
        )
        params["impuesto"] = f"%{impuesto}%"
    if modelo:
        filters.append(
            "(LOWER(COALESCE(l.titulo, '')) LIKE LOWER(:modelo) "
            "OR LOWER(COALESCE(l.cuestion_practica, '')) LIKE LOWER(:modelo) "
            "OR LOWER(COALESCE(d.texto, '')) LIKE LOWER(:modelo))"
        )
        params["modelo"] = f"%modelo {modelo}%"
    return " AND ".join(filters), params


def _record_lineas_audit(
    request: Request,
    *,
    path: str,
    query_text: str,
    tool_name: str,
    retrieved_chunks: list[dict],
    safe_to_answer: bool,
):
    _record_doctrina_query_audit(
        request,
        path=path,
        query_text=query_text,
        tool_name=tool_name,
        retrieved_chunks=retrieved_chunks,
        response_summary=f"lineas={len(retrieved_chunks)} safe_to_answer={safe_to_answer}",
        confidence={
            "score": 0.9 if safe_to_answer else 0.2,
            "label": "alta" if safe_to_answer else "baja",
            "review_required": not safe_to_answer,
        },
        completeness="completa" if safe_to_answer else "parcial",
        verified=safe_to_answer,
    )


@router.get(
    "/lineas/coverage",
    operation_id="doctrina_coverage",
    response_model=DoctrinaCoverageResponse,
)
async def doctrina_coverage(request: Request):
    with db_session() as db:
        row = db.execute(
            text(
                f"""
                SELECT
                    COUNT(*) AS lineas_total,
                    SUM(CASE WHEN dgt_refs > 0 OR teac_refs > 0 THEN 1 ELSE 0 END) AS lineas_con_dgt_teac,
                    SUM(CASE WHEN official_refs > 0 THEN 1 ELSE 0 END) AS lineas_con_fuente_oficial,
                    SUM(CASE WHEN article_links > 0 THEN 1 ELSE 0 END) AS lineas_con_articulo,
                    0 AS lineas_complete
                FROM (
                    {_lineas_base_sql("l.activo = true")}
                ) base
                """
            )
        ).mappings().one()
        pilot_lineas = _pilot_lineas_payload(db)

        payload = {
            "familia": "doctrina_administrativa_dgt_teac",
            "estado": "implemented_partial",
            "fuentes": ["DGT", "TEAC"],
            "lineas_total": int(row["lineas_total"] or 0) + len(pilot_lineas),
            "lineas_con_dgt_teac": int(row["lineas_con_dgt_teac"] or 0)
            + sum(1 for item in pilot_lineas if item["referencias_oficiales"] > 0),
            "lineas_con_fuente_oficial": int(row["lineas_con_fuente_oficial"] or 0)
            + sum(1 for item in pilot_lineas if item["source_url"]),
            "lineas_con_articulo": int(row["lineas_con_articulo"] or 0)
            + sum(1 for item in pilot_lineas if item["articulo_referencia"]),
            "lineas_complete": sum(1 for item in pilot_lineas if item["completeness"] == "complete"),
            "safe_to_answer": False,
            "evidence_notice": (
                "DGT/TEAC existen como superficie parcial: corpus y lineas editoriales "
                "pueden estar disponibles, pero la familia no esta completa hasta mapear "
                "lineas por impuesto, articulo, modelo, tema y evidencia oficial."
            ),
            "review_required": True,
        }
        _record_lineas_audit(
            request,
            path="/v1/doctrina/lineas/coverage",
            query_text="coverage",
            tool_name="doctrina_coverage",
            retrieved_chunks=[payload],
            safe_to_answer=False,
        )
        return payload


@router.get(
    "/lineas",
    operation_id="buscar_lineas_criterio",
    response_model=DoctrinaLineaCriterioListResponse,
)
async def buscar_lineas_criterio(
    request: Request,
    impuesto: str | None = Query(None, description="Filtro exploratorio por impuesto"),
    tema: str | None = Query(None, description="Filtro exploratorio por tema"),
    modelo: str | None = Query(None, description="Filtro exploratorio por modelo AEAT"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    where_clause, params = _lineas_filter_sql(impuesto, tema, modelo)
    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT * FROM (
                    {_lineas_base_sql(where_clause)}
                ) base
                ORDER BY id ASC
                """
            ),
            params,
        ).mappings()
        all_lineas = [_linea_payload(row) for row in rows]
        all_lineas.extend(_pilot_lineas_payload(db, impuesto, tema, modelo))
        total = len(all_lineas)
        lineas = all_lineas[offset : offset + limit]

    safe_to_answer = bool(lineas) and all(item["safe_to_answer"] for item in lineas)
    response = {
        "lineas": lineas,
        "total": int(total or 0),
        "safe_to_answer": safe_to_answer,
        "evidence_notice": (
            "Listado exploratorio de lineas de criterio. Use safe_to_answer de cada "
            "linea antes de tratarla como doctrina oficial utilizable."
        ),
        "review_required": not safe_to_answer,
    }
    _record_lineas_audit(
        request,
        path="/v1/doctrina/lineas",
        query_text=f"impuesto={impuesto or ''};tema={tema or ''};modelo={modelo or ''}",
        tool_name="buscar_lineas_criterio",
        retrieved_chunks=lineas,
        safe_to_answer=safe_to_answer,
    )
    return response


@router.get(
    "/lineas/{codigo}/relaciones",
    operation_id="criterio_relacionado_con_modelo",
    response_model=DoctrinaLineaRelacionResponse,
)
async def criterio_relacionado_con_modelo(request: Request, codigo: str):
    pilot_definition = PILOT_LINEAS_BY_CODE.get(codigo.strip().upper())
    if pilot_definition is not None:
        with db_session() as db:
            rows = _fetch_pilot_doc_rows(db, pilot_definition)
            relaciones = _pilot_relaciones_payload(
                pilot_definition,
                rows,
                _fetch_criterio_relaciones(db, pilot_definition["codigo"]),
            )
        response = {
            "codigo": pilot_definition["codigo"],
            "relaciones": relaciones,
            "safe_to_answer": False,
            "evidence_notice": (
                "Relaciones piloto DGT/TEAC consultables parcialmente; "
                "no usar como doctrina oficial cerrada sin curacion completa."
            ),
            "review_required": True,
        }
        _record_lineas_audit(
            request,
            path=f"/v1/doctrina/lineas/{codigo}/relaciones",
            query_text=codigo,
            tool_name="criterio_relacionado_con_modelo",
            retrieved_chunks=relaciones,
            safe_to_answer=False,
        )
        return response

    linea_id = _parse_linea_codigo(codigo)
    if linea_id is None:
        raise HTTPException(status_code=404, detail={"error": "Linea de criterio no encontrada"})

    with db_session() as db:
        exists = db.execute(
            text("SELECT id FROM linea_criterio WHERE id = :linea_id AND activo = true"),
            {"linea_id": linea_id},
        ).mappings().first()
        if not exists:
            raise HTTPException(status_code=404, detail={"error": "Linea de criterio no encontrada"})

        rows = db.execute(
            text(
                """
                SELECT
                    r.linea_id,
                    r.documento_referencia,
                    COALESCE(d.organismo_emisor, r.organismo_emisor) AS fuente,
                    d.url_fuente AS source_url,
                    COALESCE(
                        CAST(d.fecha_publicacion AS TEXT),
                        CAST(d.fecha AS TEXT),
                        CAST(r.fecha AS TEXT)
                    ) AS capture_date,
                    n.codigo AS norma_codigo,
                    a.numero AS articulo,
                    r.rol_en_linea,
                    COALESCE(d.row_completeness, 'partial') AS row_completeness,
                    sr.content_hash_sha256 AS source_hash,
                    sr.fetched_at AS source_capture_date,
                    cr.modelo_aeat,
                    cr.tipo_renta,
                    cr.source_hash AS relacion_source_hash,
                    cr.capture_date AS relacion_capture_date,
                    cr.verified AS relacion_verified,
                    cr.completeness AS relacion_completeness,
                    cr.nota_limitacion
                FROM linea_criterio_referencia r
                LEFT JOIN documento_interpretativo d ON d.referencia = r.documento_referencia
                LEFT JOIN source_revision sr
                  ON sr.source_entity_id = d.referencia
                 AND LOWER(sr.source_entity_tipo) IN (
                     'consulta', 'consulta_vinculante', 'documento', 'resolucion_teac'
                 )
                LEFT JOIN documento_articulo da ON da.documento_id = d.id
                LEFT JOIN articulo a ON a.id = da.articulo_id
                LEFT JOIN norma n ON n.id = a.norma_id
                LEFT JOIN criterio_relacion cr ON cr.linea_criterio_id = r.linea_id
                 AND cr.documento_referencia = r.documento_referencia
                WHERE r.linea_id = :linea_id
                ORDER BY r.orden ASC, n.codigo, a.numero
                """
            ),
            {"linea_id": linea_id},
        ).mappings()

        relaciones = []
        for row in rows:
            official = row["fuente"] in DOCTRINA_FUENTES and row["source_url"] is not None
            article_ready = row["norma_codigo"] is not None and row["articulo"] is not None
            verified = bool(
                official
                and row["row_completeness"] == "complete"
                and article_ready
                and row["source_hash"]
                and row["source_capture_date"]
                and row["modelo_aeat"]
                and row["relacion_source_hash"] == row["source_hash"]
                and row["relacion_capture_date"]
                and row["relacion_verified"]
                and row["relacion_completeness"] == "complete"
            )
            relaciones.append(
                {
                    "linea_criterio_id": int(row["linea_id"]),
                    "documento_referencia": row["documento_referencia"],
                    "fuente": row["fuente"],
                    "source_url": row["source_url"],
                    "capture_date": (
                        str(row["source_capture_date"])
                        if row["source_capture_date"]
                        else str(row["capture_date"])
                        if row["capture_date"]
                        else None
                    ),
                    "norma_codigo": row["norma_codigo"],
                    "articulo": row["articulo"],
                    "modelo_aeat": row["modelo_aeat"],
                    "tipo_renta": row["tipo_renta"],
                    "relacion": row["rol_en_linea"] or "soporte",
                    "nota_limitacion": (
                        row["nota_limitacion"] or "Relacion verificada con evidencia completa."
                        if verified
                        else "Relacion parcial: falta fuente DGT/TEAC oficial completa, articulo o modelo trazable."
                    ),
                    "verified": verified,
                    "completeness": "complete" if verified else "partial" if official else "target",
                }
            )

    safe_to_answer = bool(relaciones) and all(item["verified"] for item in relaciones)
    response = {
        "codigo": _linea_codigo(linea_id),
        "relaciones": relaciones,
        "safe_to_answer": safe_to_answer,
        "evidence_notice": (
            "Relaciones de criterio con evidencia trazable."
            if safe_to_answer
            else "Relaciones consultables parcialmente; no usar como doctrina oficial cerrada sin revision."
        ),
        "review_required": not safe_to_answer,
    }
    _record_lineas_audit(
        request,
        path=f"/v1/doctrina/lineas/{codigo}/relaciones",
        query_text=codigo,
        tool_name="criterio_relacionado_con_modelo",
        retrieved_chunks=relaciones,
        safe_to_answer=safe_to_answer,
    )
    return response


@router.get(
    "/lineas/{codigo}",
    operation_id="detalle_linea_criterio_doctrina",
    response_model=DoctrinaLineaCriterioItem,
)
async def detalle_linea_criterio_doctrina(request: Request, codigo: str):
    pilot_definition = PILOT_LINEAS_BY_CODE.get(codigo.strip().upper())
    if pilot_definition is not None:
        with db_session() as db:
            payload = _pilot_linea_payload(
                pilot_definition,
                _fetch_pilot_doc_rows(db, pilot_definition),
                _fetch_criterio_relaciones(db, pilot_definition["codigo"]),
            )
        _record_lineas_audit(
            request,
            path=f"/v1/doctrina/lineas/{codigo}",
            query_text=codigo,
            tool_name="detalle_linea_criterio",
            retrieved_chunks=[payload],
            safe_to_answer=payload["safe_to_answer"],
        )
        return payload

    linea_id = _parse_linea_codigo(codigo)
    if linea_id is None:
        raise HTTPException(status_code=404, detail={"error": "Linea de criterio no encontrada"})

    with db_session() as db:
        row = db.execute(
            text(_lineas_base_sql("l.activo = true AND l.id = :linea_id")),
            {"linea_id": linea_id},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail={"error": "Linea de criterio no encontrada"})

    payload = _linea_payload(row)
    _record_lineas_audit(
        request,
        path=f"/v1/doctrina/lineas/{codigo}",
        query_text=codigo,
        tool_name="detalle_linea_criterio",
        retrieved_chunks=[payload],
        safe_to_answer=payload["safe_to_answer"],
    )
    return payload


@router.get(
    "/buscar",
    operation_id="buscar_doctrina",
    response_model=DoctrinaSearchResponse,
    summary="Buscar doctrina interpretativa",
)
async def buscar_doctrina(
    request: Request,
    q: str = Query(
        ..., min_length=1, description="Termino de busqueda en texto de doctrina"
    ),
    tipo: str | None = Query(
        None,
        description="Filtrar por tipo (consulta_vinculante, resolucion_teac, etc.)",
    ),
    desde: str | None = Query(None, description="Fecha minima (YYYY-MM-DD)"),
    organismo_emisor: str | None = Query(
        None, description="Filtrar por organismo (DGT, TEAC, etc.)"
    ),
    include_boe: bool = Query(True, description="Incluir normas BOE relacionadas cuando apliquen"),
):
    with db_session() as db:
        is_postgres = db.bind.dialect.name == "postgresql"

        if is_postgres:
            result = _buscar_doctrina_pg(db, q, tipo, desde, organismo_emisor)
        else:
            result = _buscar_doctrina_sqlite(db, q, tipo, desde, organismo_emisor)

        if include_boe and tipo is None and (organismo_emisor is None or organismo_emisor.upper() == "BOE"):
            result["resultados"].extend(_buscar_normas_boe(db, q))

        get_query_audit_service().record_query(
            request_id=get_request_id(request),
            user_id=get_user_id(request),
            path="/v1/doctrina/buscar",
            query_text=q,
            retrieved_chunks=_build_doctrina_audit_chunks(result),
            response_summary=f"resultados={len(result.get('resultados', []))}",
        )
        return result


def _buscar_doctrina_pg(db, q, tipo, desde, organismo_emisor):
    """Postgres branch: search over documento_fragmento chunks with ts_rank.

    Falls back to direct search on documento_interpretativo if the
    documento_fragmento table does not exist (not yet backfilled).
    """
    params: dict = {}
    tsquery_str, _ = _build_tsquery_sql(q)
    use_ts_rank = bool(tsquery_str)

    exact_reference = q.strip()

    if use_ts_rank:
        chunk_filter = (
            "(df.search_vector @@ ("
            + tsquery_str
            + ") OR LOWER(d.referencia) = LOWER(:exact_referencia))"
        )
        rank_expr = (
            "CASE WHEN LOWER(d.referencia) = LOWER(:exact_referencia) THEN 1.0 "
            "ELSE ts_rank(df.search_vector, ("
            + tsquery_str
            + ")) END"
        )
        params["exact_referencia"] = exact_reference
    else:
        chunk_filter = "(df.texto ILIKE :term OR d.titulo ILIKE :term OR d.referencia ILIKE :term)"
        params["term"] = f"%{q}%"
        rank_expr = "0.0"

    chunk_filters = [chunk_filter, "df.documento_origen_tipo = 'doctrina'"]

    if tipo is not None:
        chunk_filters.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo
    if desde is not None:
        chunk_filters.append("d.fecha >= :desde")
        params["desde"] = desde
    if organismo_emisor is not None:
        chunk_filters.append("LOWER(d.organismo_emisor) = LOWER(:organismo_emisor)")
        params["organismo_emisor"] = organismo_emisor

    where_clause = " AND ".join(chunk_filters)

    try:
        query = text(
            f"""
            SELECT
                df.documento_origen_id AS d_id,
                d.referencia,
                d.tipo_documento,
                d.organismo_emisor,
                d.fecha,
                d.titulo,
                d.url_fuente,
                df.texto AS chunk_texto,
                df.id AS chunk_id,
                {rank_expr} AS chunk_rank,
                MAX(da.confianza_enlace) AS nivel_enlace,
                n.codigo AS norma,
                a.numero
            FROM documento_fragmento df
            JOIN documento_interpretativo d ON d.id = df.documento_origen_id
            LEFT JOIN documento_articulo da ON da.documento_id = d.id
            LEFT JOIN articulo a ON a.id = da.articulo_id
            LEFT JOIN norma n ON n.id = a.norma_id
            WHERE {where_clause}
            GROUP BY d.id, df.id, df.texto, n.codigo, a.numero
            ORDER BY chunk_rank DESC
            LIMIT 20
            """
        )

        rows = db.execute(query, params).mappings()
        results = []
        for row in rows:
            chunk_rank = row.get("chunk_rank")
            if chunk_rank is not None and use_ts_rank:
                has_chunks = bool(row.get("chunk_id"))
                chunk_rank = _chunk_rank_boost(has_chunks, float(chunk_rank))

            chunk_texto = row.get("chunk_texto")
            fragmento = None
            if chunk_texto and use_ts_rank:
                fragmento = _build_fragment(chunk_texto, q)
            elif chunk_texto:
                fragmento = chunk_texto[:220] + ("..." if len(chunk_texto) > 220 else "")

            results.append(_doctrina_result_payload(row, fragmento or ""))

        results = _normalize_doctrina_results(q, results)

        if not results:
            return _buscar_doctrina_pg_fallback(
                db, q, tipo, desde, organismo_emisor, params, use_ts_rank
            )
        return {"q": q, "resultados": results}

    except Exception:
        # documento_fragmento table does not exist — fall back to direct search
        return _buscar_doctrina_pg_fallback(db, q, tipo, desde, organismo_emisor, params, use_ts_rank)


def _buscar_doctrina_pg_fallback(db, q, tipo, desde, organismo_emisor, params, use_ts_rank):
    """Fallback search over documento_interpretativo when documento_fragmento is missing."""
    fallback_params: dict = {}
    exact_reference = q.strip()
    if use_ts_rank:
        tsquery_str, _ = _build_tsquery_sql(q)
        search_filter = (
            "(d.search_vector @@ ("
            + tsquery_str
            + ") OR LOWER(d.referencia) = LOWER(:exact_referencia))"
        )
        rank_expr = (
            "CASE WHEN LOWER(d.referencia) = LOWER(:exact_referencia) THEN 1.0 "
            "ELSE ts_rank(d.search_vector, ("
            + tsquery_str
            + ")) END"
        )
        fallback_params["exact_referencia"] = exact_reference
    else:
        search_filter = "(LOWER(d.texto) LIKE LOWER(:term) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term) OR LOWER(d.referencia) LIKE LOWER(:term))"
        fallback_params["term"] = f"%{q}%"
        rank_expr = "0.0"

    filters = [search_filter]
    if tipo is not None:
        filters.append("d.tipo_documento = :tipo")
        fallback_params["tipo"] = tipo
    if desde is not None:
        filters.append("d.fecha >= :desde")
        fallback_params["desde"] = desde
    if organismo_emisor is not None:
        filters.append("LOWER(d.organismo_emisor) = LOWER(:organismo_emisor)")
        fallback_params["organismo_emisor"] = organismo_emisor

    where_clause = " AND ".join(filters)

    query = text(
        f"""
        SELECT
            d.id,
            d.referencia,
            d.tipo_documento,
            d.organismo_emisor,
            d.fecha,
            d.titulo,
            d.texto,
            d.url_fuente,
            {rank_expr} AS chunk_rank,
            MAX(da.confianza_enlace) AS nivel_enlace,
            n.codigo AS norma,
            a.numero
        FROM documento_interpretativo d
        LEFT JOIN documento_articulo da ON da.documento_id = d.id
        LEFT JOIN articulo a ON a.id = da.articulo_id
        LEFT JOIN norma n ON n.id = a.norma_id
        WHERE {where_clause}
        GROUP BY d.id, d.referencia, d.tipo_documento, d.organismo_emisor, d.fecha, d.titulo, d.texto, d.url_fuente, n.codigo, a.numero
        ORDER BY chunk_rank DESC
        LIMIT 20
        """
    )

    rows = db.execute(query, fallback_params).mappings()
    results = []
    for row in rows:
        chunk_rank = row.get("chunk_rank")
        if chunk_rank is not None and use_ts_rank:
            chunk_rank = float(chunk_rank)

        texto = row["texto"] or ""
        results.append(
            _doctrina_result_payload(row, _build_fragment(texto, q) if texto else "")
        )

    return {"q": q, "resultados": _normalize_doctrina_results(q, results)}


def _buscar_doctrina_sqlite(db, q, tipo, desde, organismo_emisor):
    """SQLite branch: legacy ILIKE search over documento_interpretativo."""
    params: dict = {"term_like": f"%{q}%"}
    where_parts = [
        "(LOWER(d.texto) LIKE LOWER(:term_like) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term_like) OR LOWER(d.referencia) LIKE LOWER(:term_like))"
    ]

    if tipo is not None:
        where_parts.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo
    if desde is not None:
        where_parts.append("d.fecha >= :desde")
        params["desde"] = desde
    if organismo_emisor is not None:
        where_parts.append("LOWER(d.organismo_emisor) = LOWER(:organismo_emisor)")
        params["organismo_emisor"] = organismo_emisor

    where_clause = " AND ".join(where_parts)

    query = text(
        f"""
        SELECT
            d.referencia,
            d.tipo_documento,
            d.organismo_emisor,
            d.fecha,
            d.titulo,
            d.texto,
            d.url_fuente,
            n.codigo AS norma,
            a.numero,
            MAX(da.confianza_enlace) AS nivel_enlace
        FROM documento_interpretativo d
        LEFT JOIN documento_articulo da ON da.documento_id = d.id
        LEFT JOIN articulo a ON a.id = da.articulo_id
        LEFT JOIN norma n ON n.id = a.norma_id
        WHERE {where_clause}
        GROUP BY d.id, d.referencia, d.tipo_documento, d.organismo_emisor, d.fecha, d.titulo, d.texto, d.url_fuente, n.codigo, a.numero
        ORDER BY d.fecha DESC
        LIMIT 20
        """
    )

    rows = db.execute(query, params).mappings()
    results = []
    for row in rows:
        texto = row["texto"] or ""
        results.append(
            _doctrina_result_payload(
                row, texto[:220] + ("..." if len(texto) > 220 else "")
            )
        )

    return {"q": q, "resultados": _normalize_doctrina_results(q, results)}


@router.get(
    "/{referencia:path}",
    operation_id="get_doctrina",
    response_model=DoctrinaDetailSchema,
)
async def get_doctrina(request: Request, referencia: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                SELECT
                    d.id,
                    d.referencia,
                    d.tipo_documento,
                    d.organismo_emisor,
                    d.fecha,
                    d.url_fuente,
                    d.texto
                FROM documento_interpretativo d
                WHERE d.referencia = :referencia
                LIMIT 1
                """
                ),
                {"referencia": referencia},
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=404, detail={"error": "Documento no encontrado"}
            )

        linked_articles = list(
            db.execute(
                text(
                    """
                    SELECT
                        n.codigo AS norma,
                        a.numero,
                        da.metodo_enlace,
                        da.confianza_enlace
                    FROM documento_articulo da
                    JOIN articulo a ON a.id = da.articulo_id
                    JOIN norma n ON n.id = a.norma_id
                    WHERE da.documento_id = :documento_id
                    ORDER BY da.confianza_enlace DESC, n.codigo, a.numero
                    """
                ),
                {"documento_id": row["id"]},
            ).mappings()
        )

        has_any_anchor = bool(linked_articles)
        has_exact_anchor = _has_exact_anchor(linked_articles)

        payload = {
            "referencia": row["referencia"],
            "tipo_documento": row["tipo_documento"],
            "organismo_emisor": row["organismo_emisor"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "url_fuente": row["url_fuente"],
            "texto": row["texto"],
            "articulos_relacionados": [
                {
                    "norma": item["norma"],
                    "numero": item["numero"],
                    "metodo_enlace": item["metodo_enlace"],
                    "confianza_enlace": float(item["confianza_enlace"]),
                }
                for item in linked_articles
            ],
            "confianza": {
                "nivel": 2 if has_exact_anchor else (1 if has_any_anchor else 0),
                "fuentes": [row["referencia"]],
                "aviso": None
                if has_any_anchor
                else "Criterio sin anclaje normativo suficiente",
            },
        }
        _record_doctrina_query_audit(
            request,
            path=f"/v1/doctrina/{referencia}",
            query_text=referencia,
            tool_name="get_doctrina",
            retrieved_chunks=[
                {
                    "referencia": row["referencia"],
                    "tipo_documento": row["tipo_documento"],
                    "organismo_emisor": row["organismo_emisor"],
                    "norma": item["norma"],
                    "numero": item["numero"],
                }
                for item in linked_articles
            ],
            response_summary=f"articulos_relacionados={len(linked_articles)}",
            confidence={
                "score": 0.9 if has_exact_anchor else (0.5 if has_any_anchor else 0.0),
                "label": "alta" if has_exact_anchor else ("media" if has_any_anchor else "baja"),
            },
            completeness="completa" if has_exact_anchor else "parcial",
            verified=has_exact_anchor,
        )
        return payload


@router.get("/buscar/hybrid", operation_id="buscar_doctrina_hybrid")
async def buscar_doctrina_hybrid(
    q: str = Query(..., min_length=1, description="Termino de busqueda en texto de doctrina"),
    tipo: str | None = Query(None, description="Filtrar por tipo (consulta_vinculante, resolucion_teac, etc.)"),
    desde: str | None = Query(None, description="Fecha minima (YYYY-MM-DD)"),
    organismo_emisor: str | None = Query(None, description="Filtrar por organismo (DGT, TEAC, etc.)"),
    hybrid_weight: float = Query(0.3, ge=0.0, le=1.0, description="Peso busqueda vectorial (0.0=fulltext, 0.3=optimo, 1.0=vectorial)"),
    limit: int = Query(10, ge=1, le=50, description="Numero maximo de resultados"),
):
    result = hybrid_search_doctrina(
        q, tipo, desde, organismo_emisor, hybrid_weight, limit
    )
    return JSONResponse(content=result)
