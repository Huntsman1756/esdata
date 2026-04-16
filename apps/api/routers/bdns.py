from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import BDNSDetail, BDNSListResponse

router = APIRouter(prefix="/v1/bdns", tags=["bdns"])


@router.get("", response_model=BDNSListResponse, operation_id="listar_bdns")
async def listar_bdns(
    q: str | None = Query(None, description="Filtrar por texto o título"),
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

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT referencia, fecha, titulo, texto, url_fuente
                FROM documento_interpretativo d
                WHERE {where_clause}
                ORDER BY fecha DESC, referencia DESC
                LIMIT 20
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        return {
            "convocatorias": [
                {
                    "referencia": row["referencia"],
                    "fecha": str(row["fecha"]) if row["fecha"] else None,
                    "titulo": row["titulo"],
                    "fragmento": row["texto"][:220]
                    + ("..." if len(row["texto"]) > 220 else ""),
                    "url_fuente": row["url_fuente"],
                }
                for row in rows
            ]
        }


@router.get("/{referencia:path}", response_model=BDNSDetail, operation_id="get_bdns")
async def get_bdns(referencia: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT referencia, fecha, titulo, texto, url_fuente
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

        return {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
        }
