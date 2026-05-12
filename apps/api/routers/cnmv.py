from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    CNMVObligationLinkResponse,
    CNMVRegulationLinkResponse,
    CNMVVersionResponse,
    DocInterpretativoDetail,
    DocInterpretativoListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/cnmv", tags=["cnmv"])


def _cnmv_boe_reference(row) -> str | None:
    referencia_boe = row.get("referencia_boe")
    if referencia_boe:
        return referencia_boe
    referencia = row["referencia"]
    return referencia if str(referencia).startswith("BOE-") else None


def _cnmv_source_alias(row) -> str | None:
    return row.get("url_fuente")


def _cnmv_list_payload(row) -> dict:
    texto = row["texto"] or ""
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
    }


@router.get("", response_model=DocInterpretativoListResponse, operation_id="listar_cnmv")
async def listar_cnmv(
    q: str | None = Query(None, description="Filtrar por texto o título"),
    ambito: str | None = Query(None, description="Filtrar por ámbito regulatorio"),
    tipo_documento: str | None = Query(None, description="Filtrar por tipo de documento"),
    vigencia: str | None = Query(None, description="Filtrar por estado de vigencia"),
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

    if vigencia:
        filters.append("d.estado_vigencia = :vigencia")
        params["vigencia"] = vigencia

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
                       estado_vigencia, fecha_publicacion, referencia_boe
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

        return {
            "documentos": docs,
            "skip": skip,
            "limit": limit,
            "total": total,
        }


@router.get("/buscar", response_model=DocInterpretativoListResponse, operation_id="buscar_cnmv")
async def buscar_cnmv(
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


@router.get("/{referencia:path}/versions", response_model=CNMVVersionResponse, operation_id="get_cnmv_versions")
async def get_cnmv_versions(referencia: str):
    """Get version history for a CNMV document (Fase 23.6)."""
    with db_session() as db:
        rows = (
            db.execute(
                text(
                    """
                    SELECT documento_referencia, version_num, texto, cambio_tipo,
                           fecha_version, nota, url_version
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
                               fuente_version AS url_version
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
                           estado_vigencia, numero_circular, fecha_publicacion, referencia_boe
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
        }
