from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import SEPBLACDetail, SEPBLACListResponse

router = APIRouter(prefix="/v1/sepblac", tags=["sepblac"])


@router.get("", response_model=SEPBLACListResponse, operation_id="listar_sepblac")
async def listar_sepblac(
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


@router.get("/{referencia:path}", response_model=SEPBLACDetail, operation_id="get_sepblac")
async def get_sepblac(referencia: str):
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

        return {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "tipo_documento": row["tipo_documento"],
            "ambito": row["ambito"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
        }
