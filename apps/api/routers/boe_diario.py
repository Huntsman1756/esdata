import json

from db import db_session
from fastapi import APIRouter, HTTPException, Query, Request
from schemas import BOEDiarioDetail, BOEDiarioListResponse
from sqlalchemy import text

from routers.retrieval_audit import record_retrieval_query_audit

router = APIRouter(prefix="/v1/boe-diario", tags=["boe-diario"])


def _metadata(value):
    if value is None or isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


@router.get("", response_model=BOEDiarioListResponse, operation_id="listar_boe_diario")
async def listar_boe_diario(
    request: Request,
    q: str | None = Query(None, description="Filtrar por texto o titulo"),
    tipo: str | None = Query(None, description="anuncio_boe | suplemento_boe | notificacion_boe"),
    limit: int = Query(20, ge=1, le=100, description="Limite de documentos devueltos"),
    offset: int = Query(0, ge=0, description="Offset de paginacion"),
):
    filters = ["d.organismo_emisor = 'BOE'", "d.tipo_fuente = 'boe_diario'"]
    params: dict[str, str] = {}
    if q:
        filters.append("(LOWER(d.texto) LIKE LOWER(:term) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term))")
        params["term"] = f"%{q}%"
    if tipo:
        filters.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo
    where_clause = " AND ".join(filters)

    with db_session() as db:
        rows = list(
            db.execute(
                text(
                    f"""
                    SELECT
                        referencia,
                        fecha,
                        titulo,
                        tipo_documento,
                        texto,
                        url_fuente,
                        row_completeness,
                        row_provenance
                    FROM documento_interpretativo d
                    WHERE {where_clause}
                    ORDER BY fecha DESC, referencia DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {**params, "limit": limit, "offset": offset},
            ).mappings()
        )
        total = db.execute(
            text(f"SELECT COUNT(*) FROM documento_interpretativo d WHERE {where_clause}"),
            params,
        ).scalar()

    documentos = [
        {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "tipo_documento": row["tipo_documento"],
            "fragmento": (row["texto"] or "")[:220] + ("..." if len(row["texto"] or "") > 220 else ""),
            "url_fuente": row["url_fuente"],
            "row_completeness": row["row_completeness"],
            "row_provenance": row["row_provenance"],
        }
        for row in rows
    ]
    record_retrieval_query_audit(
        request,
        path="/v1/boe-diario",
        query_text=q or tipo or "",
        tool_name="listar_boe_diario",
        items=documentos,
        total=int(total or 0),
        verified=True,
        completeness="completa" if documentos else "parcial",
    )
    next_offset = offset + limit if offset + len(documentos) < int(total or 0) else None
    return {
        "documentos": documentos,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": next_offset is not None,
        "next_offset": next_offset,
    }


@router.get("/{referencia:path}", response_model=BOEDiarioDetail, operation_id="get_boe_diario")
async def get_boe_diario(referencia: str, request: Request):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT
                        referencia,
                        fecha,
                        titulo,
                        tipo_documento,
                        texto,
                        url_fuente,
                        row_completeness,
                        row_provenance,
                        metadata
                    FROM documento_interpretativo d
                    WHERE d.organismo_emisor = 'BOE'
                      AND d.tipo_fuente = 'boe_diario'
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
        raise HTTPException(status_code=404, detail={"error": "Documento BOE diario no encontrado"})

    result = {
        "referencia": row["referencia"],
        "fecha": str(row["fecha"]) if row["fecha"] else None,
        "titulo": row["titulo"],
        "tipo_documento": row["tipo_documento"],
        "texto": row["texto"],
        "url_fuente": row["url_fuente"],
        "row_completeness": row["row_completeness"],
        "row_provenance": row["row_provenance"],
        "metadata": _metadata(row["metadata"]),
    }
    record_retrieval_query_audit(
        request,
        path="/v1/boe-diario/{referencia}",
        query_text=referencia,
        tool_name="get_boe_diario",
        items=[result],
        total=1,
        verified=True,
        completeness=result["row_completeness"] or "completa",
    )
    return result
