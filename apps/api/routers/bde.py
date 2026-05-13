from db import db_session
from fastapi import APIRouter, HTTPException, Query, Request
from schemas import DocInterpretativoDetail, DocInterpretativoListResponse
from sqlalchemy import text

from routers.retrieval_audit import record_retrieval_query_audit

router = APIRouter(prefix="/v1/bde", tags=["bde"])


@router.get("", response_model=DocInterpretativoListResponse, operation_id="listar_bde")
async def listar_bde(
    request: Request,
    q: str | None = Query(None, description="Filtrar por texto o título"),
    tipo: str | None = Query(None, description="Filtrar por tipo (informe_bde, comunicacion_bde, publicacion_bde)"),
    ambito: str | None = Query(None, description="Filtrar por ámbito (estabilidad_financiera, politica_monetaria, supervision_bancaria)"),
):
    filters = [
        "d.tipo_fuente = 'bde'",
    ]
    params: dict[str, str] = {}

    if q:
        filters.append(
            "(LOWER(d.texto) LIKE LOWER(:term) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term))"
        )
        params["term"] = f"%{q}%"

    if tipo:
        filters.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo

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
            }
            for row in rows
        ]
        record_retrieval_query_audit(
            request,
            path="/v1/bde",
            query_text=q or tipo or ambito or "",
            tool_name="listar_bde",
            items=documentos,
            total=len(documentos),
            verified=bool(documentos),
            completeness="parcial",
        )
        return {"documentos": documentos}


@router.get("/{referencia:path}", response_model=DocInterpretativoDetail, operation_id="get_bde")
async def get_bde(referencia: str, request: Request):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente
                    FROM documento_interpretativo d
                    WHERE d.tipo_fuente = 'bde'
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
            raise HTTPException(status_code=404, detail={"error": "Documento Banco de España no encontrado"})

        result = {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "tipo_documento": row["tipo_documento"],
            "ambito": row["ambito"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
        }
        record_retrieval_query_audit(
            request,
            path="/v1/bde/{referencia}",
            query_text=referencia,
            tool_name="get_bde",
            items=[result],
            total=1,
            verified=True,
            completeness="parcial",
        )
        return result
