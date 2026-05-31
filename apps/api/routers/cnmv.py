from db import db_session
from fastapi import APIRouter, HTTPException, Query, Request
from schemas import (
    CNMVCoverageResponse,
    CNMVObligationLinkResponse,
    CNMVRegulationLinkResponse,
    CNMVVersionResponse,
    DocInterpretativoDetail,
    DocInterpretativoListResponse,
)
from sqlalchemy import text

from routers.retrieval_audit import record_retrieval_query_audit

router = APIRouter(prefix="/v1/cnmv", tags=["cnmv"])

CNMV_CURRENT_VIGENCIA_STATES = ("vigente", "vigente_modificado")
CNMV_COVERAGE_NOTE = (
    "CNMV devuelve el corpus oficial cargado en ESData; no encontrar un documento "
    "puede significar no cargado, no inexistente. Por defecto se excluyen documentos "
    "derogados; use vigencia=all o vigencia=derogado para auditoria historica."
)

CNMV_SOURCE_FAMILIES = [
    {
        "family_id": "circulares",
        "nombre": "Circulares CNMV",
        "source_url": "https://www.cnmv.es/portal/Legislacion/Circulares",
        "loaded_tipo_documentos": ["circular_cnmv", "circular"],
        "coverage_status": "partial_loaded",
        "contract_note": (
            "Cargado parcialmente desde el indice oficial de circulares. "
            "El conteo cargado no representa el universo completo CNMV."
        ),
    },
    {
        "family_id": "documentos_cnmv_genericos",
        "nombre": "Documentos CNMV genericos cargados",
        "source_url": "https://www.cnmv.es/Portal/Menu/Legislacion?lang=es",
        "loaded_tipo_documentos": ["documento_cnmv"],
        "coverage_status": "partial_generic",
        "contract_note": (
            "Documentos oficiales CNMV sin familia especifica normalizada. "
            "No debe usarse como prueba de cobertura completa de guias, consultas o modelos."
        ),
    },
    {
        "family_id": "guias_tecnicas",
        "nombre": "Guias tecnicas CNMV",
        "source_url": "https://www.cnmv.es/portal/legislacion/guias-tecnicas?lang=es",
        "loaded_tipo_documentos": ["guia_tecnica_cnmv"],
        "coverage_status": "partial_loaded",
        "contract_note": (
            "Ingestion dedicada desde la pagina oficial de guias tecnicas. "
            "Son criterios de interpretacion/supervision, no norma primaria."
        ),
    },
    {
        "family_id": "preguntas_respuestas_normas",
        "nombre": "Preguntas y respuestas sobre normas y recomendaciones",
        "source_url": "https://www.cnmv.es/Portal/Menu/Legislacion?lang=es",
        "loaded_tipo_documentos": [],
        "coverage_status": "configured_but_unavailable",
        "contract_note": "Familia oficial identificada en el menu CNMV; sin ingestion dedicada.",
    },
    {
        "family_id": "sanciones_cnmv",
        "nombre": "Registro publico de sanciones CNMV",
        "source_url": "https://www.cnmv.es/Portal/Consultas/RegistroSanciones/verRegSanciones?lang=es",
        "loaded_tipo_documentos": ["sancion_cnmv"],
        "coverage_status": "partial_loaded",
        "contract_note": (
            "Ingestion dedicada del registro publico oficial de sanciones. "
            "La informacion se mantiene como monitor parcial y trazable; "
            "no sustituye al BOE ni afirma universo historico completo."
        ),
    },
    {
        "family_id": "documentos_consulta_cnmv",
        "nombre": "Documentos a consulta de la CNMV",
        "source_url": "https://www.cnmv.es/portal/publicaciones/Documentos-Fase-Consulta?tDoc=1",
        "loaded_tipo_documentos": ["documento_consulta_cnmv"],
        "coverage_status": "partial_loaded",
        "contract_note": (
            "Ingestion dedicada de procesos de consulta CNMV. "
            "No son norma vigente ni obligaciones actuales; sirven para seguimiento regulatorio."
        ),
    },
    {
        "family_id": "modelos_normalizados",
        "nombre": "Modelos normalizados CNMV",
        "source_url": "https://www.cnmv.es/portal/Legislacion/ModelosN/ModelosN",
        "loaded_tipo_documentos": ["modelo_esi_cnmv"],
        "coverage_status": "partial_loaded",
        "contract_note": (
            "Carga dedicada de modelos normalizados ESI desde fuente oficial CNMV. "
            "Son formularios/reporting supervisor, no normativa primaria."
        ),
    },
    {
        "family_id": "normativa_esi",
        "nombre": "Normativa CNMV para ESI",
        "source_url": "https://www.cnmv.es/portal/menu/legislacion-esi?lang=es",
        "loaded_tipo_documentos": ["normativa_esi_cnmv"],
        "coverage_status": "partial_loaded",
        "contract_note": (
            "Indice oficial CNMV para empresas de servicios de inversion. "
            "Puede enlazar a BOE/EUR-Lex; la obligacion vigente debe confirmarse en la fuente normativa primaria."
        ),
    },
    {
        "family_id": "registros_oficiales",
        "nombre": "Registros oficiales CNMV",
        "source_url": "https://www.cnmv.es/Portal/Menu/Legislacion?lang=es",
        "loaded_tipo_documentos": [],
        "coverage_status": "configured_but_unavailable",
        "contract_note": (
            "La web oficial lista registros de entidades, emisores, IIC, ESI, "
            "infraestructuras y CASP; no forman parte del corpus CNMV documental actual."
        ),
    },
]


def _cnmv_boe_reference(row) -> str | None:
    referencia_boe = row.get("referencia_boe")
    if referencia_boe:
        return referencia_boe
    referencia = row["referencia"]
    return referencia if str(referencia).startswith("BOE-") else None


def _cnmv_source_alias(row) -> str | None:
    return row.get("url_fuente")


def _cnmv_row_completeness(row) -> str | None:
    return row.get("row_completeness")


def _cnmv_verified(row) -> bool | None:
    completeness = row.get("row_completeness")
    provenance = row.get("row_provenance")
    if completeness is None and provenance is None:
        return None
    return completeness == "complete" and provenance == "official_exact"


def _cnmv_list_payload(row) -> dict:
    texto = row["texto"] or ""
    completeness = _cnmv_row_completeness(row)
    return {
        "referencia": row["referencia"],
        "fecha": str(row["fecha"]) if row["fecha"] else None,
        "titulo": row["titulo"],
        "tipo_documento": row["tipo_documento"],
        "ambito": row["ambito"],
        "fragmento": texto[:220] + ("..." if texto and len(texto) > 220 else ""),
        "url_fuente": row["url_fuente"],
        "estado_vigencia": row.get("estado_vigencia"),
        "fecha_publicacion": str(row["fecha_publicacion"])
        if row.get("fecha_publicacion")
        else None,
        "referencia_boe": row.get("referencia_boe"),
        "boe_referencia": _cnmv_boe_reference(row),
        "url_cnmv": _cnmv_source_alias(row),
        "verified": _cnmv_verified(row),
        "completeness": completeness,
        "row_completeness": completeness,
        "row_provenance": row.get("row_provenance"),
        "es_consolidado": row.get("es_consolidado"),
        "consolidated_verification_status": row.get("consolidated_verification_status"),
        "consolidated_source_url": row.get("consolidated_source_url"),
        "consolidated_checked_at": str(row["consolidated_checked_at"])
        if row.get("consolidated_checked_at")
        else None,
        "boe_last_modified": str(row["boe_last_modified"])
        if row.get("boe_last_modified")
        else None,
        "consolidated_evidence_note": row.get("consolidated_evidence_note"),
    }


def _apply_cnmv_vigencia_filter(
    filters: list[str],
    params: dict[str, str],
    vigencia: str | None,
) -> tuple[str, list[str] | None]:
    """Apply the CNMV default current-document contract.

    Default retrieval is for current obligations, so derogados are excluded unless
    the caller asks for `vigencia=all` or a specific estado_vigencia.
    """
    normalized = (vigencia or "").strip().lower()
    if not normalized or normalized == "current":
        filters.append("d.estado_vigencia IN ('vigente', 'vigente_modificado')")
        return "current", list(CNMV_CURRENT_VIGENCIA_STATES)

    if normalized == "all":
        return "all", None

    filters.append("d.estado_vigencia = :vigencia")
    params["vigencia"] = normalized
    return normalized, [normalized]


def _empty_coverage_counts() -> dict[str, int]:
    return {
        "loaded_count": 0,
        "vigente_count": 0,
        "vigente_modificado_count": 0,
        "derogado_count": 0,
    }


@router.get(
    "/coverage",
    response_model=CNMVCoverageResponse,
    operation_id="get_cnmv_coverage",
)
async def get_cnmv_coverage():
    """Expose CNMV loaded corpus size versus known official source families."""
    with db_session() as db:
        total_rows = (
            db.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total,
                        SUM(
                            CASE
                                WHEN estado_vigencia IN ('vigente', 'vigente_modificado')
                                THEN 1
                                ELSE 0
                            END
                        ) AS current_total,
                        SUM(
                            CASE WHEN estado_vigencia = 'derogado' THEN 1 ELSE 0 END
                        ) AS derogado_total
                    FROM documento_interpretativo
                    WHERE organismo_emisor = 'CNMV'
                      AND tipo_fuente = 'cnmv'
                    """
                )
            )
            .mappings()
            .first()
        )
        by_type_rows = (
            db.execute(
                text(
                    """
                    SELECT
                        tipo_documento,
                        COUNT(*) AS total,
                        SUM(
                            CASE WHEN estado_vigencia = 'vigente' THEN 1 ELSE 0 END
                        ) AS vigente,
                        SUM(
                            CASE
                                WHEN estado_vigencia = 'vigente_modificado'
                                THEN 1
                                ELSE 0
                            END
                        ) AS vigente_modificado,
                        SUM(
                            CASE WHEN estado_vigencia = 'derogado' THEN 1 ELSE 0 END
                        ) AS derogado
                    FROM documento_interpretativo
                    WHERE organismo_emisor = 'CNMV'
                      AND tipo_fuente = 'cnmv'
                    GROUP BY tipo_documento
                    """
                )
            )
            .mappings()
            .all()
        )

    counts_by_type = {row["tipo_documento"]: row for row in by_type_rows}
    source_families = []
    for family in CNMV_SOURCE_FAMILIES:
        counts = _empty_coverage_counts()
        for tipo_documento in family["loaded_tipo_documentos"]:
            row = counts_by_type.get(tipo_documento)
            if not row:
                continue
            counts["loaded_count"] += int(row["total"] or 0)
            counts["vigente_count"] += int(row["vigente"] or 0)
            counts["vigente_modificado_count"] += int(row["vigente_modificado"] or 0)
            counts["derogado_count"] += int(row["derogado"] or 0)

        source_families.append(
            {
                "family_id": family["family_id"],
                "nombre": family["nombre"],
                "source_url": family["source_url"],
                "coverage_status": family["coverage_status"],
                "contract_note": family["contract_note"],
                **counts,
            }
        )

    return {
        "total_cnmv_loaded": int(total_rows["total"] or 0) if total_rows else 0,
        "current_loaded": int(total_rows["current_total"] or 0) if total_rows else 0,
        "derogado_loaded": int(total_rows["derogado_total"] or 0) if total_rows else 0,
        "source_families": source_families,
        "coverage_note": CNMV_COVERAGE_NOTE,
    }


@router.get("", response_model=DocInterpretativoListResponse, operation_id="listar_cnmv")
async def listar_cnmv(
    request: Request,
    q: str | None = Query(None, description="Filtrar por texto o título"),
    ambito: str | None = Query(None, description="Filtrar por ámbito regulatorio"),
    tipo_documento: str | None = Query(None, description="Filtrar por tipo de documento"),
    vigencia: str | None = Query(
        None,
        description=(
            "Filtrar por estado de vigencia. Por defecto: current "
            "(vigente + vigente_modificado). Use all para incluir derogados."
        ),
    ),
    regulacion: str | None = Query(None, description="Filtrar por regulación EU/ES relacionada (mifid_ii, mifir, mar, dora, priips, LIVMC)"),
    obligacion: str | None = Query(None, description="Filtrar por tipo de obligación (presentacion_modelo, remision_informacion, control_interno, comunicacion_indicio, reporting_prudencial)"),
    skip: int = Query(0, ge=0, description="Offset de paginación"),
    limit: int = Query(20, ge=1, le=100, description="Número de resultados (máx 100)"),
    order_by: str = Query("fecha", description="Campo de ordenación: fecha, referencia, titulo"),
    order_dir: str = Query("desc", description="Dirección de ordenación: asc, desc"),
):
    filters = [
        "d.organismo_emisor = 'CNMV'",
        "d.tipo_fuente = 'cnmv'",
    ]
    params: dict[str, str] = {}
    vigencia_filter, included_estados = _apply_cnmv_vigencia_filter(
        filters,
        params,
        vigencia,
    )

    if q:
        filters.append(
            "(LOWER(d.texto) LIKE LOWER(:term) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term))"
        )
        params["term"] = f"%{q}%"

    if ambito:
        filters.append("d.ambito = :ambito")
        params["ambito"] = ambito

    if tipo_documento:
        filters.append("d.tipo_documento = :tipo_documento")
        params["tipo_documento"] = tipo_documento

    if regulacion:
        filters.append(
            "(d.ambito = :regulacion OR LOWER(d.texto) LIKE LOWER(:reg_term))"
        )
        params["regulacion"] = regulacion
        params["reg_term"] = f"%{regulacion}%"

    if obligacion:
        filters.append("d.referencia IN (SELECT documento_referencia FROM cnmv_obligation_link WHERE tipo_obligacion = :obligacion)")
        params["obligacion"] = obligacion

    # Validate order_by
    allowed_orders = {"fecha", "referencia", "titulo"}
    if order_by not in allowed_orders:
        order_by = "fecha"
    if order_dir not in ("asc", "desc"):
        order_dir = "desc"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente,
                       estado_vigencia, fecha_publicacion, referencia_boe,
                       row_completeness, row_provenance,
                       (
                           SELECT dv.es_consolidado
                           FROM documento_version dv
                           WHERE dv.documento_referencia = d.referencia
                           ORDER BY dv.version_num DESC
                           LIMIT 1
                       ) AS es_consolidado,
                       (
                           SELECT dv.consolidated_verification_status
                           FROM documento_version dv
                           WHERE dv.documento_referencia = d.referencia
                           ORDER BY dv.version_num DESC
                           LIMIT 1
                       ) AS consolidated_verification_status,
                       (
                           SELECT dv.consolidated_source_url
                           FROM documento_version dv
                           WHERE dv.documento_referencia = d.referencia
                           ORDER BY dv.version_num DESC
                           LIMIT 1
                       ) AS consolidated_source_url,
                       (
                           SELECT dv.consolidated_checked_at
                           FROM documento_version dv
                           WHERE dv.documento_referencia = d.referencia
                           ORDER BY dv.version_num DESC
                           LIMIT 1
                       ) AS consolidated_checked_at,
                       (
                           SELECT dv.boe_last_modified
                           FROM documento_version dv
                           WHERE dv.documento_referencia = d.referencia
                           ORDER BY dv.version_num DESC
                           LIMIT 1
                       ) AS boe_last_modified,
                       (
                           SELECT dv.consolidated_evidence_note
                           FROM documento_version dv
                           WHERE dv.documento_referencia = d.referencia
                           ORDER BY dv.version_num DESC
                           LIMIT 1
                       ) AS consolidated_evidence_note
                FROM documento_interpretativo d
                WHERE { ' AND '.join(filters) }
                ORDER BY {order_by} {order_dir}
                LIMIT :limit OFFSET :skip
                """.strip()
            ),
            {**params, "limit": limit, "skip": skip},
        ).mappings()

        docs = [_cnmv_list_payload(row) for row in rows]

        # Get total count for pagination
        total_rows = db.execute(
            text(
                f"""
                SELECT COUNT(*) as cnt
                FROM documento_interpretativo d
                WHERE { ' AND '.join(filters) }
                """.strip()
            ),
            params,
        ).mappings().first()

        total = total_rows["cnt"] if total_rows else 0

        response = {
            "documentos": docs,
            "items": docs,
            "skip": skip,
            "limit": limit,
            "total": total,
            "offset": skip,
            "has_more": (skip + limit) < int(total or 0),
            "next_offset": skip + limit if (skip + limit) < int(total or 0) else None,
            "vigencia_filter": vigencia_filter,
            "included_estados_vigencia": included_estados,
            "coverage_note": CNMV_COVERAGE_NOTE,
        }
        path = request.url.path
        record_retrieval_query_audit(
            request,
            path=path,
            query_text=q or "",
            tool_name="buscar_cnmv" if path.endswith("/buscar") else "listar_cnmv",
            items=docs,
            total=int(total or 0),
            verified=bool(docs),
        )
        return response


@router.get("/buscar", response_model=DocInterpretativoListResponse, operation_id="buscar_cnmv")
async def buscar_cnmv(
    request: Request,
    q: str | None = Query(None, description="Filtrar por texto o titulo"),
    ambito: str | None = Query(None, description="Filtrar por ambito regulatorio"),
    tipo_documento: str | None = Query(None, description="Filtrar por tipo de documento"),
    vigencia: str | None = Query(None, description="Filtrar por estado de vigencia"),
    regulacion: str | None = Query(None, description="Filtrar por regulacion EU/ES relacionada"),
    obligacion: str | None = Query(None, description="Filtrar por tipo de obligacion"),
    skip: int = Query(0, ge=0, description="Offset de paginacion"),
    limit: int = Query(20, ge=1, le=100, description="Numero de resultados"),
    order_by: str = Query("fecha", description="Campo de ordenacion"),
    order_dir: str = Query("desc", description="Direccion de ordenacion"),
):
    return await listar_cnmv(
        request=request,
        q=q,
        ambito=ambito,
        tipo_documento=tipo_documento,
        vigencia=vigencia,
        regulacion=regulacion,
        obligacion=obligacion,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_dir=order_dir,
    )


@router.get(
    "/perfil/{perfil_codigo}",
    response_model=list[dict],
    operation_id="obtener_documentos_cnmv_perfil",
    description=(
        "Devuelve documentos CNMV (circulares, guias tecnicas, modelos "
        "normalizados ESI, normativa) aplicables a un perfil de entidad. "
        "Usar cuando el usuario pregunta que circulares CNMV aplican a una "
        "sociedad de valores, que guias tecnicas debe seguir una agencia de "
        "valores, o que modelos normalizados CNMV existen para un tipo de "
        "entidad. No devuelve obligaciones legales verificadas; para eso usar "
        "obtener_obligaciones_perfil."
    ),
)
async def obtener_documentos_cnmv_perfil(
    request: Request,
    perfil_codigo: str,
    tipo_documento: str | None = Query(
        None,
        description="Filtrar por tipo de documento CNMV",
    ),
    vigente: bool = Query(
        True,
        description="Si es true, excluye documentos CNMV derogados",
    ),
):
    """Devuelve documentos CNMV supervisores aplicables a un perfil."""
    filters = [
        "d.organismo_emisor = 'CNMV'",
        "d.tipo_fuente = 'cnmv'",
    ]
    params: dict[str, str] = {"perfil_codigo": perfil_codigo}

    if tipo_documento:
        filters.append("d.tipo_documento = :tipo_documento")
        params["tipo_documento"] = tipo_documento

    if vigente:
        filters.append("COALESCE(d.estado_vigencia, 'vigente') <> 'derogada'")

    with db_session() as db:
        dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
        dialect = getattr(dialect_name, "name", "")
        if dialect == "postgresql":
            filters.append(":perfil_codigo = ANY(COALESCE(d.sujeto_obligado, ARRAY[]::text[]))")
        else:
            filters.append(
                "instr(',' || COALESCE(d.sujeto_obligado, '') || ',', ',' || :perfil_codigo || ',') > 0"
            )

        rows = (
            db.execute(
                text(
                    f"""
                    SELECT
                        d.referencia,
                        d.titulo,
                        d.tipo_documento,
                        d.fecha,
                        d.url_fuente,
                        d.estado_vigencia,
                        d.ambito AS ambito_tematico
                    FROM documento_interpretativo d
                    WHERE { ' AND '.join(filters) }
                    ORDER BY d.fecha DESC, d.referencia ASC
                    """.strip()
                ),
                params,
            )
            .mappings()
            .all()
        )

    docs = [
        {
            "referencia": row["referencia"],
            "titulo": row["titulo"],
            "tipo_documento": row["tipo_documento"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "url_fuente": row["url_fuente"],
            "estado_vigencia": row["estado_vigencia"],
            "ambito_tematico": row["ambito_tematico"],
        }
        for row in rows
    ]
    record_retrieval_query_audit(
        request,
        path=request.url.path,
        query_text=perfil_codigo,
        tool_name="obtener_documentos_cnmv_perfil",
        items=docs,
        total=len(docs),
        verified=bool(docs),
    )
    return docs


@router.get("/{referencia:path}/versions", response_model=CNMVVersionResponse, operation_id="get_cnmv_versions")
async def get_cnmv_versions(referencia: str):
    """Get version history for a CNMV document (Fase 23.6)."""
    with db_session() as db:
        rows = (
            db.execute(
                text(
                    """
                    SELECT documento_referencia, version_num, texto, cambio_tipo,
                           fecha_version, nota, url_version, es_consolidado,
                           consolidated_verification_status, consolidated_source_url,
                           consolidated_checked_at, boe_last_modified,
                           consolidated_evidence_note
                    FROM documento_version
                    WHERE documento_referencia = :referencia
                    ORDER BY version_num ASC
                    """
                ),
                {"referencia": referencia},
            )
            .mappings()
            .all()
        )

        if not rows:
            rows = (
                db.execute(
                    text(
                        """
                        SELECT documento_referencia,
                               version_numero AS version_num,
                               COALESCE(resumen_cambios, '') AS texto,
                               estado_version AS cambio_tipo,
                               fecha_version,
                               resumen_cambios AS nota,
                               fuente_version AS url_version,
                               es_consolidado,
                               consolidated_verification_status,
                               consolidated_source_url,
                               consolidated_checked_at,
                               boe_last_modified,
                               consolidated_evidence_note
                        FROM documento_cnmv_version
                        WHERE documento_referencia = :referencia
                        ORDER BY version_numero ASC
                        """
                    ),
                    {"referencia": referencia},
                )
                .mappings()
                .all()
            )

        if not rows:
            raise HTTPException(status_code=404, detail={"error": "Historial de versiones no encontrado"})

        versions = [
            {
                "version_num": row["version_num"],
                "cambio_tipo": row["cambio_tipo"],
                "fecha_version": str(row["fecha_version"]) if row["fecha_version"] else None,
                "nota": row.get("nota"),
                "url_version": row.get("url_version"),
                "es_consolidado": row.get("es_consolidado"),
                "consolidated_verification_status": row.get("consolidated_verification_status"),
                "consolidated_source_url": row.get("consolidated_source_url"),
                "consolidated_checked_at": str(row["consolidated_checked_at"])
                if row.get("consolidated_checked_at")
                else None,
                "boe_last_modified": str(row["boe_last_modified"])
                if row.get("boe_last_modified")
                else None,
                "consolidated_evidence_note": row.get("consolidated_evidence_note"),
                "texto": row["texto"],
            }
            for row in rows
        ]

        return {
            "referencia": referencia,
            "versiones": versions,
            "total": len(versions),
        }


@router.get("/{referencia:path}/relaciones", response_model=CNMVRegulationLinkResponse, operation_id="get_cnmv_regulation_links")
async def get_cnmv_regulation_links(referencia: str):
    """Get regulation links for a CNMV document (Fase 23.7)."""
    with db_session() as db:
        rows = (
            db.execute(
                text(
                    """
                    SELECT documento_referencia, regulacion_id, relacion_tipo, nota
                    FROM cnmv_regulation_link
                    WHERE documento_referencia = :referencia
                    """
                ),
                {"referencia": referencia},
            )
            .mappings()
            .all()
        )

        links = [
            {
                "regulacion_id": row["regulacion_id"],
                "relacion_tipo": row["relacion_tipo"],
                "nota": row.get("nota"),
            }
            for row in rows
        ]

        return {
            "referencia": referencia,
            "regulaciones": links,
            "total": len(links),
        }


@router.get("/{referencia:path}/obligaciones", response_model=CNMVObligationLinkResponse, operation_id="get_cnmv_obligation_links")
async def get_cnmv_obligation_links(referencia: str):
    """Get obligation links for a CNMV document (Fase 23.9)."""
    with db_session() as db:
        rows = (
            db.execute(
                text(
                    """
                    SELECT documento_referencia, tipo_obligacion, nota
                    FROM cnmv_obligation_link
                    WHERE documento_referencia = :referencia
                    """
                ),
                {"referencia": referencia},
            )
            .mappings()
            .all()
        )

        links = [
            {
                "tipo_obligacion": row["tipo_obligacion"],
                "nota": row.get("nota"),
            }
            for row in rows
        ]

        return {
            "referencia": referencia,
            "obligaciones": links,
            "total": len(links),
        }


@router.get("/{referencia:path}", response_model=DocInterpretativoDetail, operation_id="get_cnmv")
async def get_cnmv(referencia: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente,
                           estado_vigencia, numero_circular, fecha_publicacion, referencia_boe,
                           row_completeness, row_provenance,
                           (
                               SELECT dv.es_consolidado
                               FROM documento_version dv
                               WHERE dv.documento_referencia = d.referencia
                               ORDER BY dv.version_num DESC
                               LIMIT 1
                           ) AS es_consolidado,
                           (
                               SELECT dv.consolidated_verification_status
                               FROM documento_version dv
                               WHERE dv.documento_referencia = d.referencia
                               ORDER BY dv.version_num DESC
                               LIMIT 1
                           ) AS consolidated_verification_status,
                           (
                               SELECT dv.consolidated_source_url
                               FROM documento_version dv
                               WHERE dv.documento_referencia = d.referencia
                               ORDER BY dv.version_num DESC
                               LIMIT 1
                           ) AS consolidated_source_url,
                           (
                               SELECT dv.consolidated_checked_at
                               FROM documento_version dv
                               WHERE dv.documento_referencia = d.referencia
                               ORDER BY dv.version_num DESC
                               LIMIT 1
                           ) AS consolidated_checked_at,
                           (
                               SELECT dv.boe_last_modified
                               FROM documento_version dv
                               WHERE dv.documento_referencia = d.referencia
                               ORDER BY dv.version_num DESC
                               LIMIT 1
                           ) AS boe_last_modified,
                           (
                               SELECT dv.consolidated_evidence_note
                               FROM documento_version dv
                               WHERE dv.documento_referencia = d.referencia
                               ORDER BY dv.version_num DESC
                               LIMIT 1
                           ) AS consolidated_evidence_note
                    FROM documento_interpretativo d
                    WHERE d.organismo_emisor = 'CNMV'
                      AND d.tipo_fuente = 'cnmv'
                      AND d.referencia = :referencia
                    LIMIT 1
                    """
                ),
                {"referencia": referencia},
            )
            .mappings()
            .first()
        )

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Documento CNMV no encontrado"})

        completeness = _cnmv_row_completeness(row)
        return {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "tipo_documento": row["tipo_documento"],
            "ambito": row["ambito"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
            "estado_vigencia": row.get("estado_vigencia"),
            "numero_circular": row.get("numero_circular"),
            "fecha_publicacion": row.get("fecha_publicacion"),
            "referencia_boe": row.get("referencia_boe"),
            "boe_referencia": _cnmv_boe_reference(row),
            "url_cnmv": _cnmv_source_alias(row),
            "verified": _cnmv_verified(row),
            "completeness": completeness,
            "row_completeness": completeness,
            "row_provenance": row.get("row_provenance"),
            "es_consolidado": row.get("es_consolidado"),
            "consolidated_verification_status": row.get("consolidated_verification_status"),
            "consolidated_source_url": row.get("consolidated_source_url"),
            "consolidated_checked_at": str(row["consolidated_checked_at"])
            if row.get("consolidated_checked_at")
            else None,
            "boe_last_modified": str(row["boe_last_modified"])
            if row.get("boe_last_modified")
            else None,
            "consolidated_evidence_note": row.get("consolidated_evidence_note"),
        }
