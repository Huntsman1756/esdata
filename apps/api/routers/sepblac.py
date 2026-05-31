from db import db_session
from fastapi import APIRouter, HTTPException, Query, Request
from schemas import SEPBLACDetail, SEPBLACListResponse
from sqlalchemy import text

from routers.retrieval_audit import record_retrieval_query_audit

router = APIRouter(prefix="/v1/sepblac", tags=["sepblac"])


@router.get("", response_model=SEPBLACListResponse, operation_id="listar_sepblac")
async def listar_sepblac(
    request: Request,
    q: str | None = Query(None, description="Filtrar por texto o título"),
    ambito: str | None = Query(None, description="Filtrar por ámbito operativo"),
):
    filters = [
        "d.organismo_emisor = 'SEPBLAC'",
        "d.tipo_fuente = 'sepblac'",
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

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente
                FROM documento_interpretativo d
                WHERE {where_clause}
                ORDER BY fecha DESC, referencia DESC
                LIMIT 20
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        documentos = [
            {
                "referencia": row["referencia"],
                "fecha": str(row["fecha"]) if row["fecha"] else None,
                "titulo": row["titulo"],
                "tipo_documento": row["tipo_documento"],
                "ambito": row["ambito"],
                "fragmento": row["texto"][:220] + ("..." if len(row["texto"]) > 220 else ""),
                "url_fuente": row["url_fuente"],
                "row_completeness": "partial",
                "row_provenance": "official_best_effort",
            }
            for row in rows
        ]
        record_retrieval_query_audit(
            request,
            path="/v1/sepblac",
            query_text=q or ambito or "",
            tool_name="listar_sepblac",
            items=documentos,
            total=len(documentos),
            verified=bool(documentos),
            completeness="parcial",
        )
        return {
            "documentos": documentos,
            "items": documentos,
            "total": len(documentos),
            "coverage_status": "partial_loaded" if documentos else "workflow_empty",
            "safe_to_answer": False,
            "coverage_note": (
                "SEPBLAC expone documentos oficiales cargados de forma parcial; "
                "no implica cobertura exhaustiva ni conclusion PBC/FT automatica."
            ),
        }


@router.get("/{referencia:path}", response_model=SEPBLACDetail, operation_id="get_sepblac")
async def get_sepblac(referencia: str, request: Request):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente
                    FROM documento_interpretativo d
                    WHERE d.organismo_emisor = 'SEPBLAC'
                      AND d.tipo_fuente = 'sepblac'
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
            raise HTTPException(status_code=404, detail={"error": "Documento SEPBLAC no encontrado"})

        result = {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "tipo_documento": row["tipo_documento"],
            "ambito": row["ambito"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
            "row_completeness": "partial",
            "row_provenance": "official_best_effort",
        }
        record_retrieval_query_audit(
            request,
            path="/v1/sepblac/{referencia}",
            query_text=referencia,
            tool_name="get_sepblac",
            items=[result],
            total=1,
            verified=True,
            completeness="parcial",
        )
        return result
