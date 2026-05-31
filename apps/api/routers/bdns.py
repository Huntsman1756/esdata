from db import db_session
from fastapi import APIRouter, HTTPException, Query, Request
from schemas import BDNSDetail, BDNSListResponse
from sqlalchemy import text

from routers.retrieval_audit import record_retrieval_query_audit

router = APIRouter(prefix="/v1/bdns", tags=["bdns"])

BDNS_STRUCTURED_DOCUMENT_TYPES = {
    "convocatoria_bdns",
    "concesion_bdns",
}


def _bdns_coverage_status(items: list[dict]) -> str:
    if not items:
        return "workflow_empty"
    if any(
        item.get("tipo_documento") in BDNS_STRUCTURED_DOCUMENT_TYPES
        and item.get("row_provenance") == "official_exact"
        for item in items
    ):
        return "partial_loaded"
    return "very_limited"


@router.get("", response_model=BDNSListResponse, operation_id="listar_bdns")
async def listar_bdns(
    request: Request,
    q: str | None = Query(None, description="Filtrar por texto o titulo"),
    tipo_documento: str | None = Query(None, description="Filtrar por tipo documental BDNS"),
    beneficiario: str | None = Query(None, description="Filtrar por beneficiario en metadatos BDNS"),
    numero_convocatoria: str | None = Query(None, description="Filtrar por numero de convocatoria BDNS"),
    importe_min: float | None = Query(None, description="Importe minimo de concesion"),
    fecha_desde: str | None = Query(None, description="Fecha minima YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha maxima YYYY-MM-DD"),
    limit: int = Query(20, ge=1, le=100, description="Limite de documentos devueltos"),
    offset: int = Query(0, ge=0, description="Offset de paginacion"),
):
    filters = [
        "d.organismo_emisor = 'BDNS'",
        "d.tipo_fuente = 'bdns'",
    ]
    params: dict[str, str] = {}

    if q:
        filters.append(
            "(LOWER(d.texto) LIKE LOWER(:term) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term))"
        )
        params["term"] = f"%{q}%"
    if tipo_documento:
        filters.append("d.tipo_documento = :tipo_documento")
        params["tipo_documento"] = tipo_documento
    if beneficiario:
        filters.append("LOWER(COALESCE(CAST(d.metadata AS TEXT), '')) LIKE LOWER(:beneficiario)")
        params["beneficiario"] = f"%{beneficiario}%"
    if numero_convocatoria:
        filters.append("LOWER(COALESCE(CAST(d.metadata AS TEXT), '')) LIKE LOWER(:numero_convocatoria)")
        params["numero_convocatoria"] = f"%{numero_convocatoria}%"
    if importe_min is not None:
        filters.append("CAST(d.metadata ->> 'importe' AS NUMERIC) >= :importe_min")
        params["importe_min"] = str(importe_min)
    if fecha_desde:
        filters.append("d.fecha >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filters.append("d.fecha <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT
                    referencia,
                    fecha,
                    titulo,
                    texto,
                    url_fuente,
                    tipo_documento,
                    row_completeness,
                    row_provenance
                FROM documento_interpretativo d
                WHERE {where_clause}
                ORDER BY fecha DESC, referencia DESC
                LIMIT :limit OFFSET :offset
                """.format(where_clause=" AND ".join(filters))
            ),
            {**params, "limit": limit, "offset": offset},
        ).mappings()
        total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM documento_interpretativo d
                WHERE {where_clause}
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).scalar()

        convocatorias = [
            {
                "referencia": row["referencia"],
                "fecha": str(row["fecha"]) if row["fecha"] else None,
                "titulo": row["titulo"],
                "fragmento": row["texto"][:220] + ("..." if len(row["texto"]) > 220 else ""),
                "url_fuente": row["url_fuente"],
                "tipo_documento": row["tipo_documento"],
                "row_completeness": row["row_completeness"] or "partial",
                "row_provenance": row["row_provenance"] or "official_best_effort",
            }
            for row in rows
        ]
        coverage_status = _bdns_coverage_status(convocatorias)
        next_offset = offset + limit if offset + len(convocatorias) < int(total or 0) else None
        record_retrieval_query_audit(
            request,
            path="/v1/bdns",
            query_text=q or "",
            tool_name="listar_bdns",
            items=convocatorias,
            total=int(total or 0),
            verified=bool(convocatorias),
            completeness="parcial",
        )
        return {
            "convocatorias": convocatorias,
            "items": convocatorias,
            "total": int(total or 0),
            "limit": limit,
            "offset": offset,
            "has_more": next_offset is not None,
            "next_offset": next_offset,
            "coverage_status": coverage_status,
            "safe_to_answer": False,
            "coverage_note": (
                "BDNS expone filas oficiales estructuradas parciales cuando estan "
                "cargadas; no implica cobertura amplia ni exhaustiva de subvenciones."
            ),
        }


@router.get("/{referencia:path}", response_model=BDNSDetail, operation_id="get_bdns")
async def get_bdns(referencia: str, request: Request):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT
                        referencia,
                        fecha,
                        titulo,
                        texto,
                        url_fuente,
                        tipo_documento,
                        row_completeness,
                        row_provenance
                    FROM documento_interpretativo d
                    WHERE d.organismo_emisor = 'BDNS'
                      AND d.tipo_fuente = 'bdns'
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
            raise HTTPException(status_code=404, detail={"error": "Convocatoria BDNS no encontrada"})

        result = {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
            "tipo_documento": row["tipo_documento"],
            "row_completeness": row["row_completeness"] or "partial",
            "row_provenance": row["row_provenance"] or "official_best_effort",
        }
        record_retrieval_query_audit(
            request,
            path="/v1/bdns/{referencia}",
            query_text=referencia,
            tool_name="get_bdns",
            items=[result],
            total=1,
            verified=True,
            completeness="parcial",
        )
        return result
