from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import CNMVDetail, CNMVListResponse

router = APIRouter(prefix="/v1/cendoj", tags=["cendoj"])


@router.get("", response_model=CNMVListResponse, operation_id="listar_cendoj")
async def listar_cendoj(
    q: str | None = Query(None, description="Filtrar por texto o título"),
    court: str | None = Query(None, description="Filtrar por tribunal (tribunal_supremo, audiencia_nacional, tsj)"),
    tipo: str | None = Query(None, description="Filtrar por tipo de documento (sentencia, auto, providencia)"),
    organismo: str | None = Query(None, description="Filtrar por organismo emisor"),
):
    filters = [
        "d.tipo_fuente = 'cendoj'",
    ]
    params: dict[str, str] = {}

    if q:
        filters.append(
            "(LOWER(d.texto) LIKE LOWER(:term) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term))"
        )
        params["term"] = f"%{q}%"

    if court:
        filters.append("LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:court_term)")
        params["court_term"] = f"%{court.replace('_', ' ')}%"

    if tipo:
        filters.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo

    if organismo:
        filters.append("LOWER(d.organismo_emisor) = LOWER(:organismo)")
        params["organismo"] = organismo

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente, organismo_emisor
                FROM documento_interpretativo d
                WHERE {where_clause}
                ORDER BY fecha DESC, referencia DESC
                LIMIT 20
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        return {
            "documentos": [
                {
                    "referencia": row["referencia"],
                    "fecha": str(row["fecha"]) if row["fecha"] else None,
                    "titulo": row["titulo"],
                    "tipo_documento": row["tipo_documento"],
                    "ambito": row["ambito"],
                    "fragmento": row["texto"][:220]
                    + ("..." if len(row["texto"]) > 220 else ""),
                    "url_fuente": row["url_fuente"],
                    "organismo_emisor": row.get("organismo_emisor"),
                }
                for row in rows
            ]
        }


@router.get("/{referencia:path}", response_model=CNMVDetail, operation_id="get_cendoj")
async def get_cendoj(referencia: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente, organismo_emisor
                    FROM documento_interpretativo d
                    WHERE d.tipo_fuente = 'cendoj'
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
            raise HTTPException(status_code=404, detail={"error": "Documento CENDOJ no encontrado"})

        return {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "tipo_documento": row["tipo_documento"],
            "ambito": row["ambito"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
            "organismo_emisor": row.get("organismo_emisor"),
        }
