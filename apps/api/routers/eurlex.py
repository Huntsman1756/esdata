from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import CNMVDetail, CNMVListResponse

router = APIRouter(prefix="/v1/eurlex", tags=["eurlex"])


@router.get("", response_model=CNMVListResponse, operation_id="listar_eurlex")
async def listar_eurlex(
    q: str | None = Query(None, description="Filtrar por texto o título"),
    tipo: str | None = Query(None, description="Filtrar por tipo (directiva, reglamento, decision)"),
    ambito: str | None = Query(None, description="Filtrar por ámbito fiscal_ue, mercado_interior, competencia_ue"),
):
    filters = [
        "d.tipo_fuente = 'eurlex'",
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
                }
                for row in rows
            ]
        }


@router.get("/{referencia:path}", response_model=CNMVDetail, operation_id="get_eurlex")
async def get_eurlex(referencia: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente
                    FROM documento_interpretativo d
                    WHERE d.tipo_fuente = 'eurlex'
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
            raise HTTPException(status_code=404, detail={"error": "Documento EUR-Lex no encontrado"})

        return {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "tipo_documento": row["tipo_documento"],
            "ambito": row["ambito"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
        }
